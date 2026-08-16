"""Codex-Paseo-Claude collaboration seam (Issue #32).

Thin collaboration module that calls the real Paseo CLI for daemon probing,
provider discovery, agent creation, dispatch, and repair.  Reuses the shared
codex_direct state, evidence, recovery, acceptance, and commit machinery
unchanged.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

from harness.codex_direct import (
    CONTROL_SCHEMAS,
    DIRECT_MODES,
    GUARDED_ACTIONS,
    RUN_SCHEMAS,
    CodexDirectAdapterError,
    CodexDirectError,
    _add_history,
    _changed_paths,
    _commit_identity_environment,
    _control,
    _diff_digest,
    _git,
    _git_worktree_roots,
    _load_run,
    _manual_skill_was_reminded_elsewhere,
    _path_is_owned,
    _path_snapshot,
    _reject_in_progress_git_operation,
    _reject_repository_filters,
    _reject_ticket_in_other_worktree,
    _repository_lock_identity,
    _repository_mutex,
    _require_digest,
    _rollback_unstable_start,
    _runtime_contract,
    _save_run,
    _snapshot_digest,
    _task_dir,
    _task_source_digest,
    _begin_repair_unlocked,
    _accept_codex_direct_unlocked,
    _enter_recovery_unlocked,
    begin_repair,
    bounded_file_lock,
    ensure_no_link_components,
    enter_recovery,
    guard_codex_direct,
    read_bounded_bytes,
    read_bounded_json_object,
)
from harness.capabilities import check_manual_skill
from harness.contracts import ContractError, validate_task_contract
from harness.safe_io import _unlink_nofollow

COLLAB_GUARD_ACTIONS = GUARDED_ACTIONS | {"stage", "review", "verify", "explore", "accept"}
from harness.context import WorktreeContext

# ---------------------------------------------------------------------------
# Schemas and limits
# ---------------------------------------------------------------------------

PREFLIGHT_SCHEMA = "harness.paseo-preflight/v1"
LAUNCH_SCHEMA = "harness.paseo-writer-launch/v1"
REPORT_SCHEMA = "harness.paseo-writer-report/v1"


def _launch_digest(launch: dict[str, Any]) -> str:
    """Canonical launch-sidecar digest — the single serialization seam
    shared by report persistence and acceptance binding."""
    return hashlib.sha256(
        json.dumps(launch, sort_keys=True).encode("utf-8")
    ).hexdigest()


def _is_hex64(value: Any) -> bool:
    """Strict 64-char lowercase hex digest check."""
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(c in "0123456789abcdef" for c in value)
    )


def _is_safe_identifier(value: Any) -> bool:
    """Runtime-safe bounded identifier: 1-64 chars, fixed alphabet."""
    return (
        isinstance(value, str)
        and 1 <= len(value) <= 64
        and all(
            c in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._:-"
            for c in value
        )
    )


def _prompt_identity_matches(
    prompt_path: Path,
    descriptor: int,
    expected_size: int | None = None,
) -> bool:
    try:
        opened = os.fstat(descriptor)
    except OSError:
        return False
    if os.name != "nt":
        return (
            stat.S_ISREG(opened.st_mode)
            and opened.st_nlink == 0
            and (expected_size is None or opened.st_size == expected_size)
        )
    try:
        current = os.stat(prompt_path, follow_symlinks=False)
    except OSError:
        return False
    return (
        stat.S_ISREG(opened.st_mode)
        and opened.st_nlink == 1
        and (opened.st_dev, opened.st_ino) == (current.st_dev, current.st_ino)
        and (expected_size is None or opened.st_size == expected_size)
    )


def _open_private_prompt(prompt_path: Path) -> int:
    if os.name != "nt":
        try:
            os.lstat(prompt_path)
        except FileNotFoundError:
            pass
        else:
            raise FileExistsError(prompt_path)
        with tempfile.TemporaryFile(dir=prompt_path.parent) as private:
            return os.dup(private.fileno())

    import ctypes
    import msvcrt
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create_file = kernel32.CreateFileW
    create_file.argtypes = (
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    )
    create_file.restype = wintypes.HANDLE
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = (wintypes.HANDLE,)
    close_handle.restype = wintypes.BOOL
    handle = create_file(
        str(prompt_path),
        0xC0000000,  # GENERIC_READ | GENERIC_WRITE
        0x00000001,  # FILE_SHARE_READ
        None,
        1,  # CREATE_NEW
        0x00000100,  # FILE_ATTRIBUTE_TEMPORARY
        None,
    )
    if handle == wintypes.HANDLE(-1).value:
        raise OSError(ctypes.get_last_error(), "private prompt creation failed")
    try:
        return msvcrt.open_osfhandle(
            handle, os.O_RDWR | getattr(os, "O_BINARY", 0)
        )
    except OSError:
        close_handle(handle)
        raise


def _unlink_ephemeral_prompt(
    context: WorktreeContext,
    prompt_path: Path,
    descriptor: int | None = None,
) -> None:
    """Fail-closed ephemeral prompt cleanup.

    No launch/repair-dispatch success evidence may be emitted after a
    cleanup failure, so an unlink error stops the operation (the prepared
    pending intent stays for recovery inspection)."""
    if descriptor is not None:
        try:
            os.ftruncate(descriptor, 0)
            os.fsync(descriptor)
        except OSError as exc:
            raise PaseoCollaborationError(
                f"prompt_cleanup_failed: {prompt_path.name}"
            ) from exc
        finally:
            os.close(descriptor)
        if os.name != "nt":
            return
    try:
        ensure_no_link_components(context.root, prompt_path)
        current = prompt_path.stat(follow_symlinks=False)
        if not stat.S_ISREG(current.st_mode) or current.st_nlink != 1:
            raise OSError("prompt path is not a private regular file")
        prompt_path.unlink()
    except FileNotFoundError:
        return
    except (OSError, ValueError) as exc:
        raise PaseoCollaborationError(
            f"prompt_cleanup_failed: {prompt_path.name}"
        ) from exc


def _write_ephemeral_prompt(
    context: WorktreeContext,
    prompt_path: Path,
    content: str,
) -> int:
    """Create a private prompt without following or truncating existing files."""
    raw = content.encode("utf-8")
    if len(raw) > PROMPT_FILE_MAX_BYTES:
        raise PaseoCollaborationError("ephemeral_prompt_oversized")

    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        ensure_no_link_components(context.root, prompt_path)
        descriptor = _open_private_prompt(prompt_path)
    except (OSError, ValueError) as exc:
        raise PaseoCollaborationError(
            f"ephemeral_prompt_unavailable: {prompt_path.name}"
        ) from exc

    try:
        if not _prompt_identity_matches(prompt_path, descriptor, 0):
            raise PaseoCollaborationError(
                f"ephemeral_prompt_unavailable: {prompt_path.name}"
            )
        view = memoryview(raw)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("short prompt write")
            view = view[written:]
        os.fsync(descriptor)
        if not _prompt_identity_matches(prompt_path, descriptor, len(raw)):
            raise PaseoCollaborationError(
                f"ephemeral_prompt_unavailable: {prompt_path.name}"
            )
    except (OSError, PaseoCollaborationError) as exc:
        # The descriptor always identifies the inode created above with
        # O_EXCL.  If another process links or relocates it, erase those bytes
        # through the trusted descriptor before reporting the failed write.
        try:
            os.ftruncate(descriptor, 0)
            os.fsync(descriptor)
        except OSError as scrub_exc:
            os.close(descriptor)
            raise PaseoCollaborationError(
                f"ephemeral_prompt_scrub_failed: {prompt_path.name}"
            ) from scrub_exc
        os.close(descriptor)
        if isinstance(exc, PaseoCollaborationError):
            raise
        raise PaseoCollaborationError(
            f"ephemeral_prompt_write_failed: {prompt_path.name}"
        ) from exc
    return descriptor


def _send_verified_prompt(
    agent_id: str,
    prompt_path: Path,
    descriptor: int,
) -> dict[str, Any]:
    if not _prompt_identity_matches(prompt_path, descriptor):
        raise PaseoCollaborationError("prompt_identity_changed")
    prompt_source = str(prompt_path)
    pass_fds: tuple[int, ...] = ()
    if os.name != "nt":
        # POSIX Paseo reads an anonymous inherited file. Windows keeps the
        # private source handle open, denying writes and path replacement.
        os.lseek(descriptor, 0, os.SEEK_SET)
        prompt_source = f"/dev/fd/{descriptor}"
        pass_fds = (descriptor,)
    result = _run_paseo_cli(
        "send", agent_id,
        "--prompt-file", prompt_source,
        "--no-wait",
        timeout=PASEO_RUN_TIMEOUT,
        pass_fds=pass_fds,
    )
    if not _prompt_identity_matches(prompt_path, descriptor):
        raise PaseoCollaborationError("prompt_identity_changed")
    return result


def _validate_repair_deliveries(
    task_dir: Path,
    run: dict[str, Any],
    task_id: str,
) -> list[str]:
    """Every recorded repair entry must have matching dispatch evidence.

    Returns mismatch tags (empty = all delivered).  Binds each dispatch
    sidecar's schema/task/mode/agent/attempt/fingerprint to the frozen run
    record and requires a bounded send digest — closes the crash window
    after ``_begin_repair_unlocked`` but before the sidecar write."""
    errors: list[str] = []
    frozen_agent_id = run.get("agent_id", "")
    for entry in run.get("repairs", []):
        attempt = entry.get("attempt")
        if not isinstance(attempt, int) or attempt < 1:
            errors.append(f"repair_entry_bad_attempt: {attempt!r}")
            continue
        evidence = read_bounded_json_object(
            task_dir / f"repair-dispatch-{attempt}.json",
            MAX_STATE_BYTES,
            max_nodes=MAX_STATE_NODES,
        )
        if not isinstance(evidence, dict):
            errors.append(f"repair_attempt_{attempt}_dispatch_missing")
            continue
        if evidence.get("schema") != "harness.repair-dispatch/v1":
            errors.append(f"repair_attempt_{attempt}_bad_schema")
            continue
        if evidence.get("task_id") != task_id:
            errors.append(f"repair_attempt_{attempt}_task_id_mismatch")
            continue
        if evidence.get("mode") != "codex-paseo-claude":
            errors.append(f"repair_attempt_{attempt}_mode_mismatch")
            continue
        if evidence.get("agent_id") != frozen_agent_id:
            errors.append(f"repair_attempt_{attempt}_agent_id_mismatch")
            continue
        if evidence.get("attempt") != attempt:
            errors.append(f"repair_attempt_{attempt}_attempt_mismatch")
            continue
        if evidence.get("fingerprint") != entry.get("fingerprint"):
            errors.append(f"repair_attempt_{attempt}_fingerprint_mismatch")
            continue
        if not _is_hex64(evidence.get("send_digest")):
            errors.append(f"repair_attempt_{attempt}_bad_send_digest")
    return errors


BRIDGE_SCHEMA = "harness.codex-bridge-trigger/v1"

MAX_STATE_BYTES = 256 * 1024
MAX_STATE_NODES = 512
REPORT_TEXT_MAX_BYTES = 4096  # bound free text before hashing
PASEO_TIMEOUT = 30  # seconds for most CLI calls
PASEO_RUN_TIMEOUT = 60  # seconds for agent creation
MAX_STDOUT = 256 * 1024
MAX_STDERR = 64 * 1024
PROMPT_FILE_MAX_BYTES = 128 * 1024

# Evidence fields we never persist
REDACTED_KEYS = frozenset({
    "stdout", "stderr", "command", "prompt", "absolute_path",
    "home", "logPath", "daemonNode", "cliNode", "listen", "relay",
    "hostname", "owner", "pid",
})


# ---------------------------------------------------------------------------
# Paseo CLI resolution and subprocess
# ---------------------------------------------------------------------------

class PaseoCollaborationError(Exception):
    """Fail-closed Paseo collaboration error."""


def _resolve_paseo_cli() -> Path:
    """Resolve the installed Paseo CLI launcher.

    Resolve only the platform-native launcher through ``shutil.which``; no
    hard-coded machine paths or cross-platform command shims are executed.
    """
    candidates = ["paseo.cmd", "paseo"] if os.name == "nt" else ["paseo"]
    for name in candidates:
        resolved = shutil.which(name)
        if resolved is not None:
            return Path(resolved)
    raise PaseoCollaborationError(
        "paseo_cli_unavailable: native launcher not found on PATH"
    )


def _run_paseo_cli(
    *args: str,
    timeout: int = PASEO_TIMEOUT,
    input_bytes: bytes | None = None,
    pass_fds: tuple[int, ...] = (),
) -> dict[str, Any]:
    """Single bounded Paseo CLI subprocess call.

    Fail-closed: ``shell=False``, ``stdin=DEVNULL``, stdout/stderr drained
    concurrently and killed on byte overflow or timeout, JSON-only output,
    metadata-only errors (raw stderr is never surfaced).  Never persists
    credentials.
    """
    exe = str(_resolve_paseo_cli())
    full_args = [exe, "--json", *args]
    try:
        popen_options: dict[str, Any] = {}
        if pass_fds:
            if os.name == "nt":
                raise PaseoCollaborationError("paseo_prompt_fd_unsupported")
            popen_options["pass_fds"] = pass_fds
        process = subprocess.Popen(
            full_args,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            **popen_options,
        )
    except (OSError, subprocess.SubprocessError):
        raise PaseoCollaborationError("paseo_cli_unavailable")

    stdout_chunks: list[bytes] = []
    stderr_chunks: list[bytes] = []
    stdout_overflow = threading.Event()
    stderr_overflow = threading.Event()

    def read_bounded(stream, chunks, max_bytes, overflow) -> None:
        try:
            remaining = max_bytes + 1
            while remaining:
                chunk = stream.read(min(64 * 1024, remaining))
                if not chunk:
                    return
                chunks.append(chunk)
                remaining -= len(chunk)
            overflow.set()
            try:
                process.kill()
            except OSError:
                pass
        except OSError:
            try:
                process.kill()
            except OSError:
                pass

    stdout_reader = threading.Thread(
        target=read_bounded,
        args=(process.stdout, stdout_chunks, MAX_STDOUT, stdout_overflow),
        daemon=True,
    )
    stderr_reader = threading.Thread(
        target=read_bounded,
        args=(process.stderr, stderr_chunks, MAX_STDERR, stderr_overflow),
        daemon=True,
    )
    stdout_reader.start()
    stderr_reader.start()

    def close_streams() -> None:
        for stream in (process.stdout, process.stderr):
            if stream is not None:
                stream.close()

    try:
        return_code = process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            process.kill()
        except OSError:
            pass
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass
        stdout_reader.join(timeout=5)
        stderr_reader.join(timeout=5)
        close_streams()
        raise PaseoCollaborationError("paseo_cli_timeout")

    stdout_reader.join(timeout=5)
    stderr_reader.join(timeout=5)
    close_streams()
    if stdout_reader.is_alive() or stderr_reader.is_alive():
        raise PaseoCollaborationError("paseo_cli_output_did_not_close")
    if stdout_overflow.is_set():
        raise PaseoCollaborationError("paseo_cli_stdout_oversized")
    if stderr_overflow.is_set():
        raise PaseoCollaborationError("paseo_cli_stderr_oversized")
    if return_code != 0:
        raise PaseoCollaborationError(f"paseo_cli_exit_{return_code}")

    stdout_bytes = b"".join(stdout_chunks)
    try:
        result = json.loads(
            (stdout_bytes or b"null").decode("utf-8", errors="strict")
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PaseoCollaborationError("paseo_cli_invalid_json") from exc

    if not isinstance(result, (dict, list)):
        raise PaseoCollaborationError("paseo_cli_unexpected_output")
    return result


# ---------------------------------------------------------------------------
# Orchestration preferences
# ---------------------------------------------------------------------------

def _read_orchestration_prefs() -> dict[str, Any]:
    """Read ``~/.paseo/orchestration-preferences.json``.

    Returns the parsed dict or an empty dict when unavailable.
    """
    prefs_path = Path.home() / ".paseo" / "orchestration-preferences.json"
    raw = read_bounded_bytes(prefs_path, MAX_STATE_BYTES)
    if raw is None:
        return {}
    try:
        data = json.loads(raw.decode("utf-8", errors="strict"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _resolve_provider(prefs: dict[str, Any], override: str | None) -> tuple[str, str]:
    """Resolve provider and model from preferences or override.

    Returns ``(provider, model)`` tuple.  The preferences key is
    ``providers.impl`` in ``<provider>/<model>`` form.
    """
    coordinate: Any = override
    if coordinate is None:
        providers = prefs.get("providers")
        coordinate = providers.get("impl") if isinstance(providers, dict) else None
    parts = coordinate.split("/") if isinstance(coordinate, str) else []
    if len(parts) != 2 or not all(_is_safe_identifier(part) for part in parts):
        raise PaseoCollaborationError(
            "provider_not_resolved: set providers.impl in "
            "~/.paseo/orchestration-preferences.json or pass --provider"
        )
    return parts[0], parts[1]


# ---------------------------------------------------------------------------
# Preflight (finding #1, #2)
# ---------------------------------------------------------------------------

def paseo_preflight(
    context: WorktreeContext,
    provider_override: str | None = None,
) -> dict[str, Any]:
    """Read-only Paseo capability probe.

    Checks daemon health and provider list. Never starts/restarts a daemon.
    Never picks an automatic fallback. Returns
    ``harness.paseo-preflight/v1``.
    """
    result: dict[str, Any] = {
        "schema": PREFLIGHT_SCHEMA,
        "available": False,
        "restarted_daemon": False,
        "fallback_chosen": False,
        "providers": {},
        "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    # Daemon status
    try:
        status = _run_paseo_cli("daemon", "status")
    except PaseoCollaborationError as exc:
        result["error"] = str(exc)
        return result

    if not isinstance(status, dict):
        result["error"] = "daemon_status_unexpected_format"
        return result
    local = status.get("localDaemon", "")
    connected = status.get("connectedDaemon", "")
    if local != "running":
        result["error"] = f"daemon_not_running: {local}"
        return result
    # Paseo 0.2.5 reports a healthy connected daemon as "reachable";
    # older healthy spellings ("connected") remain accepted.
    if connected not in ("connected", "reachable"):
        result["error"] = f"daemon_not_connected: {connected}"
        return result

    daemon_version = status.get("daemonVersion", "")
    cli_version = status.get("cliVersion", "")
    result["daemon"] = {
        "version": daemon_version,
        "cli_version": cli_version,
    }

    # Provider list
    try:
        providers_raw = _run_paseo_cli("provider", "ls")
    except PaseoCollaborationError as exc:
        result["error"] = f"provider_list_failed: {exc}"
        return result

    if not isinstance(providers_raw, list):
        result["error"] = "provider_list_unexpected_format"
        return result

    providers_map: dict[str, dict[str, Any]] = {}
    for entry in providers_raw:
        if not isinstance(entry, dict):
            continue
        name = entry.get("provider")
        if not isinstance(name, str):
            continue
        providers_map[name] = {
            "status": entry.get("status", "unknown"),
            "label": entry.get("label", name),
            "default_mode": entry.get("defaultMode", ""),
        }
    result["providers"] = providers_map

    # Resolve target provider
    try:
        prefs = _read_orchestration_prefs()
        provider, model = _resolve_provider(prefs, provider_override)
    except PaseoCollaborationError as exc:
        result["error"] = str(exc)
        return result

    if provider != "claude":
        result["error"] = f"provider_not_claude: {provider}"
        return result

    provider_info = providers_map.get(provider)
    if provider_info is None or provider_info.get("status") != "available":
        result["error"] = f"provider_unavailable: {provider}"
        return result

    # Validate model exists (fail closed — model discovery failure is blocking)
    try:
        models_raw = _run_paseo_cli("provider", "models", provider, "--thinking")
    except PaseoCollaborationError as exc:
        result["error"] = f"model_list_failed: {exc}"
        return result

    model_ids: set[str] = set()
    if isinstance(models_raw, list):
        for entry in models_raw:
            if isinstance(entry, dict):
                mid = entry.get("id")
                if isinstance(mid, str):
                    model_ids.add(mid)

    if not model_ids:
        result["error"] = f"model_discovery_empty: no models returned for provider {provider}"
        return result
    if model not in model_ids:
        result["error"] = f"model_not_found: {model}"
        return result

    result["available"] = True
    result["provider"] = provider
    result["model"] = model
    result["source"] = "explicit-override" if provider_override else "orchestration-preferences"
    return result


# ---------------------------------------------------------------------------
# Bridge trigger (finding #4, #5, #6)
# ---------------------------------------------------------------------------

def _read_bridge_trigger(
    context: WorktreeContext, task_id: str
) -> dict[str, Any] | None:
    """Read the Codex-authored bridge trigger from the coordination directory."""
    trigger_path = (
        context.root / ".harness" / "coordination" / task_id / "bridge-trigger.json"
    )
    try:
        ensure_no_link_components(context.root, trigger_path)
        data = read_bounded_json_object(
            trigger_path, MAX_STATE_BYTES, max_nodes=MAX_STATE_NODES
        )
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    if data.get("schema") != BRIDGE_SCHEMA:
        return None
    return data


def _validate_bridge_trigger(
    bridge: dict[str, Any],
    contract: dict[str, Any],
) -> list[str]:
    """Validate every frozen field of the bridge trigger matches the contract.

    Returns a list of mismatch labels (empty = valid).
    handoff_digest is NOT validated here — it is checked at dispatch time
    against the actual handoff file content.
    """
    errors: list[str] = []
    task = contract.get("task", {})
    execution = contract.get("execution", {})
    plan = contract.get("plan", {})
    lease = contract.get("writer_lease", {})

    def _check(field: str, expected: Any) -> None:
        actual = bridge.get(field)
        if actual != expected:
            errors.append(f"mismatch:{field}")

    _check("task_id", task.get("id"))
    _check("mode", "codex-paseo-claude")
    _check("triggered_by", "codex")
    _check("target_host", "claude")
    _check("native_invocation", "/implement")
    _check("canonical_worktree", execution.get("canonical_worktree"))
    _check("base_sha", execution.get("base_sha"))
    _check("branch", execution.get("branch"))
    _check("acceptance_owner", "codex")
    _check("manual_skill", "implement")

    bridge_lease = bridge.get("writer_lease", {})
    if (bridge_lease.get("holder") != lease.get("holder") or
            bridge_lease.get("state") != "active"):
        errors.append("mismatch:writer_lease")

    bridge_status = bridge.get("status", "")
    if bridge_status != "recorded-before-native-invocation":
        errors.append("mismatch:status")

    bridge_contract_digest = bridge.get("contract_digest", "")
    actual_digest = hashlib.sha256(
        json.dumps(contract, sort_keys=True, ensure_ascii=True).encode("utf-8")
    ).hexdigest()
    if bridge_contract_digest != actual_digest:
        errors.append("mismatch:contract_digest")

    # handoff_digest must be non-empty 64-lower-hex
    handoff_digest = bridge.get("handoff_digest", "")
    if not isinstance(handoff_digest, str) or len(handoff_digest) != 64:
        errors.append("missing_or_bad_length:handoff_digest")
    elif not all(c in "0123456789abcdef" for c in handoff_digest):
        errors.append("bad_hex:handoff_digest")

    return errors


# ---------------------------------------------------------------------------
# Live-agent identity validator (Slice 2 — reusable seam)
# ---------------------------------------------------------------------------

INSPECT_REQUIRED = frozenset({"Id", "Provider", "Model", "Mode", "Cwd", "Status", "Archived"})


def _validate_inspect(
    inspect_result: dict[str, Any],
    *,
    agent_id: str,
    provider: str,
    model: str,
    worktree: Path,
    expected_statuses: frozenset[str],
) -> str | None:
    """Validate live Paseo inspect result against frozen identity.

    Returns ``None`` when valid, or an error tag string on failure.
    Uses only the inspect result and caller-supplied expected values —
    never reads run state or persisted files.

    Archived must be present and explicitly ``False`` — missing or truthy
    values are rejected.
    """
    # Every required field must be a non-empty string (except Archived
    # which must be the boolean False — checked separately)
    string_fields = INSPECT_REQUIRED - {"Archived"}
    missing: list[str] = []
    for field in string_fields:
        v = inspect_result.get(field)
        if not isinstance(v, str) or not v:
            missing.append(field)
    # Archived must be explicitly False
    if inspect_result.get("Archived") is not False:
        missing.append("Archived")
    if missing:
        return f"inspect_missing_fields: {','.join(missing)}"

    if inspect_result["Id"] != agent_id:
        return f"inspect_id_mismatch: {inspect_result['Id']} != {agent_id}"
    if inspect_result["Provider"] != provider:
        return f"inspect_provider_mismatch: {inspect_result['Provider']}"
    if inspect_result["Model"] != model:
        return f"inspect_model_mismatch: {inspect_result['Model']} != {model}"
    if inspect_result["Mode"] != "bypassPermissions":
        return f"inspect_mode_mismatch: {inspect_result['Mode']}"
    if inspect_result["Status"] not in expected_statuses:
        return f"inspect_status_unexpected: {inspect_result['Status']}"

    # Cwd must resolve to the canonical worktree
    inspected_cwd = inspect_result.get("Cwd", "")
    if inspected_cwd and Path(inspected_cwd).resolve() != worktree.resolve():
        return "inspect_cwd_mismatch"

    return None


# ---------------------------------------------------------------------------
# Contract validation (finding #7)
# ---------------------------------------------------------------------------
# Manual-skill reminder (finding #6)
# ---------------------------------------------------------------------------

def _bridge_reminder_payload(
    task_id: str,
    already_reminded: bool,
) -> dict[str, Any]:
    """Single deduplicated bridge-trigger reminder."""
    return {
        "schema": PREFLIGHT_SCHEMA,
        "mode": "codex-paseo-claude",
        "state": "awaiting-user",
        "task_id": task_id,
        "manual_skill": {
            "name": "implement",
            "host": "claude",
            "native_invocation": "/implement",
            "status": "already-reminded" if already_reminded else "reminder-emitted",
        },
    }


# ---------------------------------------------------------------------------
# Bootstrap (finding #3, #4)
# ---------------------------------------------------------------------------

def paseo_bootstrap(
    context: WorktreeContext,
    contract: dict[str, Any],
    provider_override: str | None = None,
) -> tuple[dict[str, Any], int]:
    """Freeze a codex-paseo-claude run.

    1. Validate collaboration contract.
    2. Run read-only preflight.
    3. Read and validate bridge trigger.
    4. Create exactly one Paseo Claude agent with await-handoff prompt.
    5. Persist frozen run state with agent identity.
    """
    # --- early mode gate (before shared validator — the validator
    #     accepts all three modes but collaboration only serves one) ---
    collab_errors: list[str] = []
    execution = contract.get("execution", {}) if isinstance(contract, dict) else {}
    if not isinstance(execution, dict) or execution.get("mode") != "codex-paseo-claude":
        collab_errors.append("wrong_mode")
        return {
            "schema": RUN_SCHEMAS["codex-paseo-claude"],
            "state": "rejected",
            "errors": collab_errors,
        }, 2

    # --- contract validation (mode-agnostic shared validator) ---
    try:
        contract = validate_task_contract(contract)
    except ContractError as exc:
        return {
            "schema": RUN_SCHEMAS["codex-paseo-claude"],
            "state": "rejected",
            "error": str(exc),
        }, 2

    # --- collaboration-specific assertions ---
    execution = contract["execution"]
    if "branch" not in execution:
        collab_errors.append("missing_branch")
    if "plan" not in contract:
        collab_errors.append("missing_plan")
    if contract["state"] != "ready":
        collab_errors.append("not_ready")
    if contract["writer_lease"] != {"holder": "claude", "state": "inactive"}:
        collab_errors.append("lease_must_be_inactive_claude")
    if contract["acceptance_owner"] != "codex":
        collab_errors.append("wrong_acceptance_owner")
    skills = contract.get("required_manual_skills", [])
    implement_skill = [s for s in skills
                       if isinstance(s, dict) and s.get("name") == "implement"]
    if not implement_skill or implement_skill[0].get("host") != "claude":
        collab_errors.append("missing_implement_skill_gate")
    if collab_errors:
        return {
            "schema": RUN_SCHEMAS["codex-paseo-claude"],
            "state": "rejected",
            "errors": collab_errors,
        }, 2

    task_id = contract["task"]["id"]

    # --- authority freeze (live Git checks before agent creation) ---
    _reject_in_progress_git_operation(context)
    _reject_repository_filters(context.root, contract["plan"]["owned_paths"])

    head_sha = _git(context.root, "rev-parse", "HEAD").lower()
    if head_sha != execution["base_sha"].lower():
        return {
            "schema": RUN_SCHEMAS["codex-paseo-claude"],
            "state": "rejected",
            "error": "live HEAD does not match the contract base SHA",
        }, 2
    if _git(context.root, "branch", "--show-current") != execution["branch"]:
        return {
            "schema": RUN_SCHEMAS["codex-paseo-claude"],
            "state": "rejected",
            "error": "worktree branch does not match the contract branch",
        }, 2
    if execution["canonical_worktree"] != str(context.root.resolve()):
        return {
            "schema": RUN_SCHEMAS["codex-paseo-claude"],
            "state": "rejected",
            "error": "contract worktree does not match the current worktree",
        }, 2
    if _git(context.root, "status", "--porcelain=v1", "--untracked-files=all"):
        return {
            "schema": RUN_SCHEMAS["codex-paseo-claude"],
            "state": "rejected",
            "error": "worktree must be clean before writer acquisition",
        }, 2

    # --- preflight ---
    preflight_result = paseo_preflight(context, provider_override)
    if not preflight_result.get("available"):
        return {
            "schema": RUN_SCHEMAS["codex-paseo-claude"],
            "state": "rejected",
            "preflight": preflight_result,
            "error": preflight_result.get("error", "preflight_unavailable"),
        }, 1

    provider = preflight_result["provider"]
    model = preflight_result["model"]
    provider_model = f"{provider}/{model}"

    # --- bridge trigger ---
    bridge = _read_bridge_trigger(context, task_id)
    if bridge is None:
        try:
            already = _bridge_reminder_already_emitted(context, task_id, contract)
            _write_bridge_reminder(context, task_id, contract)
        except (OSError, ValueError) as exc:
            # Hardened persistence refused (link/junction, invalid marker,
            # capacity): bounded rejection, never a traceback.
            return {
                "schema": RUN_SCHEMAS["codex-paseo-claude"],
                "state": "rejected",
                "error": f"manual_skill_reminder_failed: {exc}",
            }, 2
        return _bridge_reminder_payload(task_id, already), 3

    handoff_digest = bridge.get("handoff_digest", "")
    bridge_errors = _validate_bridge_trigger(bridge, contract)
    if bridge_errors:
        return {
            "schema": RUN_SCHEMAS["codex-paseo-claude"],
            "state": "rejected",
            "bridge_errors": bridge_errors,
        }, 2

    # --- reject existing run before any agent/run write ---
    task_dir = _task_dir(context, task_id)
    run_path = task_dir / "run.json"
    if run_path.exists():
        return {
            "schema": RUN_SCHEMAS["codex-paseo-claude"],
            "state": "rejected",
            "error": "run_already_exists",
        }, 2

    # --- reject sibling worktree with same task/source lease ---
    known_roots = _git_worktree_roots(context)
    source_digest = _task_source_digest(contract)
    try:
        _reject_ticket_in_other_worktree(context, known_roots, task_id, source_digest)
    except CodexDirectError as exc:
        return {
            "schema": RUN_SCHEMAS["codex-paseo-claude"],
            "state": "rejected",
            "error": f"sibling_worktree_rejected: {exc}",
        }, 2

    # --- freeze durable run BEFORE external paseo run ---
    run_path, run = _make_fresh_run(
        context, contract, "", provider_model,
        bridge, handoff_digest,
    )
    # Mark agent as pending (not yet created)
    run["agent_state"] = "pending"
    _save_run(context, run_path, run)

    # --- create Paseo agent ---
    await_prompt = (
        "You are a Claude Code agent launched by Codex through Paseo. "
        "Wait for the implementation handoff to be dispatched. "
        "Do not analyze, inspect, or edit anything until the handoff arrives."
    )
    def _bootstrap_recovery(reason: str) -> tuple[dict[str, Any], int]:
        """Route bootstrap failures through the shared recovery path so a
        durable secret-free bundle always accompanies recovery-required.

        The raw reason is never persisted in the run record (the shared run
        shape has no error key); only the hashed fingerprint and category
        reach the Recovery Bundle."""
        run["agent_provider"] = provider_model
        _save_run(context, run_path, run)
        fingerprint = hashlib.sha256(
            f"adapter-failure-v1\0{reason}".encode("utf-8")
        ).hexdigest()
        return _enter_recovery_unlocked(
            context,
            task_id=task_id,
            category="adapter-failure",
            fingerprint=fingerprint,
            expected_mode="codex-paseo-claude",
        )

    try:
        run_result = _run_paseo_cli(
            "run",
            "--background",
            "--provider", provider_model,
            "--mode", "bypassPermissions",
            "--cwd", str(context.root),
            await_prompt,
            timeout=PASEO_RUN_TIMEOUT,
        )
    except PaseoCollaborationError as exc:
        return _bootstrap_recovery(f"agent_creation_failed: {exc}")

    if not isinstance(run_result, dict):
        return _bootstrap_recovery("agent_creation_unexpected_output")

    agent_id = run_result.get("id") or run_result.get("agentId") or ""
    if not isinstance(agent_id, str) or not agent_id:
        return _bootstrap_recovery("agent_creation_no_id")

    # --- validate agent via inspect (fail closed) ---
    try:
        inspect_result = _run_paseo_cli("inspect", agent_id)
    except PaseoCollaborationError:
        # Preserve the candidate agent identity before entering recovery.
        run["agent_id"] = agent_id
        return _bootstrap_recovery("agent_inspect_failed")

    if not isinstance(inspect_result, dict):
        # Preserve the candidate agent identity before entering recovery.
        run["agent_id"] = agent_id
        return _bootstrap_recovery("agent_inspect_unexpected_output")

    err = _validate_inspect(
        inspect_result,
        agent_id=agent_id,
        provider=provider,
        model=model,
        worktree=context.root,
        expected_statuses=frozenset({"idle", "active", "running"}),
    )
    if err is not None:
        # Preserve the candidate agent identity before entering recovery.
        run["agent_id"] = agent_id
        return _bootstrap_recovery(err)

    # --- bind agent identity to frozen run ---
    run["agent_id"] = agent_id
    run["agent_state"] = "active"
    run["agent_provider"] = provider_model
    _save_run(context, run_path, run)
    return _control(run), 0


def _make_fresh_run(
    context: WorktreeContext,
    contract: dict[str, Any],
    agent_id: str,
    provider_model: str,
    bridge: dict[str, Any],
    handoff_digest: str,
) -> tuple[Path, dict[str, Any]]:
    """Build a fresh run dict matching the shared Direct run shape.

    Adds collaboration-specific fields (agent_id, provider_routing,
    bridge_handoff_digest) on top of the canonical shape so the shared
    state/advance/record/judge/accept/commit machinery works unchanged.
    """
    from harness.codex_direct import _runtime_contract
    task_id = contract["task"]["id"]
    execution = contract["execution"]
    head_sha = execution["base_sha"].lower()
    run_path = _task_dir(context, task_id) / "run.json"

    # Mutable copy for runtime normalization
    contract["writer_lease"] = {"holder": "claude", "state": "active"}
    contract["state"] = "executing"
    frozen = _runtime_contract(context, contract)
    empty_digest = hashlib.sha256(b"").hexdigest()

    run: dict[str, Any] = {
        "schema": RUN_SCHEMAS["codex-paseo-claude"],
        "contract": frozen,
        "state": "executing",
        "sequence": 3,
        "history": [
            {"sequence": 1, "event": "mode-frozen", "state": "mode-frozen"},
            {"sequence": 2, "event": "baseline-verified", "state": "baselined"},
            {"sequence": 3, "event": "writer-acquired", "state": "executing"},
        ],
        "baseline": {
            "head_sha": head_sha,
            "branch": execution["branch"],
            "status_digest": empty_digest,
        },
        "checks": {},
        "evidence_log": [],
        "criteria": {},
        "risks": {},
        "repairs": [],
        "commit_sha": None,
        # Collaboration-specific fields
        "agent_id": agent_id,
        "bridge_handoff_digest": handoff_digest,
        "bridge_recorded_at": bridge.get("recorded_at", ""),
    }
    return run_path, run


def _bridge_reminder_already_emitted(
    context: WorktreeContext, task_id: str, contract: dict[str, Any]
) -> bool:
    """Repository-wide bridge-trigger reminder dedup via shared seam."""
    known_roots = _git_worktree_roots(context)
    source_digest = _task_source_digest(contract)
    return _manual_skill_was_reminded_elsewhere(
        context, known_roots,
        task_id=f"source:{source_digest}",
        adapter="codex-paseo-claude",
        host="claude",
        skill="implement",
    )


def _write_bridge_reminder(
    context: WorktreeContext, task_id: str, contract: dict[str, Any]
) -> None:
    """Persist the dedup marker through the hardened shared seam
    (link/junction refusal, bounded size/count, lock, durability re-read)
    so linked worktrees see the same reminder."""
    source_digest = _task_source_digest(contract)
    check_manual_skill(
        runtime_root=context.runtime_root,
        task_id=f"source:{source_digest}",
        adapter="codex-paseo-claude",
        host="claude",
        skill="implement",
        invoked=False,
        worktree_root=context.root,
    )


# ---------------------------------------------------------------------------
# Public bootstrap wrapper
# ---------------------------------------------------------------------------

def bootstrap(
    context: WorktreeContext,
    contract: dict[str, Any],
    provider_override: str | None = None,
) -> tuple[dict[str, Any], int]:
    """Bootstrap with repository mutex + lock identity wrapping.

    Follows the accepted ``start_direct`` lock protocol:
    identity from ``common_git_dir/config`` → bounded_file_lock →
    _repository_mutex → recheck → unlocked start → recheck.
    """
    # --- structural rejection before any nested indexing: malformed input
    #     returns bounded JSON, never a traceback, and never touches the
    #     repository lock or the Paseo CLI ---
    task = contract.get("task") if isinstance(contract, dict) else None
    if not isinstance(task, dict):
        return {
            "schema": RUN_SCHEMAS["codex-paseo-claude"],
            "state": "rejected",
            "error": "contract task is missing or invalid",
        }, 2
    task_id = task.get("id")
    if not isinstance(task_id, str) or not task_id:
        return {
            "schema": RUN_SCHEMAS["codex-paseo-claude"],
            "state": "rejected",
            "error": "contract task id is missing or invalid",
        }, 2
    task_dir = _task_dir(context, task_id)
    ensure_no_link_components(context.root, task_dir)
    repository_lock = context.common_git_dir / "config"
    if (
        not repository_lock.exists()
        or not repository_lock.is_file()
        or repository_lock.is_symlink()
        or repository_lock.stat().st_size == 0
    ):
        raise PaseoCollaborationError("repository control lock is unavailable")
    expected_lock_identity = _repository_lock_identity(repository_lock)
    with bounded_file_lock(task_dir / "run.lock"):
        with _repository_mutex(context, repository_lock):
            if _repository_lock_identity(repository_lock) != expected_lock_identity:
                raise PaseoCollaborationError(
                    "repository control lock changed before acquisition"
                )
            result = paseo_bootstrap(context, contract, provider_override)
            if _repository_lock_identity(repository_lock) != expected_lock_identity:
                control, exit_code = result
                if exit_code == 0:
                    # The Paseo agent may already be launched: Direct
                    # rollback would delete the frozen run. Preserve the
                    # writer and enter the normal collaboration Recovery
                    # Bundle path — never stop/restart the agent.
                    return _enter_recovery_unlocked(
                        context,
                        task_id=task_id,
                        category="adapter-failure",
                        fingerprint=hashlib.sha256(
                            b"adapter-failure-v1\0repository-lock-drift-post-launch"
                        ).hexdigest(),
                        expected_mode="codex-paseo-claude",
                    )
                _rollback_unstable_start(context, contract, result)
                raise PaseoCollaborationError(
                    "repository control lock changed during acquisition"
                )
            return result


# ---------------------------------------------------------------------------
# Dispatch (finding #4, #21)
# ---------------------------------------------------------------------------

def paseo_dispatch(
    context: WorktreeContext,
    task_id: str,
    handoff_path: Path,
) -> dict[str, Any]:
    """Dispatch the implementation handoff to the frozen Paseo agent.

    Serialized under per-task lock (Slice 3) — rejects a second caller or
    different agent identity.  Persists a prepared dispatch intent before the
    external send; only deletes it after launch evidence is durably written.
    """
    from harness.codex_direct import _write_json

    task_dir = _task_dir(context, task_id)
    launch_path = task_dir / "launch.json"
    pending_path = task_dir / "dispatch-pending.json"
    prompt_path = task_dir / "dispatch-prompt.txt"

    with bounded_file_lock(task_dir / "run.lock"):
        _run_path, run = _load_run(context, task_id, expected_mode="codex-paseo-claude")
        _unlink_ephemeral_prompt(context, prompt_path)

        if pending_path.exists() or launch_path.exists():
            raise PaseoCollaborationError("dispatch_already_completed")

        lease = run["contract"]["writer_lease"]
        if lease["holder"] != "claude" or lease["state"] != "active":
            raise PaseoCollaborationError("writer_lease_not_active")

        agent_id = run.get("agent_id")
        if not isinstance(agent_id, str) or not agent_id:
            raise PaseoCollaborationError("no_frozen_agent_id")

        # --- validate agent still exists via inspect (fail-closed) ---
        try:
            inspect_result = _run_paseo_cli("inspect", agent_id)
        except PaseoCollaborationError as exc:
            raise PaseoCollaborationError(f"agent_inspect_failed: {exc}") from exc

        if not isinstance(inspect_result, dict):
            raise PaseoCollaborationError("agent_inspect_unexpected_output")

        provider_model = run.get("agent_provider", "")
        provider, _, model = provider_model.partition("/")
        if not provider or not model:
            raise PaseoCollaborationError("frozen_agent_provider_missing")

        err = _validate_inspect(
            inspect_result,
            agent_id=agent_id,
            provider=provider,
            model=model,
            worktree=context.root,
            expected_statuses=frozenset({"idle", "active", "running"}),
        )
        if err is not None:
            raise PaseoCollaborationError(f"agent_identity_invalid: {err}")

        # --- validate bridge trigger still present ---
        bridge = _read_bridge_trigger(context, task_id)
        if bridge is None:
            raise PaseoCollaborationError("bridge_trigger_missing_at_dispatch")

        # --- read and validate handoff ---
        try:
            ensure_no_link_components(context.root, handoff_path)
        except OSError as exc:
            raise PaseoCollaborationError(f"handoff_unreadable: {exc}") from exc
        if not handoff_path.is_file():
            raise PaseoCollaborationError("handoff_unreadable")
        handoff_bytes = read_bounded_bytes(handoff_path, PROMPT_FILE_MAX_BYTES)
        if handoff_bytes is None:
            raise PaseoCollaborationError("handoff_oversized")
        try:
            handoff_text = handoff_bytes.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise PaseoCollaborationError("handoff_not_utf8") from exc

        # --- validate handoff against the FROZEN run record — the current
        #     bridge digest and the actual handoff bytes must both equal
        #     run["bridge_handoff_digest"]; mutable bridge state alone never
        #     authorizes outgoing instructions ---
        expected_handoff_digest = bridge.get("handoff_digest", "")
        if not isinstance(expected_handoff_digest, str) or len(expected_handoff_digest) != 64:
            raise PaseoCollaborationError("bridge_handoff_digest_missing_or_bad_length")
        if not all(c in "0123456789abcdef" for c in expected_handoff_digest):
            raise PaseoCollaborationError("bridge_handoff_digest_bad_hex")
        frozen_handoff_digest = run.get("bridge_handoff_digest", "")
        if expected_handoff_digest != frozen_handoff_digest:
            raise PaseoCollaborationError("bridge_handoff_digest_frozen_mismatch")
        actual_handoff_digest = hashlib.sha256(handoff_bytes).hexdigest()
        if actual_handoff_digest != frozen_handoff_digest:
            raise PaseoCollaborationError("handoff_digest_frozen_mismatch")

        # --- build dispatch prompt content (starts with /implement) ---
        prompt_content = f"/implement\n{handoff_text}"

        # --- at-most-once: persist the metadata-only prepared intent BEFORE
        #     prompt creation — a pending-write failure must leave no prompt
        #     bytes on disk ---
        pending_payload = {
            "schema": "harness.dispatch-pending/v1",
            "status": "prepared",
            "task_id": task_id,
            "mode": "codex-paseo-claude",
            "agent_id": agent_id,
            "prompt_digest": hashlib.sha256(
                prompt_content.encode("utf-8")
            ).hexdigest(),
            "prepared_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        _write_json(context, pending_path, pending_payload)

        # --- create prompt file and send (ephemeral across every exit) ---
        descriptor: int | None = None
        try:
            descriptor = _write_ephemeral_prompt(context, prompt_path, prompt_content)
            try:
                send_result = _send_verified_prompt(
                    agent_id, prompt_path, descriptor,
                )
            except PaseoCollaborationError as exc:
                # Keep pending sidecar — recovery inspects it
                raise PaseoCollaborationError(f"dispatch_send_failed: {exc}") from exc
        finally:
            # Fail-closed cleanup on EVERY exit: a prompt write, send, or
            # cleanup failure must not leave raw handoff text on disk, and
            # no launch evidence may follow a cleanup failure, so this
            # raises instead of swallowing OSError.
            _unlink_ephemeral_prompt(context, prompt_path, descriptor)

        # --- persist launch evidence ---
        launch: dict[str, Any] = {
            "schema": LAUNCH_SCHEMA,
            "task_id": task_id,
            "mode": "codex-paseo-claude",
            "agent_id": agent_id,
            "writer_lease": {"holder": "claude", "state": "active"},
            "acceptance_owner": "codex",
            # Opaque worktree identity only — never the absolute private cwd
            # (live inspect already proves cwd).
            "worktree_id": context.worktree_id,
            "dispatch_prompt_digest": hashlib.sha256(
                prompt_content.encode("utf-8")
            ).hexdigest(),
            "dispatch_send_digest": hashlib.sha256(
                json.dumps(_redact_evidence(send_result), sort_keys=True).encode("utf-8")
            ).hexdigest(),
            "handoff_digest": actual_handoff_digest,
            "dispatched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "tracked_provider_configuration_written": False,
            "remote_side_effect_authorized": False,
        }

        # --- at-most-once: persist launch BEFORE deleting pending ---
        _write_json(context, launch_path, launch)
        _unlink_nofollow(pending_path, missing_ok=True)
        return launch


def dispatch(
    context: WorktreeContext,
    task_id: str,
    handoff_path: Path,
) -> dict[str, Any]:
    """Validate task-id and handoff path, then persist launch evidence."""
    if not isinstance(task_id, str) or not task_id:
        raise PaseoCollaborationError("invalid_task_id")
    return paseo_dispatch(context, task_id, handoff_path)


# ---------------------------------------------------------------------------
# Collaboration guard (finding #7)
# ---------------------------------------------------------------------------


def collaboration_guard(
    context: WorktreeContext,
    task_id: str,
    action: str,
    actor: str,
    path: str | None = None,
) -> tuple[dict[str, Any], int]:
    """Actor-aware collaboration guard reusing ``guard_codex_direct``.

    Delegates to the shared guard for all action-class checks (push, PR,
    release, credential, SSH, broad delete, history rewrite, commit, edit,
    write, delete, rename, read, build, test, lint, package).  Adds
    collaboration-specific actor checks on top:
    - Codex write/delete/rename/edit on owned paths → blocked while Claude holds lease.
    - Claude write outside owned paths → blocked.
    - accept → Codex-only authorization (Claude denied), handled before shared delegation.
    - Claude commit/stage → blocked (Codex-owned).
    - Unknown actions fail closed.
    """
    # Validate actor inside the function, not only in argparse.
    if actor not in ("codex", "claude"):
        return {
            "schema": CONTROL_SCHEMAS["codex-paseo-claude"],
            "allowed": False,
            "reason": "invalid_actor",
        }, 1

    # ``stage`` is collaboration-specific — handled before shared delegation.
    if action == "stage":
        return {
            "schema": CONTROL_SCHEMAS["codex-paseo-claude"],
            "allowed": False,
            "reason": "stage_blocked_while_claude_lease_active",
        }, 1

    # ``accept`` is collaboration-specific — handled before shared
    # delegation so the outcome is deterministic for both actors (the
    # shared guard knows no ``accept`` action). The public acceptance
    # command itself remains fully gated by collaboration_accept.
    if action == "accept":
        if actor == "codex":
            return {
                "schema": CONTROL_SCHEMAS["codex-paseo-claude"],
                "allowed": True,
                "actor": actor,
                "action": action,
            }, 0
        return {
            "schema": CONTROL_SCHEMAS["codex-paseo-claude"],
            "allowed": False,
            "reason": "accept_is_codex_owned",
        }, 1

    # ``local-commit`` is Codex-owned: deny Claude before shared delegation
    # so an accepted run can never pass the actor-agnostic shared guard
    # through.  Codex behavior (state-gated by the shared guard) is unchanged.
    if action == "local-commit" and actor == "claude":
        return {
            "schema": CONTROL_SCHEMAS["codex-paseo-claude"],
            "allowed": False,
            "reason": "local_commit_is_codex_owned",
        }, 1

    # Reject unknown actions early — fail closed.
    if action not in COLLAB_GUARD_ACTIONS:
        return {
            "schema": CONTROL_SCHEMAS["codex-paseo-claude"],
            "allowed": False,
            "reason": "unknown_action",
        }, 1

    # Read-only reviewer actions — always allowed.
    if action in {"review", "verify", "explore"}:
        return {
            "schema": CONTROL_SCHEMAS["codex-paseo-claude"],
            "allowed": True,
            "actor": actor,
        }, 0

    writer_actions: set[str] = {"edit", "write", "delete", "rename"}
    try:
        shared, shared_ec = guard_codex_direct(
            context, task_id=task_id, action=action, path=path,
            expected_mode="codex-paseo-claude",
        )
    except (CodexDirectError, CodexDirectAdapterError):
        return {
            "schema": CONTROL_SCHEMAS["codex-paseo-claude"],
            "allowed": False,
            "reason": "guard_resolution_failed",
        }, 1

    if shared_ec != 0:
        return {
            "schema": CONTROL_SCHEMAS["codex-paseo-claude"],
            "allowed": False,
            **shared,
            "actor": actor,
        }, shared_ec

    # Shared guard passed — add collaboration-specific actor checks.
    _run_path, run = _load_run(context, task_id, expected_mode="codex-paseo-claude")
    owned_paths = run["contract"]["plan"]["owned_paths"]

    if actor == "codex" and action in writer_actions:
        if path is not None and _path_is_owned(path, owned_paths):
            return {
                "schema": CONTROL_SCHEMAS["codex-paseo-claude"],
                "allowed": False,
                "reason": "codex_cannot_edit_owned_path_while_claude_lease_active",
            }, 1

    if actor == "claude" and action in writer_actions:
        if path is not None and not _path_is_owned(path, owned_paths):
            return {
                "schema": CONTROL_SCHEMAS["codex-paseo-claude"],
                "allowed": False,
                "reason": "claude_write_outside_owned_paths",
            }, 1

    return {
        **shared,
        "actor": actor,
    }, 0


# ---------------------------------------------------------------------------
# Report (finding #9)
# ---------------------------------------------------------------------------

REQUIRED_REPORT_KEYS = frozenset({
    "task_id", "mode", "agent_id", "summary",
    "files_changed", "commands", "skipped_checks", "risks",
    "criterion_evidence",
})


def paseo_report(
    context: WorktreeContext,
    task_id: str,
    report_value: dict[str, Any],
) -> dict[str, Any]:
    """Validate a structured writer report.

    Requires exact bounded schema: non-empty summary, correct task/mode,
    matching agent identity, actual changed paths reconciled with
    ``files_changed``, required diff digest, command/result records,
    explicit skips with reasons, explicit risks, and exactly one evidence
    record per frozen criterion.
    """
    # --- schema validation (before run load) ---
    missing = REQUIRED_REPORT_KEYS - set(report_value)
    if missing:
        raise PaseoCollaborationError(f"report_missing_keys: {sorted(missing)}")

    # Reject extra keys — bounded schema only
    allowed = REQUIRED_REPORT_KEYS | {"schema", "diff_digest"}
    extra = set(report_value) - allowed
    if extra:
        raise PaseoCollaborationError(f"report_extra_keys: {sorted(extra)}")

    if report_value.get("schema") != REPORT_SCHEMA:
        raise PaseoCollaborationError("report_wrong_schema")

    if not isinstance(report_value.get("summary"), str) or not report_value["summary"].strip():
        raise PaseoCollaborationError("report_summary_empty")

    if report_value.get("task_id") != task_id:
        raise PaseoCollaborationError("report_task_id_mismatch")
    if report_value.get("mode") != "codex-paseo-claude":
        raise PaseoCollaborationError("report_mode_mismatch")

    # --- run and launch evidence (frozen-writer binding: the launch
    #     sidecar is mutable — bind it to run.json, never the reverse) ---
    _run_path, run = _load_run(context, task_id, expected_mode="codex-paseo-claude")

    launch_path = _task_dir(context, task_id) / "launch.json"
    if not launch_path.exists():
        raise PaseoCollaborationError("no_launch_evidence_for_report")
    launch = read_bounded_json_object(
        launch_path, MAX_STATE_BYTES, max_nodes=MAX_STATE_NODES
    )
    if not isinstance(launch, dict):
        raise PaseoCollaborationError("report_launch_not_object")
    if launch.get("schema") != LAUNCH_SCHEMA:
        raise PaseoCollaborationError("report_launch_schema_invalid")
    if launch.get("task_id") != task_id:
        raise PaseoCollaborationError("report_launch_task_id_mismatch")
    if launch.get("mode") != "codex-paseo-claude":
        raise PaseoCollaborationError("report_launch_mode_mismatch")
    frozen_agent_id = run.get("agent_id")
    if not isinstance(frozen_agent_id, str) or not frozen_agent_id:
        raise PaseoCollaborationError("report_missing_frozen_agent_id")
    if launch.get("agent_id") != frozen_agent_id:
        raise PaseoCollaborationError("report_launch_agent_id_mismatch")
    if launch.get("handoff_digest") != run.get("bridge_handoff_digest", ""):
        raise PaseoCollaborationError("report_launch_handoff_digest_mismatch")
    if report_value.get("agent_id") != frozen_agent_id:
        raise PaseoCollaborationError("report_agent_id_mismatch")

    # --- path ownership ---
    files_changed = report_value.get("files_changed", [])
    if not isinstance(files_changed, list):
        raise PaseoCollaborationError("report_files_changed_not_list")
    owned_paths = run["contract"]["plan"]["owned_paths"]
    for p in files_changed:
        if not isinstance(p, str):
            raise PaseoCollaborationError("report_files_changed_item_not_string")
        if not _path_is_owned(p, owned_paths):
            raise PaseoCollaborationError(f"report_unowned_path: {p}")

    # --- diff digest reconciliation ---
    actual_paths = _changed_paths(context.root)
    actual_diff_digest = _diff_digest(context.root)
    report_digest = report_value.get("diff_digest")
    if not isinstance(report_digest, str) or report_digest != actual_diff_digest:
        raise PaseoCollaborationError("report_diff_digest_mismatch")
    if sorted(files_changed) != sorted(actual_paths):
        raise PaseoCollaborationError("report_paths_diverge_from_actual_diff")

    # --- commands (secret-free) ---
    COMMAND_ALLOWED_KEYS = frozenset({"id", "digest", "status", "exit_code"})
    FORBIDDEN_COMMAND_KEYS = frozenset({
        "raw", "stdout", "stderr", "env", "path", "token",
        "cookie", "prompt", "command", "output",
    })
    commands = report_value.get("commands", [])
    if not isinstance(commands, list):
        raise PaseoCollaborationError("report_commands_not_list")
    if not commands:
        raise PaseoCollaborationError("report_commands_empty")
    for i, cmd in enumerate(commands):
        if not isinstance(cmd, dict):
            raise PaseoCollaborationError("report_command_not_dict")
        cmd_keys = set(cmd)
        forbidden = cmd_keys & FORBIDDEN_COMMAND_KEYS
        if forbidden:
            raise PaseoCollaborationError(
                f"report_command_{i}_forbidden_keys: {sorted(forbidden)}"
            )
        extra = cmd_keys - COMMAND_ALLOWED_KEYS
        if extra:
            raise PaseoCollaborationError(
                f"report_command_{i}_extra_keys: {sorted(extra)}"
            )
        # Exact metadata-only shape: runtime-safe ID, canonical digest,
        # pass|fail status, signed 32-bit non-bool exit code, consistency.
        if "id" not in cmd or not _is_safe_identifier(cmd["id"]):
            raise PaseoCollaborationError(f"report_command_{i}_bad_id")
        if not _is_hex64(cmd.get("digest")):
            raise PaseoCollaborationError(f"report_command_{i}_bad_digest")
        status = cmd.get("status")
        if status not in ("pass", "fail"):
            raise PaseoCollaborationError(f"report_command_{i}_bad_status")
        exit_code = cmd.get("exit_code")
        if (
            not isinstance(exit_code, int)
            or isinstance(exit_code, bool)
            or not -(2**31) <= exit_code < 2**31
        ):
            raise PaseoCollaborationError(f"report_command_{i}_bad_exit_code")
        if (status == "pass") != (exit_code == 0):
            raise PaseoCollaborationError(f"report_command_{i}_status_exit_mismatch")

    # --- skipped checks (exact key set; reason persisted as digest only) ---
    skipped = report_value.get("skipped_checks", [])
    if not isinstance(skipped, list):
        raise PaseoCollaborationError("report_skipped_checks_not_list")
    skip_ids: set[str] = set()
    projected_skips: list[dict[str, Any]] = []
    for i, s in enumerate(skipped):
        if not isinstance(s, dict):
            raise PaseoCollaborationError("report_skip_not_dict")
        if "id" not in s or not isinstance(s["id"], str) or not s["id"]:
            raise PaseoCollaborationError(f"report_skip_{i}_missing_id")
        if not _is_safe_identifier(s["id"]):
            raise PaseoCollaborationError(f"report_skip_{i}_bad_id")
        reason = s.get("reason")
        if not isinstance(reason, str) or not reason:
            raise PaseoCollaborationError(f"report_skip_{i}_missing_reason")
        if len(reason.encode("utf-8")) > REPORT_TEXT_MAX_BYTES:
            raise PaseoCollaborationError(f"report_skip_{i}_reason_oversized")
        extra = set(s) - {"id", "reason"}
        if extra:
            raise PaseoCollaborationError(
                f"report_skip_{i}_extra_keys: {sorted(extra)}"
            )
        if s["id"] in skip_ids:
            raise PaseoCollaborationError(f"report_skip_duplicate_id: {s['id']}")
        skip_ids.add(s["id"])
        projected_skips.append({
            "id": s["id"],
            "reason_digest": hashlib.sha256(reason.encode("utf-8")).hexdigest(),
        })

    # --- risks (exact key set; detail persisted as digest only) ---
    risks = report_value.get("risks", [])
    if not isinstance(risks, list):
        raise PaseoCollaborationError("report_risks_not_list")
    risk_ids: set[str] = set()
    projected_risks: list[dict[str, Any]] = []
    for i, r in enumerate(risks):
        if not isinstance(r, dict):
            raise PaseoCollaborationError("report_risk_not_dict")
        if "id" not in r or not isinstance(r["id"], str) or not r["id"]:
            raise PaseoCollaborationError(f"report_risk_{i}_missing_id")
        if not _is_safe_identifier(r["id"]):
            raise PaseoCollaborationError(f"report_risk_{i}_bad_id")
        extra = set(r) - {"id", "detail"}
        if extra:
            raise PaseoCollaborationError(
                f"report_risk_{i}_extra_keys: {sorted(extra)}"
            )
        if "detail" in r and not isinstance(r["detail"], str):
            raise PaseoCollaborationError(f"report_risk_{i}_bad_detail")
        if r["id"] in risk_ids:
            raise PaseoCollaborationError(f"report_risk_duplicate_id: {r['id']}")
        risk_ids.add(r["id"])
        projected = {"id": r["id"]}
        if "detail" in r:
            detail = r["detail"]
            if len(detail.encode("utf-8")) > REPORT_TEXT_MAX_BYTES:
                raise PaseoCollaborationError(f"report_risk_{i}_detail_oversized")
            projected["detail_digest"] = hashlib.sha256(
                detail.encode("utf-8")
            ).hexdigest()
        projected_risks.append(projected)

    # --- criterion evidence (deduplicate explicitly, reject duplicates) ---
    criteria = run["contract"]["plan"]["acceptance_criteria"]
    evidence_list = report_value.get("criterion_evidence", [])
    if not isinstance(evidence_list, list):
        raise PaseoCollaborationError("report_criterion_evidence_not_list")
    criterion_ids = {c["id"] for c in criteria}
    evidence_ids_seen: set[str] = set()
    projected_evidence: list[dict[str, Any]] = []
    for i, ev in enumerate(evidence_list):
        if not isinstance(ev, dict):
            raise PaseoCollaborationError("report_evidence_not_dict")
        eid = ev.get("id")
        if eid not in criterion_ids:
            raise PaseoCollaborationError(f"report_evidence_unknown_criterion: {eid}")
        if eid in evidence_ids_seen:
            raise PaseoCollaborationError(f"report_evidence_duplicate_id: {eid}")
        evidence_ids_seen.add(eid)
        if ev.get("status") not in ("pass", "fail"):
            raise PaseoCollaborationError("report_evidence_bad_status")
        if not _is_hex64(ev.get("digest")):
            raise PaseoCollaborationError("report_evidence_bad_digest")
        extra = set(ev) - {"id", "status", "digest"}
        if extra:
            raise PaseoCollaborationError(
                f"report_evidence_{i}_extra_keys: {sorted(extra)}"
            )
        projected_evidence.append(
            {"id": ev["id"], "status": ev["status"], "digest": ev["digest"]}
        )
    if evidence_ids_seen != criterion_ids:
        raise PaseoCollaborationError("report_evidence_missing_or_extra_criterion")

    # --- writer must be idle or stopped (live inspect of the frozen ID) ---
    report_agent_id = frozen_agent_id
    provider_model = run.get("agent_provider", "")
    provider, _, model = provider_model.partition("/")
    if not provider or not model:
        raise PaseoCollaborationError("run_missing_agent_provider")
    try:
        inspect_result = _run_paseo_cli(
            "inspect", report_agent_id, "--json", timeout=PASEO_TIMEOUT,
        )
    except PaseoCollaborationError as exc:
        raise PaseoCollaborationError(f"report_inspect_failed: {exc}") from exc
    if not isinstance(inspect_result, dict):
        raise PaseoCollaborationError("report_inspect_not_dict")
    err = _validate_inspect(
        inspect_result, agent_id=report_agent_id, provider=provider,
        model=model, worktree=context.root,
        expected_statuses=frozenset({"idle", "stopped"}),
    )
    if err is not None:
        raise PaseoCollaborationError(f"report_inspect_invalid: {err}")
    # Update persisted agent_state from live inspect
    run["agent_state"] = inspect_result.get("Status", run.get("agent_state", ""))

    # --- persist normalized metadata-only object ---
    summary_digest = hashlib.sha256(
        report_value["summary"].encode("utf-8")
    ).hexdigest()
    normalized = {
        "schema": REPORT_SCHEMA,
        "task_id": task_id,
        "mode": "codex-paseo-claude",
        "agent_id": frozen_agent_id,
        "summary_digest": summary_digest,
        "files_changed": files_changed,
        "diff_digest": actual_diff_digest,
        "commands": commands,
        "skipped_checks": projected_skips,
        "risks": projected_risks,
        "criterion_evidence": projected_evidence,
        "launch_digest": _launch_digest(launch),
    }
    report_path = _task_dir(context, task_id) / "report.json"
    from harness.codex_direct import _write_json
    _write_json(context, report_path, normalized)
    return {
        "schema": REPORT_SCHEMA,
        "status": "valid",
        "task_id": task_id,
        "summary_digest": summary_digest,
    }


def report(
    context: WorktreeContext,
    task_id: str,
    report_value: dict[str, Any],
) -> dict[str, Any]:
    """Validate task-id and report value, then persist report evidence."""
    if not isinstance(task_id, str) or not task_id:
        raise PaseoCollaborationError("invalid_task_id")
    return paseo_report(context, task_id, report_value)


# ---------------------------------------------------------------------------
# Repair (finding #10)
# ---------------------------------------------------------------------------

def paseo_repair(
    context: WorktreeContext,
    task_id: str,
    review_path: Path,
) -> tuple[dict[str, Any], int]:
    """Route a bounded review prompt to the frozen Paseo agent.

    Serialized under per-task lock (Slice 5) — rejects duplicate/ambiguous
    repair.  Persists a prepared repair intent before send; deletes it only
    after dispatch evidence is durably written.
    """
    from harness.codex_direct import _write_json

    task_dir = _task_dir(context, task_id)
    prompt_path = task_dir / "repair-prompt.txt"

    with bounded_file_lock(task_dir / "run.lock"):
        _run_path, run = _load_run(context, task_id, expected_mode="codex-paseo-claude")
        _unlink_ephemeral_prompt(context, prompt_path)

        # --- attempt-keyed evidence: a completed prior attempt never blocks
        #     the next authorized one; only a prepared intent for the
        #     current attempt blocks replay ---
        attempt_number = len(run["repairs"]) + 1
        repair_pending_path = task_dir / f"repair-pending-{attempt_number}.json"
        repair_dispatch_path = task_dir / f"repair-dispatch-{attempt_number}.json"
        if repair_pending_path.exists():
            raise PaseoCollaborationError("repair_already_pending")

        # --- every RECORDED repair must have been delivered: a crash after
        #     _begin_repair_unlocked but before the sidecar write leaves an
        #     undelivered entry that must block further repair ---
        undelivered = _validate_repair_deliveries(task_dir, run, task_id)
        if undelivered:
            raise PaseoCollaborationError(
                f"repair_blocked_undelivered_prior_attempt: {undelivered}"
            )

        agent_id = run.get("agent_id")
        if not isinstance(agent_id, str) or not agent_id:
            raise PaseoCollaborationError("no_frozen_agent_id_for_repair")

        # --- live agent identity check ---
        provider_model = run.get("agent_provider", "")
        provider, _, model = provider_model.partition("/")
        if not provider or not model:
            raise PaseoCollaborationError("run_missing_agent_provider")
        try:
            inspect_result = _run_paseo_cli(
                "inspect", agent_id, "--json", timeout=PASEO_TIMEOUT,
            )
        except PaseoCollaborationError as exc:
            raise PaseoCollaborationError(f"repair_inspect_failed: {exc}") from exc
        if not isinstance(inspect_result, dict):
            raise PaseoCollaborationError("repair_inspect_not_dict")
        err = _validate_inspect(
            inspect_result, agent_id=agent_id, provider=provider,
            model=model, worktree=context.root,
            expected_statuses=frozenset({"idle", "active", "running"}),
        )
        if err is not None:
            raise PaseoCollaborationError(f"repair_inspect_invalid: {err}")

        # --- read review file ---
        try:
            ensure_no_link_components(context.root, review_path)
        except OSError as exc:
            raise PaseoCollaborationError(f"review_file_unreadable: {exc}") from exc
        if not review_path.is_file():
            raise PaseoCollaborationError("review_file_unreadable")
        review_bytes = read_bounded_bytes(review_path, PROMPT_FILE_MAX_BYTES)
        if review_bytes is None:
            raise PaseoCollaborationError("review_file_oversized")
        try:
            review_text = review_bytes.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise PaseoCollaborationError("review_not_utf8") from exc

        review_digest = hashlib.sha256(review_bytes).hexdigest()
        fingerprint = _require_digest(review_digest, "review digest")

        # --- check eligibility (unlocked core — we already hold run.lock) ---
        control, ec = _begin_repair_unlocked(
            context,
            task_id=task_id,
            fingerprint=fingerprint,
            expected_mode="codex-paseo-claude",
        )
        if ec != 0:
            return control, ec

        # --- persist prepared repair intent before external send ---
        pending_payload = {
            "schema": "harness.repair-pending/v1",
            "status": "prepared",
            "task_id": task_id,
            "mode": "codex-paseo-claude",
            "agent_id": agent_id,
            "attempt": attempt_number,
            "fingerprint": fingerprint,
            "prepared_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        _write_json(context, repair_pending_path, pending_payload)

        # --- create prompt file and send (ephemeral across every exit) ---
        descriptor: int | None = None
        try:
            descriptor = _write_ephemeral_prompt(context, prompt_path, review_text)
            try:
                send_result = _send_verified_prompt(
                    agent_id, prompt_path, descriptor,
                )
            except PaseoCollaborationError as exc:
                # Keep pending — recovery inspects it
                raise PaseoCollaborationError(f"repair_send_failed: {exc}") from exc
        finally:
            # Fail-closed cleanup on EVERY exit: a prompt write, send, or
            # cleanup failure must not leave raw review text on disk, and
            # no repair-dispatch evidence may follow a cleanup failure.
            _unlink_ephemeral_prompt(context, prompt_path, descriptor)

        # --- persist repair dispatch evidence, then clear pending ---
        dispatch_evidence: dict[str, Any] = {
            "schema": "harness.repair-dispatch/v1",
            "task_id": task_id,
            "mode": "codex-paseo-claude",
            "agent_id": agent_id,
            "attempt": attempt_number,
            "fingerprint": fingerprint,
            "send_digest": hashlib.sha256(
                json.dumps(_redact_evidence(send_result), sort_keys=True).encode("utf-8")
            ).hexdigest(),
            "dispatched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        _write_json(context, repair_dispatch_path, dispatch_evidence)
        _unlink_nofollow(repair_pending_path, missing_ok=True)

        return control, ec


def repair(
    context: WorktreeContext,
    task_id: str,
    review_path: Path,
) -> tuple[dict[str, Any], int]:
    """Validate task-id and review path, then route repair to Paseo agent."""
    if not isinstance(task_id, str) or not task_id:
        raise PaseoCollaborationError("invalid_task_id")
    return paseo_repair(context, task_id, review_path)


# ---------------------------------------------------------------------------
# Recovery (finding #11)
# ---------------------------------------------------------------------------

def paseo_recover(
    context: WorktreeContext,
    task_id: str,
    category: str,
    fingerprint: str,
) -> tuple[dict[str, Any], int]:
    """Enter recovery — preserve mode, lease, agent identity, and evidence.

    Never restarts a daemon, releases/transfers the lease, or invokes
    another adapter.
    """
    return enter_recovery(
        context,
        task_id=task_id,
        category=category,
        fingerprint=fingerprint,
        expected_mode="codex-paseo-claude",
    )


def recover(
    context: WorktreeContext,
    task_id: str,
    category: str,
    fingerprint: str,
) -> tuple[dict[str, Any], int]:
    """Validate inputs then delegate to shared recovery."""
    if not isinstance(task_id, str) or not task_id:
        raise PaseoCollaborationError("invalid_task_id")
    _require_digest(fingerprint, "recovery fingerprint")
    return paseo_recover(context, task_id, category, fingerprint)


# ---------------------------------------------------------------------------
# Shared controller wrappers (finding #13)
# ---------------------------------------------------------------------------

def collaboration_status(
    context: WorktreeContext, task_id: str
) -> dict[str, Any]:
    from harness.codex_direct import codex_direct_status
    return codex_direct_status(
        context, task_id=task_id, expected_mode="codex-paseo-claude"
    )


def collaboration_advance(
    context: WorktreeContext, task_id: str, target: str
) -> dict[str, Any]:
    from harness.codex_direct import advance_codex_direct
    return advance_codex_direct(
        context, task_id=task_id, target=target,
        expected_mode="codex-paseo-claude",
    )


def collaboration_record_check(
    context: WorktreeContext, *, task_id: str, check_id: str,
    status: str, source: str, exit_code: int | None,
    sensitivity: str, digest: str, reason_code: str | None,
) -> dict[str, Any]:
    from harness.codex_direct import record_check
    return record_check(
        context, task_id=task_id, check_id=check_id,
        status=status, source=source, exit_code=exit_code,
        sensitivity=sensitivity, digest=digest,
        reason_code=reason_code, expected_mode="codex-paseo-claude",
    )


def collaboration_judge(
    context: WorktreeContext, *, task_id: str,
    criterion_id: str, status: str, evidence_digest: str,
) -> dict[str, Any]:
    from harness.codex_direct import judge_criterion
    return judge_criterion(
        context, task_id=task_id, criterion_id=criterion_id,
        status=status, evidence_digest=evidence_digest,
        expected_mode="codex-paseo-claude",
    )


def collaboration_record_risk(
    context: WorktreeContext, *, task_id: str,
    risk_id: str, severity: str, status: str, digest: str,
) -> dict[str, Any]:
    from harness.codex_direct import record_risk
    return record_risk(
        context, task_id=task_id, risk_id=risk_id,
        severity=severity, status=status, digest=digest,
        expected_mode="codex-paseo-claude",
    )


def collaboration_accept(
    context: WorktreeContext, *, task_id: str,
    message: str = "chore(harness): create accepted ticket commit",
) -> dict[str, Any]:
    """Collaboration acceptance: validated launch + report evidence, live
    idle/stopped proof, and no pending/ambiguous dispatch or repair.
    Delegates to shared ``_accept_codex_direct_unlocked`` under ``run.lock``."""
    task_dir = _task_dir(context, task_id)
    with bounded_file_lock(task_dir / "run.lock"):
        # --- pending dispatch/repair check ---
        launch_path = task_dir / "launch.json"
        dispatch_pending_path = task_dir / "dispatch-pending.json"
        if dispatch_pending_path.exists() and not launch_path.exists():
            raise PaseoCollaborationError("acceptance_blocked_by_pending_dispatch")
        for pending in sorted(task_dir.glob("repair-pending-*.json")):
            attempt_tag = pending.name[len("repair-pending-"):-len(".json")]
            if not (task_dir / f"repair-dispatch-{attempt_tag}.json").exists():
                raise PaseoCollaborationError("acceptance_blocked_by_pending_repair")

        if not launch_path.exists():
            raise PaseoCollaborationError("acceptance_requires_launch_evidence")
        report_path = task_dir / "report.json"
        if not report_path.exists():
            raise PaseoCollaborationError("acceptance_requires_report_evidence")

        launch = read_bounded_json_object(
            launch_path, MAX_STATE_BYTES, max_nodes=MAX_STATE_NODES
        )
        if not isinstance(launch, dict):
            raise PaseoCollaborationError("acceptance_launch_not_object")
        if launch.get("schema") != LAUNCH_SCHEMA:
            raise PaseoCollaborationError("acceptance_launch_schema_invalid")
        if launch.get("task_id") != task_id:
            raise PaseoCollaborationError("acceptance_launch_task_id_mismatch")
        report = read_bounded_json_object(
            report_path, MAX_STATE_BYTES, max_nodes=MAX_STATE_NODES
        )
        if not isinstance(report, dict):
            raise PaseoCollaborationError("acceptance_report_not_object")
        if report.get("schema") != REPORT_SCHEMA:
            raise PaseoCollaborationError("acceptance_report_schema_invalid")
        if report.get("task_id") != task_id:
            raise PaseoCollaborationError("acceptance_report_task_id_mismatch")

        # --- identity/digest binding: everything must equal the frozen run
        #     record, never mutable sidecar launch.json alone ---
        _run_path, run = _load_run(context, task_id, expected_mode="codex-paseo-claude")
        frozen_agent_id = run.get("agent_id")
        if not isinstance(frozen_agent_id, str) or not frozen_agent_id:
            raise PaseoCollaborationError("accept_missing_frozen_agent_id")
        if launch.get("agent_id") != frozen_agent_id:
            raise PaseoCollaborationError("acceptance_launch_agent_id_mismatch")
        if report.get("agent_id") != frozen_agent_id:
            raise PaseoCollaborationError("acceptance_report_agent_id_mismatch")
        report_launch_digest = report.get("launch_digest")
        if report_launch_digest != _launch_digest(launch):
            raise PaseoCollaborationError("acceptance_report_launch_digest_mismatch")
        frozen_handoff_digest = run.get("bridge_handoff_digest", "")
        if launch.get("handoff_digest") != frozen_handoff_digest:
            raise PaseoCollaborationError("acceptance_handoff_digest_mismatch")
        bridge = _read_bridge_trigger(context, task_id)
        if bridge is None:
            raise PaseoCollaborationError("acceptance_bridge_trigger_missing")
        if bridge.get("handoff_digest") != frozen_handoff_digest:
            raise PaseoCollaborationError("acceptance_bridge_handoff_digest_mismatch")

        # --- current report: the normalized report must describe the
        #     CURRENT Git diff — a pre-repair report cannot authorize a
        #     later diff ---
        current_diff_digest = _diff_digest(context.root)
        current_paths = _changed_paths(context.root)
        if report.get("diff_digest") != current_diff_digest:
            raise PaseoCollaborationError("acceptance_diff_changed_since_report")
        if sorted(report.get("files_changed") or []) != sorted(current_paths):
            raise PaseoCollaborationError("acceptance_paths_changed_since_report")

        # --- every RECORDED repair must have matching dispatch evidence ---
        undelivered = _validate_repair_deliveries(task_dir, run, task_id)
        if undelivered:
            raise PaseoCollaborationError(
                f"acceptance_blocked_by_undelivered_repair: {undelivered}"
            )

        # --- live agent identity: must be idle/stopped, same frozen agent ---
        provider_model = run.get("agent_provider", "")
        provider, _, model = provider_model.partition("/")
        if not provider or not model:
            raise PaseoCollaborationError("accept_missing_agent_provider")
        try:
            inspect_result = _run_paseo_cli(
                "inspect", frozen_agent_id, "--json", timeout=PASEO_TIMEOUT,
            )
        except PaseoCollaborationError as exc:
            raise PaseoCollaborationError(f"accept_inspect_failed: {exc}") from exc
        if not isinstance(inspect_result, dict):
            raise PaseoCollaborationError("accept_inspect_not_dict")
        err = _validate_inspect(
            inspect_result, agent_id=frozen_agent_id, provider=provider,
            model=model, worktree=context.root,
            expected_statuses=frozenset({"idle", "stopped"}),
        )
        if err is not None:
            raise PaseoCollaborationError(f"accept_inspect_invalid: {err}")

        return _accept_codex_direct_unlocked(
            context, task_id=task_id, message=message,
            expected_mode="codex-paseo-claude",
        )


def collaboration_commit(
    context: WorktreeContext, *, task_id: str, message: str,
) -> dict[str, Any]:
    from harness.codex_direct import commit_codex_direct
    return commit_codex_direct(
        context, task_id=task_id, message=message,
        expected_mode="codex-paseo-claude",
    )


# ---------------------------------------------------------------------------
# Evidence redaction (addendum finding #1)
# ---------------------------------------------------------------------------

def _redact_evidence(data: Any) -> Any:
    """Strip secret-bearing fields from runtime evidence.

    Returns a copy with redacted keys removed and absolute paths replaced
    with relative-stem digests.  Never mutates the input.
    """
    if isinstance(data, dict):
        result: dict[str, Any] = {}
        for k, v in data.items():
            if k in REDACTED_KEYS:
                continue
            result[k] = _redact_evidence(v)
        return result
    if isinstance(data, list):
        return [_redact_evidence(item) for item in data]
    if isinstance(data, str) and (
        data.startswith("C:\\") or data.startswith("/") or data.startswith("\\\\")
    ):
        # Replace absolute path with its SHA-256 digest
        return hashlib.sha256(data.encode("utf-8")).hexdigest()[:16]
    return data


# ---------------------------------------------------------------------------
# Public aliases
# ---------------------------------------------------------------------------

preflight = paseo_preflight
