"""Persistent shared control loop for direct accepted-ticket adapters."""

from __future__ import annotations

import copy
import hashlib
import itertools
import json
import os
import re
import stat
import subprocess
import tempfile
import threading
from contextlib import contextmanager
from functools import wraps
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Iterator

from harness.capabilities import check_manual_skill, manual_skill_reminder_id
from harness.context import WorktreeContext, git_environment
from harness.contracts import ACCEPTANCE_OWNERS, WRITERS, validate_direct_contract
from harness.safe_io import (
    _hold_windows_directory_chain,
    _open_directory_nofollow,
    _unlink_nofollow,
    bounded_file_lock,
    ensure_no_link_components,
    read_bounded_bytes,
    read_bounded_json_object,
    validate_json_shape,
    write_bounded_text,
)


class CodexDirectError(ValueError):
    """The Codex Direct controller rejected a task operation."""


class CodexDirectAdapterError(CodexDirectError):
    """The active adapter failed after task execution began."""


ORDINARY_ACTIONS = {"read", "edit", "write", "delete", "rename", "build", "test", "lint", "package"}
USER_AUTH_ACTIONS = {"push", "pull-request", "tag", "release", "publish"}
BLOCKED_ACTIONS = {"broad-delete", "history-rewrite", "credential", "ssh"}
GUARDED_ACTIONS = ORDINARY_ACTIONS | USER_AUTH_ACTIONS | BLOCKED_ACTIONS | {
    "local-commit"
}
RUNTIME_ID_RE = re.compile(r"^[A-Za-z0-9_.:#-]+$")
MAX_STATE_BYTES = 512 * 1024
MAX_STATE_NODES = 20_000
MAX_RISKS = 128
MAX_EVIDENCE_RECORDS = 384
MAX_ACCEPTED_PATHS = 256
MAX_ACCEPTED_PATH_BYTES = 16 * 1024
MAX_GIT_OUTPUT_BYTES = 8 * 1024 * 1024
MAX_INDEX_BYTES = 64 * 1024 * 1024
MAX_REPOSITORY_TASKS = 1024
DIRECT_MODES = ("codex-direct", "claude-direct", "codex-paseo-claude")
RUN_SCHEMAS = {
    "codex-direct": "harness.codex-direct-run/v1",
    "claude-direct": "harness.claude-direct-run/v1",
    "codex-paseo-claude": "harness.codex-paseo-claude-run/v1",
}
CONTROL_SCHEMAS = {
    "codex-direct": "harness.codex-direct-control/v1",
    "claude-direct": "harness.claude-direct-control/v1",
    "codex-paseo-claude": "harness.codex-paseo-claude-control/v1",
}
GIT_SAFE_CONFIG = (
    "-c",
    f"core.hooksPath={os.devnull}",
    "-c",
    "core.fsmonitor=false",
)


def _direct_mode(contract: Any) -> str:
    execution = contract.get("execution") if isinstance(contract, dict) else None
    mode = execution.get("mode") if isinstance(execution, dict) else None
    if mode not in DIRECT_MODES:
        raise CodexDirectError("direct task mode is unavailable or invalid")
    return mode


def _git(
    root: Path, *args: str, env_overrides: dict[str, str] | None = None
) -> str:
    raw = _run_git_bytes(root, args, env_overrides=env_overrides)
    try:
        return raw.decode("utf-8", errors="strict").strip()
    except UnicodeDecodeError as exc:
        raise CodexDirectAdapterError("canonical worktree Git output is invalid") from exc


def _git_bytes(
    root: Path, *args: str, env_overrides: dict[str, str] | None = None
) -> bytes:
    return _run_git_bytes(root, args, env_overrides=env_overrides)


def _run_git_bytes(
    root: Path,
    args: tuple[str, ...],
    allowed_codes: set[int] | None = None,
    input_bytes: bytes | None = None,
    env_overrides: dict[str, str] | None = None,
) -> bytes:
    chunks: list[bytes] = []
    overflow = threading.Event()
    read_error: list[OSError] = []
    try:
        if input_bytes is not None and len(input_bytes) > MAX_GIT_OUTPUT_BYTES:
            raise CodexDirectError("canonical worktree Git input exceeds its bound")
        environment = git_environment()
        if env_overrides:
            environment.update(env_overrides)
        process = subprocess.Popen(
            ["git", "-C", str(root), *GIT_SAFE_CONFIG, *args],
            stdin=subprocess.PIPE if input_bytes is not None else subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=environment,
        )

        def read_stdout() -> None:
            try:
                assert process.stdout is not None
                remaining = MAX_GIT_OUTPUT_BYTES + 1
                while remaining:
                    chunk = process.stdout.read(min(64 * 1024, remaining))
                    if not chunk:
                        return
                    chunks.append(chunk)
                    remaining -= len(chunk)
                overflow.set()
                try:
                    process.kill()
                except OSError:
                    pass
            except OSError as exc:
                read_error.append(exc)
                try:
                    process.kill()
                except OSError:
                    pass

        reader = threading.Thread(target=read_stdout, daemon=True)
        reader.start()
        if input_bytes is not None:
            assert process.stdin is not None
            process.stdin.write(input_bytes)
            process.stdin.close()
        try:
            return_code = process.wait(timeout=20)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
            reader.join(timeout=5)
            if process.stdout is not None:
                process.stdout.close()
            raise CodexDirectAdapterError("canonical worktree Git command timed out")
        reader.join(timeout=5)
        if process.stdout is not None:
            process.stdout.close()
        if reader.is_alive():
            raise CodexDirectAdapterError("canonical worktree Git output did not close")
    except (OSError, subprocess.SubprocessError) as exc:
        raise CodexDirectAdapterError("canonical worktree Git inspection failed") from exc
    if overflow.is_set():
        raise CodexDirectAdapterError("canonical worktree Git output exceeds its bound")
    if read_error:
        raise CodexDirectAdapterError("canonical worktree Git output failed") from read_error[0]
    if return_code not in (allowed_codes or {0}):
        raise CodexDirectAdapterError("canonical worktree Git command failed")
    return b"".join(chunks)


def _configured_filter_drivers(root: Path) -> set[str]:
    try:
        output = _run_git_bytes(
            root,
            (
                "config",
                "--name-only",
                "--get-regexp",
                r"^filter\..*\.(clean|process)$",
            ),
            {0, 1},
        ).decode("utf-8", errors="strict")
    except (CodexDirectAdapterError, UnicodeDecodeError) as exc:
        raise CodexDirectAdapterError("Git filter inspection failed") from exc
    drivers: set[str] = set()
    for key in output.splitlines():
        if key.startswith("filter.") and key.rsplit(".", 1)[-1] in {"clean", "process"}:
            drivers.add(key[len("filter.") :].rsplit(".", 1)[0].lower())
    return drivers


def _task_key(task_id: str) -> str:
    return hashlib.sha256(f"task-v1\0{task_id}".encode("utf-8")).hexdigest()[:24]


def _task_dir(context: WorktreeContext, task_id: str) -> Path:
    return context.runtime_root / "tasks" / _task_key(task_id)


def _git_worktree_roots(context: WorktreeContext) -> list[Path]:
    raw = _git_bytes(context.root, "worktree", "list", "--porcelain", "-z")
    roots: list[Path] = []
    try:
        for record in raw.split(b"\0\0"):
            if not record:
                continue
            first = record.split(b"\0", 1)[0]
            if not first.startswith(b"worktree "):
                raise ValueError
            roots.append(
                Path(first[len(b"worktree ") :].decode("utf-8", "strict")).resolve()
            )
            if len(roots) > 512:
                raise ValueError
    except (UnicodeDecodeError, ValueError) as exc:
        raise CodexDirectAdapterError("Git returned invalid linked-worktree data") from exc
    return roots


def _repository_runtime_roots(
    context: WorktreeContext, known_roots: list[Path]
) -> list[tuple[Path, Path]]:
    roots = {context.root.resolve(), *(root.resolve() for root in known_roots)}
    primary = context.common_git_dir.parent.resolve()
    primary_marker = primary / ".git"
    if primary_marker.is_dir() and primary_marker.resolve() == context.common_git_dir.resolve():
        roots.add(primary)
    metadata_root = context.common_git_dir / "worktrees"
    if metadata_root.exists():
        if metadata_root.is_symlink() or not metadata_root.is_dir():
            raise CodexDirectError("linked-worktree metadata is unsafe")
        entries = list(itertools.islice(metadata_root.iterdir(), 513))
        if len(entries) > 512:
            raise CodexDirectError("linked-worktree metadata exceeds its bound")
        entries.sort(key=lambda item: item.name)
        for entry in entries:
            gitdir_file = entry / "gitdir"
            if (
                entry.is_symlink()
                or not entry.is_dir()
            ):
                raise CodexDirectError("linked-worktree metadata is invalid")
            try:
                raw_gitdir = read_bounded_bytes(gitdir_file, 4096)
                if raw_gitdir is None:
                    raise ValueError
                root = Path(
                    raw_gitdir.decode("utf-8", errors="strict").strip()
                ).parent.resolve()
            except (UnicodeDecodeError, ValueError) as exc:
                raise CodexDirectError("linked-worktree metadata is invalid") from exc
            if root.exists():
                roots.add(root)

    runtime_roots: list[tuple[Path, Path]] = []
    for root in sorted(roots, key=lambda item: os.path.normcase(str(item))):
        base = root / ".harness" / "runtime"
        if not base.exists():
            continue
        ensure_no_link_components(root, base)
        entries = list(itertools.islice(base.iterdir(), 513))
        if len(entries) > 512:
            raise CodexDirectError("worktree runtime roots exceed their bound")
        entries.sort(key=lambda item: item.name)
        for runtime_root in entries:
            if runtime_root.is_symlink() or not runtime_root.is_dir():
                raise CodexDirectError("worktree runtime root is invalid")
            runtime_roots.append((root, runtime_root))
            if len(runtime_roots) > 512:
                raise CodexDirectError("repository runtime roots exceed their bound")
    return runtime_roots


def _reject_ticket_in_other_worktree(
    context: WorktreeContext,
    known_roots: list[Path],
    task_id: str,
    source_digest: str,
) -> None:
    task_count = 0
    for root, runtime_root in _repository_runtime_roots(context, known_roots):
        tasks_root = runtime_root / "tasks"
        if not tasks_root.exists():
            continue
        ensure_no_link_components(root, tasks_root)
        entries = list(itertools.islice(tasks_root.iterdir(), MAX_REPOSITORY_TASKS + 1))
        task_count += len(entries)
        if task_count > MAX_REPOSITORY_TASKS:
            raise CodexDirectError("repository task state exceeds its bound")
        for task_dir in entries:
            if task_dir.is_symlink() or not task_dir.is_dir():
                raise CodexDirectError("repository task state is invalid")
            run_path = task_dir / "run.json"
            if not run_path.exists() and not run_path.is_symlink():
                continue
            ensure_no_link_components(root, task_dir)
            existing = read_bounded_json_object(
                run_path, MAX_STATE_BYTES, max_nodes=MAX_STATE_NODES
            )
            contract = existing.get("contract")
            task = contract.get("task") if isinstance(contract, dict) else None
            execution = contract.get("execution") if isinstance(contract, dict) else None
            mode = execution.get("mode") if isinstance(execution, dict) else None
            if (
                mode not in DIRECT_MODES
                or existing.get("schema") != RUN_SCHEMAS[mode]
                or not isinstance(task, dict)
                or set(task) != {"id", "source_digest"}
                or not isinstance(task.get("id"), str)
                or not 1 <= len(task["id"]) <= 128
                or not RUNTIME_ID_RE.fullmatch(task["id"])
                or not isinstance(task.get("source_digest"), str)
                or not re.fullmatch(r"[0-9a-f]{64}", task["source_digest"])
            ):
                raise CodexDirectError("another worktree contains invalid task state")
            if task["id"] == task_id or task["source_digest"] == source_digest:
                raise CodexDirectError(
                    "execution mode is already frozen and a writer lease exists for this task"
                )


def _manual_skill_was_reminded_elsewhere(
    context: WorktreeContext,
    known_roots: list[Path],
    *,
    task_id: str,
    adapter: str,
    host: str,
    skill: str,
) -> bool:
    reminder_id = manual_skill_reminder_id(
        task_id=task_id,
        adapter=adapter,
        host=host,
        skill=skill,
    )
    for root, runtime_root in _repository_runtime_roots(context, known_roots):
        marker = (
            runtime_root
            / "manual-skill-reminders"
            / f"{reminder_id}.json"
        )
        ensure_no_link_components(root, marker.parent)
        if read_bounded_json_object(marker, 1024) == {
            "schema": "harness.manual-skill-reminder/v1",
            "reminder_id": reminder_id,
        }:
            return True
    return False


def _control(run: dict[str, Any], **extra: Any) -> dict[str, Any]:
    contract = run["contract"]
    mode = _direct_mode(contract)
    return {
        "schema": CONTROL_SCHEMAS[mode],
        "task_id": contract["task"]["id"],
        "mode": contract["execution"]["mode"],
        "state": run["state"],
        "writer_lease": contract["writer_lease"],
        **extra,
    }


def _state_keys(value: Any, required: set[str], optional: set[str] | None = None) -> bool:
    return isinstance(value, dict) and required <= set(value) <= required | (optional or set())


def _valid_snapshot(snapshot: Any, paths: list[str]) -> bool:
    if not isinstance(snapshot, list) or len(snapshot) != len(paths):
        return False
    for path, item in zip(paths, snapshot, strict=True):
        if not isinstance(item, dict) or item.get("path") != path:
            return False
        kind = item.get("kind")
        expected = {"path", "kind", "digest", "executable"} if kind == "file" else {
            "path",
            "kind",
            "digest",
        }
        if set(item) != expected or kind not in {"file", "symlink", "deleted"}:
            return False
        if kind == "file" and not isinstance(item.get("executable"), bool):
            return False
        digest = item.get("digest")
        if kind == "deleted":
            if digest is not None:
                return False
        elif not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            return False
    return True


def _validate_evidence_record(evidence: Any) -> None:
    keys = {
        "status", "source", "exit_code", "sensitivity", "digest", "diff_digest",
        "reason_code",
    }
    if not _state_keys(evidence, keys) or any(
        not isinstance(evidence.get(key), str)
        or not re.fullmatch(r"[0-9a-f]{64}", evidence[key])
        for key in ("digest", "diff_digest")
    ):
        raise CodexDirectError("Codex Direct verification state is invalid")
    status = evidence["status"]
    source = evidence["source"]
    exit_code = evidence["exit_code"]
    reason = evidence["reason_code"]
    if (
        status not in {"pass", "fail", "skipped"}
        or source not in {"command", "inspection", "review"}
        or evidence["sensitivity"] not in {"public", "metadata", "secret-free"}
        or (
            exit_code is not None
            and (
                not isinstance(exit_code, int)
                or isinstance(exit_code, bool)
                or not -(2**31) <= exit_code < 2**31
            )
        )
        or (source == "command" and status != "skipped" and (exit_code is None or (status == "pass") != (exit_code == 0)))
        or ((source != "command" or status == "skipped") and exit_code is not None)
        or (status == "skipped" and reason is None)
        or (
            reason is not None
            and (
                not isinstance(reason, str)
                or not 1 <= len(reason) <= 128
                or not RUNTIME_ID_RE.fullmatch(reason)
            )
        )
    ):
        raise CodexDirectError("Codex Direct verification state is invalid")


def _validate_run_shape(run: dict[str, Any], context: WorktreeContext, task_id: str) -> None:
    required = {
        "schema",
        "contract",
        "state",
        "sequence",
        "history",
        "baseline",
        "checks",
        "evidence_log",
        "criteria",
        "risks",
        "repairs",
        "commit_sha",
    }
    if not _state_keys(run, required, {"accepted_diff", "recovery_bundle", "agent_id", "agent_state", "agent_provider", "provider_routing", "bridge_handoff_digest", "bridge_recorded_at"}):
        raise CodexDirectError("Codex Direct task state is unavailable or invalid")
    contract = run["contract"]
    mode = _direct_mode(contract)
    writer = WRITERS[mode]
    if run.get("schema") != RUN_SCHEMAS[mode]:
        raise CodexDirectError("Codex Direct task state is unavailable or invalid")
    contract_keys = {
        "schema",
        "source_contract_digest",
        "task",
        "execution",
        "plan",
        "writer_lease",
        "acceptance_owner",
        "authority",
        "state",
    }
    if not _state_keys(contract, contract_keys):
        raise CodexDirectError("Codex Direct runtime contract is invalid")
    task = contract.get("task")
    if (
        contract.get("schema") != "harness.task-contract/v1"
        or not isinstance(contract.get("source_contract_digest"), str)
        or not re.fullmatch(r"[0-9a-f]{64}", contract["source_contract_digest"])
        or not _state_keys(task, {"id", "source_digest"})
        or task.get("id") != task_id
        or not re.fullmatch(r"[0-9a-f]{64}", str(task.get("source_digest", "")))
        or contract.get("acceptance_owner") != ACCEPTANCE_OWNERS[mode]
        or contract.get("state") != run.get("state")
    ):
        raise CodexDirectError("Codex Direct runtime contract is invalid")
    execution = contract.get("execution")
    if not _state_keys(
        execution,
        {
            "mode",
            "worktree_id",
            "repository_id",
            "base_sha",
            "branch",
            "adapter_switch_policy",
            "isolated_worktree",
        },
    ) or (
        execution.get("mode") != mode
        or execution.get("worktree_id") != context.worktree_id
        or execution.get("repository_id") != context.repository_id
        or not re.fullmatch(r"[0-9a-f]{40}", str(execution.get("base_sha", "")))
        or execution.get("adapter_switch_policy") != "stop-and-report"
        or not isinstance(execution.get("branch"), str)
        or not 1 <= len(execution["branch"]) <= 256
        or any(
            ord(char) < 32
            or ord(char) == 127
            or 0xD800 <= ord(char) <= 0xDFFF
            for char in execution["branch"]
        )
        or not isinstance(execution.get("isolated_worktree"), bool)
        or execution["isolated_worktree"] != (context.git_dir != context.common_git_dir)
    ):
        raise CodexDirectError("canonical worktree does not match task state")
    plan = contract.get("plan")
    if not _state_keys(
        plan,
        {
            "objective_digest",
            "owned_paths",
            "acceptance_criteria",
            "verification_plan",
            "repair_policy",
            "stop_condition_digests",
        },
    ):
        raise CodexDirectError("Codex Direct runtime plan is invalid")
    owned_paths = plan.get("owned_paths")
    acceptance_plan = plan.get("acceptance_criteria")
    verification_plan = plan.get("verification_plan")
    stop_digests = plan.get("stop_condition_digests")
    repair_policy = plan.get("repair_policy")
    if (
        not isinstance(owned_paths, list)
        or not 1 <= len(owned_paths) <= 32
        or not isinstance(acceptance_plan, list)
        or not 1 <= len(acceptance_plan) <= 32
        or not isinstance(verification_plan, list)
        or not 1 <= len(verification_plan) <= 32
        or not isinstance(stop_digests, list)
        or not 1 <= len(stop_digests) <= 16
        or not isinstance(repair_policy, dict)
        or set(repair_policy) != {"max_attempts"}
        or not isinstance(repair_policy["max_attempts"], int)
        or not 1 <= repair_policy["max_attempts"] <= 10
    ):
        raise CodexDirectError("Codex Direct runtime plan is invalid")
    normalized_owned: list[str] = []
    for raw_path in owned_paths:
        if not isinstance(raw_path, str) or not 1 <= len(raw_path) <= 128:
            raise CodexDirectError("Codex Direct runtime plan is invalid")
        path = raw_path.replace("\\", "/")
        directory = path.endswith("/")
        parsed = PurePosixPath(path.rstrip("/"))
        normalized = parsed.as_posix() + ("/" if directory else "")
        if (
            path.startswith("/")
            or not parsed.parts
            or parsed.is_absolute()
            or any(part in {"", ".", ".."} for part in parsed.parts)
            or parsed.parts[0].lower() == ".git"
            or normalized != raw_path
        ):
            raise CodexDirectError("Codex Direct runtime plan is invalid")
        normalized_owned.append(normalized)
    if normalized_owned != sorted(set(normalized_owned)):
        raise CodexDirectError("Codex Direct runtime plan is invalid")
    digests = [plan.get("objective_digest"), *stop_digests]
    if any(
        not isinstance(item, str) or not re.fullmatch(r"[0-9a-f]{64}", item)
        for item in digests
    ) or len(stop_digests) != len(set(stop_digests)):
        raise CodexDirectError("Codex Direct runtime plan is invalid")
    criterion_ids: set[str] = set()
    for item in acceptance_plan:
        if not _state_keys(item, {"id", "description_digest"}) or (
            not isinstance(item.get("id"), str)
            or not 1 <= len(item["id"]) <= 96
            or not RUNTIME_ID_RE.fullmatch(item["id"])
            or not re.fullmatch(r"[0-9a-f]{64}", str(item.get("description_digest", "")))
        ):
            raise CodexDirectError("Codex Direct runtime plan is invalid")
        criterion_ids.add(item["id"])
    check_ids: set[str] = set()
    for item in verification_plan:
        if not _state_keys(item, {"id", "required", "command_digest"}) or (
            not isinstance(item.get("id"), str)
            or not 1 <= len(item["id"]) <= 96
            or not RUNTIME_ID_RE.fullmatch(item["id"])
            or not isinstance(item.get("required"), bool)
            or not re.fullmatch(r"[0-9a-f]{64}", str(item.get("command_digest", "")))
        ):
            raise CodexDirectError("Codex Direct runtime plan is invalid")
        check_ids.add(item["id"])
    if len(criterion_ids) != len(acceptance_plan) or len(check_ids) != len(verification_plan):
        raise CodexDirectError("Codex Direct runtime plan is invalid")
    if contract.get("writer_lease") not in (
        {"holder": writer, "state": "active"},
        {"holder": writer, "state": "released"},
    ) or contract.get("authority") != {
        "local_read_write_test": "allowed",
        "local_commit": "after-acceptance",
        "push_pr_tag_release_publish": "user-approval-required",
        "credentials_ssh_broad_delete_history_rewrite": "blocked",
    }:
        raise CodexDirectError("Codex Direct authority state is invalid")
    if run["state"] not in {"executing", "verifying", "reviewing", "repairing", "accepted", "recovery-required"}:
        raise CodexDirectError("Codex Direct lifecycle state is invalid")
    if (
        not isinstance(run["sequence"], int)
        or isinstance(run["sequence"], bool)
        or run["sequence"] < 0
        or not isinstance(run["history"], list)
        or not 1 <= len(run["history"]) <= 128
    ):
        raise CodexDirectError("Codex Direct history state is invalid")
    event_states = {
        "mode-frozen": {"mode-frozen"},
        "baseline-verified": {"baselined"},
        "writer-acquired": {"executing"},
        "entered-verifying": {"verifying"},
        "entered-reviewing": {"reviewing"},
        "verification-recorded": {"verifying", "reviewing", "repairing"},
        "criterion-judged": {"reviewing"},
        "risk-recorded": {"reviewing"},
        "accepted": {"accepted"},
        "recovery-required": {"recovery-required"},
        "repair-started": {"repairing"},
        "commit-recovered": {"accepted"},
        "local-commit-created": {"accepted"},
    }
    event_previous_states = {
        "baseline-verified": {"mode-frozen"},
        "writer-acquired": {"baselined"},
        "entered-verifying": {"executing", "repairing"},
        "entered-reviewing": {"verifying"},
        "verification-recorded": {"verifying", "reviewing", "repairing"},
        "criterion-judged": {"reviewing"},
        "risk-recorded": {"reviewing"},
        "accepted": {"reviewing"},
        "recovery-required": {"executing", "verifying", "reviewing", "repairing", "accepted"},
        "repair-started": {"verifying", "reviewing"},
        "commit-recovered": {"accepted"},
        "local-commit-created": {"accepted"},
    }
    previous_sequence = -1
    previous_state: str | None = None
    for item in run["history"]:
        if not _state_keys(item, {"sequence", "event", "state"}) or (
            not isinstance(item.get("sequence"), int)
            or isinstance(item.get("sequence"), bool)
            or (
                previous_sequence >= 0
                and item["sequence"] != previous_sequence + 1
            )
            or not isinstance(item.get("event"), str)
            or item["event"] not in event_states
            or item.get("state") not in event_states[item["event"]]
            or (
                previous_state is not None
                and previous_state not in event_previous_states.get(item["event"], set())
            )
        ):
            raise CodexDirectError("Codex Direct history state is invalid")
        previous_sequence = item["sequence"]
        previous_state = item["state"]
    if previous_sequence != run["sequence"] or run["history"][-1]["state"] != run["state"]:
        raise CodexDirectError("Codex Direct history state is invalid")
    if not _state_keys(run["baseline"], {"head_sha", "branch", "status_digest"}):
        raise CodexDirectError("Codex Direct baseline state is invalid")
    if (
        not re.fullmatch(r"[0-9a-f]{40}", str(run["baseline"].get("head_sha", "")))
        or not isinstance(run["baseline"].get("branch"), str)
        or not re.fullmatch(r"[0-9a-f]{64}", str(run["baseline"].get("status_digest", "")))
        or run["baseline"].get("status_digest") != hashlib.sha256(b"").hexdigest()
        or run["baseline"].get("head_sha") != execution["base_sha"]
        or run["baseline"].get("branch") != execution["branch"]
    ):
        raise CodexDirectError("Codex Direct baseline state is invalid")
    for name in ("checks", "criteria", "risks"):
        if not isinstance(run[name], dict):
            raise CodexDirectError(f"Codex Direct {name} state is invalid")
    if len(run["checks"]) > 32 or len(run["criteria"]) > 32 or len(run["risks"]) > MAX_RISKS:
        raise CodexDirectError("Codex Direct evidence state exceeds its bound")
    check_keys = {"status", "source", "exit_code", "sensitivity", "digest", "diff_digest", "reason_code"}
    for check_id, evidence in run["checks"].items():
        if not _state_keys(evidence, check_keys) or check_id not in {
            item["id"] for item in plan["verification_plan"]
        } or any(
            not isinstance(evidence.get(key), str)
            or not re.fullmatch(r"[0-9a-f]{64}", evidence[key])
            for key in ("digest", "diff_digest")
        ) or (
            evidence.get("status") not in {"pass", "fail", "skipped"}
            or evidence.get("source") not in {"command", "inspection", "review"}
            or evidence.get("sensitivity") not in {"public", "metadata", "secret-free"}
            or (
                evidence.get("source") == "command"
                and evidence.get("status") != "skipped"
                and (
                    evidence.get("exit_code") is None
                    or (evidence.get("status") == "pass")
                    != (evidence.get("exit_code") == 0)
                )
            )
            or (
                (evidence.get("source") != "command" or evidence.get("status") == "skipped")
                and evidence.get("exit_code") is not None
            )
            or (evidence.get("status") == "skipped" and evidence.get("reason_code") is None)
            or (
                evidence.get("exit_code") is not None
                and (
                    not isinstance(evidence["exit_code"], int)
                    or isinstance(evidence["exit_code"], bool)
                    or not -(2**31) <= evidence["exit_code"] < 2**31
                )
            )
            or (
                evidence.get("reason_code") is not None
                and (
                    not isinstance(evidence["reason_code"], str)
                    or not 1 <= len(evidence["reason_code"]) <= 128
                    or not RUNTIME_ID_RE.fullmatch(evidence["reason_code"])
                )
            )
        ):
            raise CodexDirectError("Codex Direct verification state is invalid")
    if not isinstance(run["evidence_log"], list) or len(run["evidence_log"]) > MAX_EVIDENCE_RECORDS:
        raise CodexDirectError("Codex Direct evidence log exceeds its bound")
    latest_evidence: dict[str, dict[str, Any]] = {}
    for record in run["evidence_log"]:
        if not _state_keys(record, {"id", *check_keys}):
            raise CodexDirectError("Codex Direct evidence log is invalid")
        check_id = record["id"]
        evidence = {key: record[key] for key in check_keys}
        if check_id not in check_ids:
            raise CodexDirectError("Codex Direct evidence log is invalid")
        try:
            _validate_evidence_record(evidence)
        except CodexDirectError as exc:
            raise CodexDirectError("Codex Direct evidence log is invalid") from exc
        latest_evidence[check_id] = evidence
    if run["checks"] != latest_evidence:
        raise CodexDirectError("Codex Direct evidence log is inconsistent")
    for criterion_id, judgment in run["criteria"].items():
        if not _state_keys(judgment, {"status", "evidence_digest"}) or criterion_id not in {
            item["id"] for item in plan["acceptance_criteria"]
        } or judgment.get("status") not in {"pass", "fail"} or not re.fullmatch(r"[0-9a-f]{64}", str(judgment.get("evidence_digest", ""))):
            raise CodexDirectError("Codex Direct criterion state is invalid")
        if judgment["evidence_digest"] not in {
            evidence["digest"]
            for evidence in run["checks"].values()
            if evidence["status"] == "pass"
        }:
            raise CodexDirectError("Codex Direct criterion state is invalid")
    for risk_id, risk in run["risks"].items():
        if not isinstance(risk_id, str) or not 1 <= len(risk_id) <= 96 or not RUNTIME_ID_RE.fullmatch(risk_id):
            raise CodexDirectError("Codex Direct risk state is invalid")
        if not _state_keys(risk, {"severity", "status", "digest"}) or not re.fullmatch(
            r"[0-9a-f]{64}", str(risk.get("digest", ""))
        ) or risk.get("severity") not in {"low", "medium", "high", "critical"} or risk.get("status") not in {"open", "accepted", "resolved"}:
            raise CodexDirectError("Codex Direct risk state is invalid")
    if not isinstance(run["repairs"], list) or len(run["repairs"]) > repair_policy["max_attempts"]:
        raise CodexDirectError("Codex Direct repair state is invalid")
    for expected_attempt, repair in enumerate(run["repairs"], 1):
        if not _state_keys(
            repair, {"attempt", "fingerprint", "diff_digest", "evidence_digest"}
        ) or (
            not isinstance(repair.get("attempt"), int)
            or isinstance(repair.get("attempt"), bool)
            or repair["attempt"] != expected_attempt
            or any(
                not re.fullmatch(r"[0-9a-f]{64}", str(repair.get(key, "")))
                for key in ("fingerprint", "diff_digest", "evidence_digest")
            )
        ):
            raise CodexDirectError("Codex Direct repair state is invalid")
    commit_sha = run["commit_sha"]
    if commit_sha is not None and not re.fullmatch(r"[0-9a-f]{40}", str(commit_sha)):
        raise CodexDirectError("Codex Direct commit state is invalid")
    lease = contract["writer_lease"]
    if run["state"] == "accepted":
        expected_lease = (
            {"holder": writer, "state": "released"}
            if commit_sha is not None
            else {"holder": writer, "state": "active"}
        )
        if lease != expected_lease or "accepted_diff" not in run:
            raise CodexDirectError("Codex Direct accepted lifecycle state is invalid")
    elif lease != {"holder": writer, "state": "active"} or commit_sha is not None:
        raise CodexDirectError("Codex Direct active lifecycle state is invalid")
    if run["state"] == "recovery-required":
        reference = run.get("recovery_bundle")
        if not _state_keys(reference, {"schema", "file", "digest", "failure"}) or (
            reference.get("schema") != "harness.recovery-bundle-ref/v1"
            or reference.get("file") != "recovery-bundle.json"
            or not re.fullmatch(r"[0-9a-f]{64}", str(reference.get("digest", "")))
            or not _state_keys(reference.get("failure"), {"category", "fingerprint"})
            or reference["failure"].get("category")
            not in {"adapter-failure", "repeated-failure", "repair-limit"}
            or not re.fullmatch(
                r"[0-9a-f]{64}", str(reference["failure"].get("fingerprint", ""))
            )
        ):
            raise CodexDirectError("Recovery Bundle reference is invalid")
        category = reference["failure"]["category"]
        if category == "repair-limit" and len(run["repairs"]) < repair_policy["max_attempts"]:
            raise CodexDirectError("Recovery Bundle repair-limit premise is invalid")
        if category == "repeated-failure" and not any(
            repair["fingerprint"] == reference["failure"]["fingerprint"]
            and repair["evidence_digest"] == _checks_digest(run)
            for repair in run["repairs"]
        ):
            raise CodexDirectError("Recovery Bundle repeated-failure premise is invalid")
    elif "recovery_bundle" in run:
        raise CodexDirectError("Recovery Bundle is invalid for this lifecycle state")


def _load_run(
    context: WorktreeContext,
    task_id: str,
    *,
    expected_mode: str | None = "codex-direct",
) -> tuple[Path, dict[str, Any]]:
    run_path = _task_dir(context, task_id) / "run.json"
    ensure_no_link_components(context.root, run_path.parent)
    run = read_bounded_json_object(
        run_path, MAX_STATE_BYTES, max_nodes=MAX_STATE_NODES
    )
    _validate_run_shape(run, context, task_id)
    if (
        expected_mode is not None
        and run["contract"]["execution"]["mode"] != expected_mode
    ):
        raise CodexDirectError("direct command mode does not match the frozen task mode")
    contract = run.get("contract")
    if not isinstance(contract, dict) or contract.get("task", {}).get("id") != task_id:
        raise CodexDirectError("Codex Direct task identity does not match state")
    execution = contract.get("execution", {})
    if (
        execution.get("worktree_id") != context.worktree_id
        or execution.get("repository_id") != context.repository_id
    ):
        raise CodexDirectError("canonical worktree does not match task state")
    risks = run.get("risks")
    if not isinstance(risks, dict) or len(risks) > MAX_RISKS:
        raise CodexDirectError("Codex Direct task risk state is invalid")
    accepted_diff = run.get("accepted_diff")
    if accepted_diff is not None:
        if run["state"] not in {"accepted", "recovery-required"}:
            raise CodexDirectError("accepted diff is invalid for this lifecycle state")
        if not _state_keys(
            accepted_diff,
            {
                "diff_digest", "digest", "paths", "snapshot", "index_snapshot",
                "index_digest",
            },
        ):
            raise CodexDirectError("Codex Direct accepted diff state is invalid")
        paths = accepted_diff["paths"]
        snapshot = accepted_diff["snapshot"]
        index_snapshot = accepted_diff["index_snapshot"]
        if (
            not isinstance(paths, list)
            or not paths
            or any(not isinstance(path, str) for path in paths)
            or paths != sorted(set(paths))
            or any(
                not _path_is_owned(path, contract["plan"]["owned_paths"])
                for path in paths
            )
            or not re.fullmatch(r"[0-9a-f]{64}", str(accepted_diff.get("diff_digest", "")))
            or not _valid_snapshot(snapshot, paths)
            or not _valid_snapshot(index_snapshot, paths)
            or _snapshot_digest(snapshot) != accepted_diff.get("digest")
            or _snapshot_digest(index_snapshot) != accepted_diff.get("index_digest")
        ):
            raise CodexDirectError("Codex Direct accepted diff state is invalid")
        _require_recovery_safe_paths(paths)
        required_checks = {
            item["id"]
            for item in contract["plan"]["verification_plan"]
            if item["required"]
        }
        passing = {
            check_id: evidence
            for check_id, evidence in run["checks"].items()
            if evidence["status"] == "pass"
            and evidence["diff_digest"] == accepted_diff["diff_digest"]
        }
        criterion_ids = {
            item["id"] for item in contract["plan"]["acceptance_criteria"]
        }
        if (
            required_checks - set(passing)
            or any(evidence["status"] == "fail" for evidence in run["checks"].values())
            or not any(evidence["source"] == "review" for evidence in passing.values())
            or set(run["criteria"]) != criterion_ids
            or any(
                judgment["status"] != "pass"
                or judgment["evidence_digest"]
                not in {evidence["digest"] for evidence in passing.values()}
                for judgment in run["criteria"].values()
            )
            or any(risk["status"] == "open" for risk in run["risks"].values())
        ):
            raise CodexDirectError("Codex Direct accepted evidence state is invalid")
    return run_path, run


def _write_json(context: WorktreeContext, path: Path, value: dict[str, Any]) -> None:
    content = _bounded_json(value)
    ensure_no_link_components(context.root, path.parent)
    if path.is_symlink():
        raise CodexDirectError("Codex Direct state path cannot be a link")
    try:
        write_bounded_text(path, content, MAX_STATE_BYTES)
    except OSError as exc:
        raise CodexDirectAdapterError("Codex Direct state persistence failed") from exc
    if (
        read_bounded_json_object(
            path, MAX_STATE_BYTES, max_nodes=MAX_STATE_NODES
        )
        != value
    ):
        raise CodexDirectAdapterError("Codex Direct state persistence was not durable")


def _bounded_json(value: dict[str, Any]) -> str:
    try:
        validate_json_shape(value, max_nodes=MAX_STATE_NODES)
    except ValueError as exc:
        raise CodexDirectError("Codex Direct state exceeds structural limits") from exc
    content = json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    )
    if len(content.encode("utf-8")) > MAX_STATE_BYTES:
        raise CodexDirectError("Codex Direct state exceeds its byte limit")
    return content


def _save_run(context: WorktreeContext, run_path: Path, run: dict[str, Any]) -> None:
    _write_json(context, run_path, run)


def _serialized(operation: Any) -> Any:
    @wraps(operation)
    def wrapper(context: WorktreeContext, *args: Any, **kwargs: Any) -> Any:
        task_id = kwargs.get("task_id")
        if not isinstance(task_id, str):
            raise CodexDirectError("Codex Direct task identity is required")
        task_dir = _task_dir(context, task_id)
        ensure_no_link_components(context.root, task_dir)
        with bounded_file_lock(task_dir / "run.lock"):
            return operation(context, *args, **kwargs)

    return wrapper


@contextmanager
def _repository_mutex(context: WorktreeContext, fallback_lock: Path) -> Any:
    if os.name != "nt":
        with bounded_file_lock(fallback_lock, create=False):
            yield
        return

    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.argtypes = (wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR)
    kernel32.CreateMutexW.restype = wintypes.HANDLE
    kernel32.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
    kernel32.WaitForSingleObject.restype = wintypes.DWORD
    kernel32.ReleaseMutex.argtypes = (wintypes.HANDLE,)
    kernel32.ReleaseMutex.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel32.CloseHandle.restype = wintypes.BOOL
    handle = kernel32.CreateMutexW(
        None, False, f"Local\\BilibiliHarnessV2-{context.repository_id}"
    )
    if not handle:
        raise CodexDirectError("repository control mutex is unavailable")
    result = kernel32.WaitForSingleObject(handle, 10_000)
    if result not in {0, 0x80}:
        kernel32.CloseHandle(handle)
        raise CodexDirectError("repository control mutex is busy")
    try:
        yield
    finally:
        kernel32.ReleaseMutex(handle)
        kernel32.CloseHandle(handle)


def _task_source_digest(contract: dict[str, Any]) -> str:
    return hashlib.sha256(contract["task"]["source"].encode("utf-8")).hexdigest()


def _runtime_contract(
    context: WorktreeContext, contract: dict[str, Any]
) -> dict[str, Any]:
    plan = contract["plan"]
    mode = contract["execution"]["mode"]
    writer = WRITERS[mode]
    contract_digest = hashlib.sha256(
        json.dumps(
            contract, ensure_ascii=True, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()
    return {
        "schema": contract["schema"],
        "source_contract_digest": contract_digest,
        "task": {
            "id": contract["task"]["id"],
            "source_digest": _task_source_digest(contract),
        },
        "execution": {
            "mode": mode,
            "worktree_id": context.worktree_id,
            "repository_id": context.repository_id,
            "base_sha": contract["execution"]["base_sha"],
            "branch": contract["execution"]["branch"],
            "adapter_switch_policy": "stop-and-report",
            "isolated_worktree": context.git_dir != context.common_git_dir,
        },
        "plan": {
            "objective_digest": hashlib.sha256(
                plan["objective"].encode("utf-8")
            ).hexdigest(),
            "owned_paths": sorted(plan["owned_paths"]),
            "acceptance_criteria": [
                {
                    "id": item["id"],
                    "description_digest": hashlib.sha256(
                        item["description"].encode("utf-8")
                    ).hexdigest(),
                }
                for item in plan["acceptance_criteria"]
            ],
            "verification_plan": [
                {
                    "id": item["id"],
                    "required": item["required"],
                    "command_digest": hashlib.sha256(
                        item["command"].encode("utf-8")
                    ).hexdigest(),
                }
                for item in plan["verification_plan"]
            ],
            "repair_policy": copy.deepcopy(plan["repair_policy"]),
            "stop_condition_digests": [
                hashlib.sha256(item.encode("utf-8")).hexdigest()
                for item in plan["stop_conditions"]
            ],
        },
        "writer_lease": {"holder": writer, "state": "active"},
        "acceptance_owner": ACCEPTANCE_OWNERS[mode],
        "authority": copy.deepcopy(contract["authority"]),
        "state": "executing",
    }


def _add_history(run: dict[str, Any], event: str, state: str) -> None:
    sequence = int(run["sequence"]) + 1
    run["sequence"] = sequence
    run["history"] = [
        *run["history"][-127:],
        {"sequence": sequence, "event": event, "state": state},
    ]


def _require_digest(value: str, name: str = "evidence digest") -> str:
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value.lower()):
        raise CodexDirectError(f"{name} must be a SHA-256 digest")
    return value.lower()


def _require_runtime_id(value: str, name: str, limit: int = 96) -> str:
    if (
        not isinstance(value, str)
        or not 1 <= len(value) <= limit
        or not RUNTIME_ID_RE.fullmatch(value)
    ):
        raise CodexDirectError(f"{name} must be a bounded identifier")
    return value


def _git_paths(
    root: Path, *args: str, env_overrides: dict[str, str] | None = None
) -> list[str]:
    raw = _git_bytes(root, *args, env_overrides=env_overrides)
    try:
        return sorted(
            item.decode("utf-8", errors="strict").replace("\\", "/")
            for item in raw.split(b"\0")
            if item
        )
    except UnicodeDecodeError as exc:
        raise CodexDirectError("Git returned a non-UTF-8 repository path") from exc


def _staged_paths(root: Path) -> list[str]:
    return _git_paths(
        root,
        "diff",
        "--cached",
        "--name-only",
        "--no-renames",
        "--no-ext-diff",
        "--no-textconv",
        "-z",
    )


def _unstaged_paths(root: Path) -> list[str]:
    _reject_repository_filters(root)
    return sorted(
        set(
            _git_paths(
                root,
                "diff",
                "--name-only",
                "--no-renames",
                "--no-ext-diff",
                "--no-textconv",
                "-z",
            )
        )
        | set(_git_paths(root, "ls-files", "--others", "--exclude-standard", "-z"))
    )


def _changed_paths(root: Path) -> list[str]:
    return sorted(set(_unstaged_paths(root)) | set(_staged_paths(root)))


def _diff_digest(root: Path) -> str:
    _changed_paths(root)
    digest = hashlib.sha256()
    digest.update(
        _git_bytes(
            root, "diff", "--binary", "--no-ext-diff", "--no-textconv"
        )
    )
    digest.update(b"\0staged-diff\0")
    digest.update(
        _git_bytes(
            root,
            "diff",
            "--cached",
            "--binary",
            "--no-ext-diff",
            "--no-textconv",
        )
    )
    untracked = _git_paths(root, "ls-files", "--others", "--exclude-standard", "-z")
    digest.update(b"\0untracked-snapshot\0")
    digest.update(_snapshot_digest(_path_snapshot(root, untracked)).encode("ascii"))
    return digest.hexdigest()


def _require_recovery_safe_paths(paths: list[str]) -> None:
    if len(paths) > MAX_ACCEPTED_PATHS or sum(
        len(path.encode("utf-8")) for path in paths
    ) > MAX_ACCEPTED_PATH_BYTES:
        raise CodexDirectError("ticket diff exceeds recovery-safe path limits")


def _recovery_path_evidence(paths: list[str]) -> dict[str, Any]:
    digest = hashlib.sha256(b"recovery-paths-v1")
    for path in paths:
        encoded = path.encode("utf-8")
        digest.update(len(encoded).to_bytes(4, "big"))
        digest.update(encoded)
    embedded = len(paths) <= MAX_ACCEPTED_PATHS and sum(
        len(path.encode("utf-8")) for path in paths
    ) <= MAX_ACCEPTED_PATH_BYTES
    return {
        "paths": paths if embedded else [],
        "count": len(paths),
        "digest": digest.hexdigest(),
        "embedded": embedded,
    }


def _require_commit_message(message: str) -> str:
    if (
        not isinstance(message, str)
        or not message.strip()
        or message != message.strip()
        or len(message) > 200
        or any(
            ord(char) < 32
            or ord(char) == 127
            or 0xD800 <= ord(char) <= 0xDFFF
            for char in message
        )
    ):
        raise CodexDirectError("commit message must be a bounded single line")
    return message


def _reject_in_progress_git_operation(context: WorktreeContext) -> None:
    markers = (
        "MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD", "BISECT_LOG",
        "rebase-merge", "rebase-apply", "sequencer",
    )
    if any(
        (context.git_dir / marker).exists() or (context.git_dir / marker).is_symlink()
        for marker in markers
    ) or _git_bytes(context.root, "ls-files", "--unmerged", "-z"):
        raise CodexDirectError("an in-progress Git operation prevents ticket control")


def _path_snapshot(root: Path, paths: list[str]) -> list[dict[str, Any]]:
    if len(paths) > 4096:
        raise CodexDirectError("ticket path snapshot exceeds its bound")
    snapshot: list[dict[str, Any]] = []
    remaining = MAX_GIT_OUTPUT_BYTES
    for relative in paths:
        path = root / PurePosixPath(relative)
        if path.is_symlink():
            try:
                target = os.readlink(path).encode(
                    "utf-8", errors="surrogateescape"
                )
            except OSError as exc:
                raise CodexDirectAdapterError(
                    "unable to fingerprint the accepted diff"
                ) from exc
            if len(target) > remaining:
                raise CodexDirectError("ticket path snapshot exceeds its byte limit")
            remaining -= len(target)
            snapshot.append(
                {
                    "path": relative,
                    "kind": "symlink",
                    "digest": hashlib.sha256(target).hexdigest(),
                }
            )
            continue
        if not path.exists():
            snapshot.append({"path": relative, "kind": "deleted", "digest": None})
            continue
        if not path.is_file():
            raise CodexDirectError("ticket diff contains an unsupported file type")
        digest = hashlib.sha256()
        try:
            file_stat = path.stat()
            if file_stat.st_size > remaining:
                raise CodexDirectError("ticket path snapshot exceeds its byte limit")
            with path.open("rb") as handle:
                while True:
                    chunk = handle.read(min(1024 * 1024, remaining + 1))
                    if not chunk:
                        break
                    if len(chunk) > remaining:
                        raise CodexDirectError(
                            "ticket path snapshot exceeds its byte limit"
                        )
                    digest.update(chunk)
                    remaining -= len(chunk)
            executable = bool(file_stat.st_mode & stat.S_IXUSR)
        except OSError as exc:
            raise CodexDirectAdapterError("unable to fingerprint the accepted diff") from exc
        snapshot.append(
            {
                "path": relative,
                "kind": "file",
                "executable": executable,
                "digest": digest.hexdigest(),
            }
        )
    return snapshot


def _snapshot_digest(snapshot: list[dict[str, Any]]) -> str:
    encoded = json.dumps(
        snapshot, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _path_is_owned(raw_path: str, owned_paths: list[str]) -> bool:
    normalized = raw_path.replace("\\", "/")
    candidate = PurePosixPath(normalized)
    if candidate.is_absolute() or any(part in {"", ".", ".."} for part in candidate.parts):
        return False
    path = candidate.as_posix()
    for raw_owner in owned_paths:
        owner = raw_owner.replace("\\", "/")
        if owner.endswith("/"):
            if path.startswith(owner) and path != owner.rstrip("/"):
                return True
        elif path == owner:
            return True
    return False


def _path_argument_batches(paths: list[str]) -> list[list[str]]:
    batches: list[list[str]] = []
    batch: list[str] = []
    units = 0
    for path in paths:
        path_units = len(path) + 3
        if path_units > 12_000:
            raise CodexDirectError("repository path exceeds the Git argument budget")
        if batch and (len(batch) >= 128 or units + path_units > 12_000):
            batches.append(batch)
            batch = []
            units = 0
        batch.append(path)
        units += path_units
    if batch:
        batches.append(batch)
    return batches


def _reject_filtered_paths(root: Path, paths: list[str]) -> None:
    drivers = _configured_filter_drivers(root)
    for batch in _path_argument_batches(paths):
        raw = _git_bytes(
            root, "check-attr", "-z", "filter", "--", *batch
        )
        fields = raw.split(b"\0")
        if fields and fields[-1] == b"":
            fields.pop()
        if len(fields) % 3:
            raise CodexDirectAdapterError("Git attribute inspection returned invalid data")
        for index in range(0, len(fields), 3):
            try:
                value = fields[index + 2].decode("utf-8", "strict").lower()
            except UnicodeDecodeError as exc:
                raise CodexDirectAdapterError(
                    "Git attribute inspection returned invalid data"
                ) from exc
            if value == "unspecified" and "unspecified" not in drivers:
                continue
            if value == "unset" and "unset" not in drivers:
                continue
            raise CodexDirectError(
                "automatic accepted commit refuses paths with external Git filters"
            )


def _reject_repository_filters(root: Path, extra_paths: list[str] | None = None) -> None:
    paths = sorted(
        set(_git_paths(root, "ls-files", "-z"))
        | set(_git_paths(root, "ls-files", "--others", "--exclude-standard", "-z"))
        | set(extra_paths or [])
    )
    _reject_filtered_paths(root, paths)


@_serialized
def guard_codex_direct(
    context: WorktreeContext,
    *,
    task_id: str,
    action: str,
    path: str | None = None,
    expected_mode: str | None = "codex-direct",
) -> tuple[dict[str, Any], int]:
    if action not in GUARDED_ACTIONS:
        raise CodexDirectError("unsupported guarded action")
    _, run = _load_run(context, task_id, expected_mode=expected_mode)
    base = _control(run, action=action)

    if action in USER_AUTH_ACTIONS:
        return {
            **base,
            "decision": "user-authorization-required",
            "requires_user": True,
            "reason_code": "external-effect",
        }, 4
    if action in BLOCKED_ACTIONS:
        return {
            **base,
            "decision": "blocked",
            "requires_user": True,
            "reason_code": "constitutionally-blocked",
        }, 5
    if action == "local-commit":
        allowed = run["state"] == "accepted"
        return {
            **base,
            "decision": "allowed" if allowed else "blocked",
            "requires_user": False,
            "reason_code": None if allowed else "acceptance-required",
        }, 0 if allowed else 5
    if action in {"edit", "write", "delete", "rename"}:
        if path is None:
            raise CodexDirectError(f"{action} guard requires a repository-relative path")
        if run["state"] not in {"executing", "repairing"}:
            return {
                **base,
                "decision": "blocked",
                "requires_user": False,
                "reason_code": "state-does-not-allow-edit",
            }, 5
        if not _path_is_owned(path, run["contract"]["plan"]["owned_paths"]):
            return {
                **base,
                "decision": "blocked",
                "requires_user": False,
                "reason_code": "path-not-owned",
            }, 5
        try:
            target = context.root / PurePosixPath(path)
            ensure_no_link_components(context.root, target)
            if target.is_file() and target.stat().st_nlink > 1:
                raise ValueError("repository edit path cannot be a hard link")
        except (OSError, ValueError):
            return {
                **base,
                "decision": "blocked",
                "requires_user": False,
                "reason_code": "unsafe-path-boundary",
            }, 5
    elif action != "read" and run["state"] not in {
        "executing",
        "verifying",
        "reviewing",
        "repairing",
    }:
        return {
            **base,
            "decision": "blocked",
            "requires_user": False,
            "reason_code": "state-does-not-allow-operation",
        }, 5
    return {
        **base,
        "decision": "allowed",
        "requires_user": False,
        "reason_code": None,
    }, 0


@_serialized
def advance_codex_direct(
    context: WorktreeContext,
    *,
    task_id: str,
    target: str,
    expected_mode: str | None = "codex-direct",
) -> dict[str, Any]:
    run_path, run = _load_run(context, task_id, expected_mode=expected_mode)
    allowed = {
        ("executing", "verifying"),
        ("repairing", "verifying"),
        ("verifying", "reviewing"),
    }
    if (run["state"], target) not in allowed:
        raise CodexDirectError("illegal Codex Direct state transition")
    run["state"] = target
    run["contract"]["state"] = target
    _add_history(run, f"entered-{target}", target)
    _save_run(context, run_path, run)
    return _control(run)


@_serialized
def record_check(
    context: WorktreeContext,
    *,
    task_id: str,
    check_id: str,
    status: str,
    source: str,
    exit_code: int | None,
    sensitivity: str,
    digest: str,
    reason_code: str | None,
    expected_mode: str | None = "codex-direct",
) -> dict[str, Any]:
    run_path, run = _load_run(context, task_id, expected_mode=expected_mode)
    if run["state"] not in {"verifying", "reviewing", "repairing"}:
        raise CodexDirectError("verification evidence is not allowed in this state")
    planned = {
        item["id"]: item for item in run["contract"]["plan"]["verification_plan"]
    }
    if check_id not in planned:
        raise CodexDirectError("verification check is not in the frozen plan")
    if status not in {"pass", "fail", "skipped"}:
        raise CodexDirectError("verification status is invalid")
    if source not in {"command", "inspection", "review"}:
        raise CodexDirectError("verification source is invalid")
    if source == "command" and status != "skipped":
        if (
            not isinstance(exit_code, int)
            or isinstance(exit_code, bool)
            or not -(2**31) <= exit_code < 2**31
        ):
            raise CodexDirectError("command verification requires a bounded exit code")
        if (status == "pass") != (exit_code == 0):
            raise CodexDirectError("command status does not match its exit code")
    elif exit_code is not None:
        raise CodexDirectError("only executed command evidence may record an exit code")
    if sensitivity not in {"public", "metadata", "secret-free"}:
        raise CodexDirectError("verification sensitivity is invalid")
    if status == "skipped" and not reason_code:
        raise CodexDirectError("skipped verification requires a reason code")
    if reason_code is not None:
        _require_runtime_id(reason_code, "verification reason code", 128)
    if len(run["evidence_log"]) >= MAX_EVIDENCE_RECORDS:
        raise CodexDirectError("verification evidence log is full")
    evidence = {
        "status": status,
        "source": source,
        "exit_code": exit_code,
        "sensitivity": sensitivity,
        "digest": _require_digest(digest),
        "diff_digest": _diff_digest(context.root),
        "reason_code": reason_code,
    }
    run["evidence_log"].append({"id": check_id, **evidence})
    run["checks"][check_id] = evidence
    passing_digests = {
        item["digest"] for item in run["checks"].values() if item["status"] == "pass"
    }
    run["criteria"] = {
        criterion_id: judgment
        for criterion_id, judgment in run["criteria"].items()
        if judgment["evidence_digest"] in passing_digests
    }
    _add_history(run, "verification-recorded", run["state"])
    _save_run(context, run_path, run)
    return _control(run, check_id=check_id, evidence=evidence)


@_serialized
def judge_criterion(
    context: WorktreeContext,
    *,
    task_id: str,
    criterion_id: str,
    status: str,
    evidence_digest: str,
    expected_mode: str | None = "codex-direct",
) -> dict[str, Any]:
    run_path, run = _load_run(context, task_id, expected_mode=expected_mode)
    if run["state"] != "reviewing":
        raise CodexDirectError("acceptance criteria can be judged only during review")
    criteria = {
        item["id"] for item in run["contract"]["plan"]["acceptance_criteria"]
    }
    if criterion_id not in criteria:
        raise CodexDirectError("acceptance criterion is not in the frozen plan")
    if status not in {"pass", "fail"}:
        raise CodexDirectError("criterion status is invalid")
    digest = _require_digest(evidence_digest)
    known_digests = {
        item["digest"] for item in run["checks"].values() if item["status"] == "pass"
    }
    if digest not in known_digests:
        raise CodexDirectError("criterion evidence must reference a passing check")
    run["criteria"][criterion_id] = {
        "status": status,
        "evidence_digest": digest,
    }
    _add_history(run, "criterion-judged", run["state"])
    _save_run(context, run_path, run)
    return _control(run, criterion_id=criterion_id, judgment=run["criteria"][criterion_id])


@_serialized
def record_risk(
    context: WorktreeContext,
    *,
    task_id: str,
    risk_id: str,
    severity: str,
    status: str,
    digest: str,
    expected_mode: str | None = "codex-direct",
) -> dict[str, Any]:
    run_path, run = _load_run(context, task_id, expected_mode=expected_mode)
    if run["state"] != "reviewing":
        raise CodexDirectError("risks can be recorded only during review")
    _require_runtime_id(risk_id, "risk id")
    if severity not in {"low", "medium", "high", "critical"}:
        raise CodexDirectError("risk severity is invalid")
    if status not in {"open", "accepted", "resolved"}:
        raise CodexDirectError("risk status is invalid")
    if risk_id not in run["risks"] and len(run["risks"]) >= MAX_RISKS:
        raise CodexDirectError("risk limit preserves Recovery Bundle capacity")
    run["risks"][risk_id] = {
        "severity": severity,
        "status": status,
        "digest": _require_digest(digest, "risk digest"),
    }
    _add_history(run, "risk-recorded", run["state"])
    _save_run(context, run_path, run)
    return _control(run, risk_id=risk_id, risk=run["risks"][risk_id])


def _accept_codex_direct_unlocked(
    context: WorktreeContext,
    *,
    task_id: str,
    message: str = "chore(harness): create accepted ticket commit",
    expected_mode: str | None = "codex-direct",
) -> dict[str, Any]:
    """Shared acceptance core — caller holds ``run.lock``."""
    run_path, run = _load_run(context, task_id, expected_mode=expected_mode)
    _require_commit_message(message)
    if run["state"] == "accepted":
        committed = _commit_unlocked(
            context,
            task_id=task_id,
            message=message,
            expected_mode=expected_mode,
        )
        run["commit_sha"] = committed["commit_sha"]
        run["contract"]["writer_lease"] = committed["writer_lease"]
        return {
            **_control(
                run,
                checks=run["checks"],
                criteria=run["criteria"],
                risks=run["risks"],
                accepted_diff=run.get("accepted_diff"),
            ),
            "commit_status": committed["commit_status"],
            "commit_sha": committed["commit_sha"],
        }
    if run["state"] != "reviewing":
        raise CodexDirectError("Codex Direct acceptance requires reviewing state")

    required_checks = {
        item["id"]
        for item in run["contract"]["plan"]["verification_plan"]
        if item["required"]
    }
    passed_checks = {
        check_id
        for check_id, evidence in run["checks"].items()
        if evidence["status"] == "pass"
    }
    if required_checks - passed_checks or any(
        evidence["status"] == "fail" for evidence in run["checks"].values()
    ):
        raise CodexDirectError("required verification evidence is incomplete or failing")
    current_diff_digest = _diff_digest(context.root)
    if any(
        run["checks"][check_id].get("diff_digest") != current_diff_digest
        for check_id in required_checks
    ):
        raise CodexDirectError("required verification evidence is not for the current diff")
    if not any(
        evidence["status"] == "pass"
        and evidence["source"] == "review"
        and evidence.get("diff_digest") == current_diff_digest
        for evidence in run["checks"].values()
    ):
        raise CodexDirectError("acceptance requires current review-sourced evidence")

    criterion_ids = {
        item["id"] for item in run["contract"]["plan"]["acceptance_criteria"]
    }
    if criterion_ids != {
        criterion_id
        for criterion_id, judgment in run["criteria"].items()
        if judgment["status"] == "pass"
    }:
        raise CodexDirectError("criterion-by-criterion acceptance evidence is incomplete")
    passing_current_digests = {
        evidence["digest"]
        for evidence in run["checks"].values()
        if evidence["status"] == "pass"
        and evidence.get("diff_digest") == current_diff_digest
    }
    if any(
        judgment["evidence_digest"] not in passing_current_digests
        for judgment in run["criteria"].values()
        if judgment["status"] == "pass"
    ):
        raise CodexDirectError("criterion evidence is not for the current diff")
    if any(risk["status"] == "open" for risk in run["risks"].values()):
        raise CodexDirectError("open risks prevent acceptance")

    contract = run["contract"]
    _reject_in_progress_git_operation(context)
    if _git(context.root, "rev-parse", "HEAD").lower() != contract["execution"]["base_sha"]:
        raise CodexDirectError("HEAD moved away from the frozen baseline before acceptance")
    if _git(context.root, "branch", "--show-current") != contract["execution"]["branch"]:
        raise CodexDirectError("branch changed before acceptance")
    if _staged_paths(context.root):
        raise CodexDirectError("pre-staged changes prevent acceptance")
    changed_paths = _changed_paths(context.root)
    if not changed_paths:
        raise CodexDirectError("acceptance requires a ticket-owned diff")
    owned_paths = contract["plan"]["owned_paths"]
    if any(not _path_is_owned(path, owned_paths) for path in changed_paths):
        raise CodexDirectError("unowned or mixed changes prevent acceptance")
    _require_recovery_safe_paths(changed_paths)

    run["state"] = "accepted"
    contract["state"] = "accepted"
    snapshot = _path_snapshot(context.root, changed_paths)
    if _diff_digest(context.root) != current_diff_digest:
        raise CodexDirectError("ticket diff changed during acceptance")
    canonical_snapshot = _canonical_index_snapshot(context, changed_paths)
    if _diff_digest(context.root) != current_diff_digest:
        raise CodexDirectError("ticket diff changed during canonical acceptance")
    run["accepted_diff"] = {
        "diff_digest": current_diff_digest,
        "digest": _snapshot_digest(snapshot),
        "paths": changed_paths,
        "snapshot": snapshot,
        "index_snapshot": canonical_snapshot,
        "index_digest": _snapshot_digest(canonical_snapshot),
    }
    _add_history(run, "accepted", "accepted")
    recovery_probe = copy.deepcopy(run)
    recovery_probe["state"] = "recovery-required"
    recovery_probe["contract"]["state"] = "recovery-required"
    recovery_bundle_probe = _make_recovery_bundle(
        run,
        category="adapter-failure",
        fingerprint="0" * 64,
        head_sha=contract["execution"]["base_sha"],
        branch=contract["execution"]["branch"],
        diff_digest=current_diff_digest,
        changed_paths=changed_paths,
        staged_paths=[],
        repository_inspection="current",
    )
    recovery_probe["recovery_bundle"] = _recovery_reference(recovery_bundle_probe)
    _add_history(recovery_probe, "recovery-required", "recovery-required")
    try:
        _bounded_json(recovery_probe)
    except CodexDirectError as exc:
        raise CodexDirectError(
            "accepted state cannot preserve recovery-safe bundle capacity"
        ) from exc
    _save_run(context, run_path, run)
    committed = _commit_unlocked(
        context,
        task_id=task_id,
        message=message,
        expected_mode=expected_mode,
    )
    run["commit_sha"] = committed["commit_sha"]
    run["contract"]["writer_lease"] = committed["writer_lease"]
    return {
        **_control(
            run,
            checks=run["checks"],
            criteria=run["criteria"],
            risks=run["risks"],
            accepted_diff=run["accepted_diff"],
        ),
        "commit_status": committed["commit_status"],
        "commit_sha": committed["commit_sha"],
    }


@_serialized
def accept_codex_direct(
    context: WorktreeContext,
    *,
    task_id: str,
    message: str = "chore(harness): create accepted ticket commit",
    expected_mode: str | None = "codex-direct",
) -> dict[str, Any]:
    return _accept_codex_direct_unlocked(
        context, task_id=task_id, message=message,
        expected_mode=expected_mode,
    )


def _checks_digest(run: dict[str, Any]) -> str:
    records = sorted(
        {
            json.dumps(
                record, ensure_ascii=True, sort_keys=True, separators=(",", ":")
            )
            for record in run["evidence_log"]
        }
    )
    encoded = "\n".join(records).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _make_recovery_bundle(
    run: dict[str, Any],
    *,
    category: str,
    fingerprint: str,
    head_sha: str | None,
    branch: str | None,
    diff_digest: str | None,
    changed_paths: list[str],
    staged_paths: list[str],
    repository_inspection: str,
) -> dict[str, Any]:
    contract = run["contract"]
    criteria = [item["id"] for item in contract["plan"]["acceptance_criteria"]]
    changed = _recovery_path_evidence(changed_paths)
    staged = _recovery_path_evidence(staged_paths)
    owned = _recovery_path_evidence(contract["plan"]["owned_paths"])
    return {
        "schema": "harness.recovery-bundle/v1",
        "task_id": contract["task"]["id"],
        "mode": contract["execution"]["mode"],
        "repository_id": contract["execution"]["repository_id"],
        "worktree_id": contract["execution"]["worktree_id"],
        "base_sha": contract["execution"]["base_sha"],
        "head_sha": head_sha,
        "branch": branch,
        "repository_inspection": repository_inspection,
        "diff_digest": diff_digest,
        "changed_paths": changed["paths"],
        "changed_path_count": changed["count"],
        "changed_paths_digest": changed["digest"],
        "changed_paths_embedded": changed["embedded"],
        "staged_paths": staged["paths"],
        "staged_path_count": staged["count"],
        "staged_paths_digest": staged["digest"],
        "staged_paths_embedded": staged["embedded"],
        "owned_paths": owned["paths"],
        "owned_path_count": owned["count"],
        "owned_paths_digest": owned["digest"],
        "owned_paths_embedded": owned["embedded"],
        "validations": [
            copy.deepcopy(record) for record in run["evidence_log"]
        ],
        "incomplete_criteria": sorted(
            criterion_id
            for criterion_id in criteria
            if run["criteria"].get(criterion_id, {}).get("status") != "pass"
        ),
        "risks": [
            {"id": risk_id, **run["risks"][risk_id]}
            for risk_id in sorted(run["risks"])
        ],
        "repair_attempts": len(run["repairs"]),
        "writer_lease": contract["writer_lease"],
        "adapter_switch_policy": contract["execution"]["adapter_switch_policy"],
        "failure": {"category": category, "fingerprint": fingerprint},
        "commit_sha": run["commit_sha"],
    }


COLLABORATION_RECOVERY_SIDECARS = (
    "dispatch-pending.json",
    "launch.json",
    "repair-pending-attempts",
    "repair-dispatch-attempts",
    "report.json",
)


def _attempts_digest(task_dir: Path, prefix: str) -> str:
    """Digest of the canonical sorted name->digest map for ``prefix-*.json``.

    Attempt-keyed repair evidence (``repair-pending-{n}.json`` /
    ``repair-dispatch-{n}.json``) is folded into one logical sidecar per
    kind; the singleton file name is not part of the evidence schema.
    """
    mapping: dict[str, str] = {}
    for path in sorted(task_dir.glob(f"{prefix}-*.json")):
        raw = read_bounded_bytes(path, MAX_STATE_BYTES)
        mapping[path.name] = (
            "missing-or-unreadable"
            if raw is None
            else hashlib.sha256(b"sidecar-v1\0" + raw).hexdigest()
        )
    if not mapping:
        return "missing-or-unreadable"
    encoded = json.dumps(mapping, sort_keys=True).encode("utf-8")
    return hashlib.sha256(b"attempts-v1\0" + encoded).hexdigest()


def _collaboration_recovery_evidence(
    run: dict[str, Any], task_dir: Path, bridge_path: Path
) -> dict[str, Any]:
    """Bounded secret-free collaboration evidence for recovery bundles.

    Digest-only: file contents are never embedded; missing or unreadable
    files record a fixed status string.  Agent identity/state is the last
    persisted run-record state (not a live inspect claim), preserving
    same-agent resume identity.  Added only to ``codex-paseo-claude``
    bundles; Direct bundles keep the exact schema.
    """
    sidecars: dict[str, str] = {}
    for name in COLLABORATION_RECOVERY_SIDECARS:
        if name.endswith("-attempts"):
            sidecars[name] = _attempts_digest(
                task_dir, name[: -len("-attempts")]
            )
            continue
        raw = read_bounded_bytes(task_dir / name, MAX_STATE_BYTES)
        if raw is None:
            sidecars[name] = "missing-or-unreadable"
        else:
            sidecars[name] = hashlib.sha256(b"sidecar-v1\0" + raw).hexdigest()
    bridge_raw = read_bounded_bytes(bridge_path, MAX_STATE_BYTES)
    bridge_digest = (
        "missing-or-unreadable"
        if bridge_raw is None
        else hashlib.sha256(b"bridge-v1\0" + bridge_raw).hexdigest()
    )
    return {
        "schema": "harness.collaboration-recovery-evidence/v1",
        "agent_id": run.get("agent_id"),
        "agent_state": run.get("agent_state"),
        "agent_provider": run.get("agent_provider"),
        "bridge_handoff_digest": run.get("bridge_handoff_digest"),
        "bridge_trigger_digest": bridge_digest,
        "sidecars": sidecars,
        "lease_preserved": True,
        "daemon_restarted": False,
        "adapter_switched": False,
        "provider_switched": False,
    }


def _recovery_reference(bundle: dict[str, Any]) -> dict[str, Any]:
    encoded = _bounded_json(bundle).encode("utf-8")
    return {
        "schema": "harness.recovery-bundle-ref/v1",
        "file": "recovery-bundle.json",
        "digest": hashlib.sha256(encoded).hexdigest(),
        "failure": copy.deepcopy(bundle["failure"]),
    }


def _enter_recovery_unlocked(
    context: WorktreeContext,
    *,
    task_id: str,
    category: str,
    fingerprint: str,
    expected_mode: str | None = None,
) -> tuple[dict[str, Any], int]:
    run_path, run = _load_run(context, task_id, expected_mode=expected_mode)
    if run["state"] not in {
        "executing",
        "verifying",
        "reviewing",
        "repairing",
        "accepted",
    }:
        raise CodexDirectError("recovery cannot start from this task state")
    if run["state"] == "accepted" and run["commit_sha"] is not None:
        raise CodexDirectError("accepted committed tasks are terminal")
    if category not in {"adapter-failure", "repeated-failure", "repair-limit"}:
        raise CodexDirectError("recovery category is invalid")
    fingerprint = _require_digest(fingerprint, "failure fingerprint")
    contract = run["contract"]
    try:
        def inspect() -> tuple[list[str], list[str], str, str, str]:
            return (
                _changed_paths(context.root),
                _staged_paths(context.root),
                _git(context.root, "rev-parse", "HEAD").lower(),
                _git(context.root, "branch", "--show-current"),
                _diff_digest(context.root),
            )

        inspection = inspect()
        if inspection != inspect():
            raise CodexDirectAdapterError("repository changed during recovery inspection")
        changed_paths, staged_paths, head_sha, branch, diff_digest = inspection
        repository_inspection = "current"
    except CodexDirectError:
        changed_paths = []
        staged_paths = []
        head_sha = None
        branch = None
        diff_digest = None
        repository_inspection = "unavailable"
    bundle = _make_recovery_bundle(
        run,
        category=category,
        fingerprint=fingerprint,
        head_sha=head_sha,
        branch=branch,
        diff_digest=diff_digest,
        changed_paths=changed_paths,
        staged_paths=staged_paths,
        repository_inspection=repository_inspection,
    )
    if contract["execution"]["mode"] == "codex-paseo-claude":
        bundle["collaboration"] = _collaboration_recovery_evidence(
            run,
            run_path.parent,
            context.root
            / ".harness"
            / "coordination"
            / task_id
            / "bridge-trigger.json",
        )
    reference = _recovery_reference(bundle)
    _write_json(context, run_path.parent / reference["file"], bundle)
    run["state"] = "recovery-required"
    contract["state"] = "recovery-required"
    run["recovery_bundle"] = reference
    _add_history(run, "recovery-required", "recovery-required")
    _save_run(context, run_path, run)
    return _control(run, recovery_bundle=bundle), 6


@_serialized
def enter_recovery(
    context: WorktreeContext,
    *,
    task_id: str,
    category: str,
    fingerprint: str,
    expected_mode: str | None = "codex-direct",
) -> tuple[dict[str, Any], int]:
    if category != "adapter-failure":
        raise CodexDirectError("public recovery can record only adapter failures")
    return _enter_recovery_unlocked(
        context,
        task_id=task_id,
        category=category,
        fingerprint=fingerprint,
        expected_mode=expected_mode,
    )


def _begin_repair_unlocked(
    context: WorktreeContext,
    *,
    task_id: str,
    fingerprint: str,
    expected_mode: str | None = "codex-direct",
) -> tuple[dict[str, Any], int]:
    """Shared repair eligibility core — caller holds ``run.lock``."""
    run_path, run = _load_run(context, task_id, expected_mode=expected_mode)
    if run["state"] not in {"verifying", "reviewing"}:
        raise CodexDirectError("repair requires verifying or reviewing state")
    fingerprint = _require_digest(fingerprint, "failure fingerprint")
    snapshot = {
        "fingerprint": fingerprint,
        "diff_digest": _diff_digest(context.root),
        "evidence_digest": _checks_digest(run),
    }
    duplicate = any(
        all(attempt.get(key) == value for key, value in snapshot.items())
        for attempt in run["repairs"]
    )
    max_attempts = run["contract"]["plan"]["repair_policy"]["max_attempts"]
    if duplicate:
        return _enter_recovery_unlocked(
            context,
            task_id=task_id,
            category="repeated-failure",
            fingerprint=fingerprint,
            expected_mode=expected_mode,
        )
    if len(run["repairs"]) >= max_attempts:
        return _enter_recovery_unlocked(
            context,
            task_id=task_id,
            category="repair-limit",
            fingerprint=fingerprint,
            expected_mode=expected_mode,
        )

    attempt_number = len(run["repairs"]) + 1
    run["repairs"].append({"attempt": attempt_number, **snapshot})
    run["criteria"] = {}
    run["risks"] = {}
    run["state"] = "repairing"
    run["contract"]["state"] = "repairing"
    _add_history(run, "repair-started", "repairing")
    _save_run(context, run_path, run)
    return _control(run, repair_attempt=attempt_number), 0


@_serialized
def begin_repair(
    context: WorktreeContext,
    *,
    task_id: str,
    fingerprint: str,
    expected_mode: str | None = "codex-direct",
) -> tuple[dict[str, Any], int]:
    return _begin_repair_unlocked(
        context, task_id=task_id, fingerprint=fingerprint,
        expected_mode=expected_mode,
    )


def _commit_paths(root: Path, commit_sha: str) -> list[str]:
    return _git_paths(
        root,
        "diff-tree",
        "--no-commit-id",
        "--name-only",
        "--no-renames",
        "-r",
        "-z",
        commit_sha,
    )


def _commit_parents(root: Path, commit_sha: str) -> list[str]:
    fields = _git(root, "rev-list", "--parents", "-n", "1", commit_sha).split()
    if not fields or fields[0].lower() != commit_sha.lower() or any(
        not re.fullmatch(r"[0-9a-fA-F]{40}", field) for field in fields
    ):
        raise CodexDirectAdapterError("Git returned invalid commit ancestry")
    return [field.lower() for field in fields[1:]]


def _git_object_digest(object_id: str) -> str:
    normalized = object_id.lower()
    if not re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", normalized):
        raise CodexDirectAdapterError("Git returned an invalid object identity")
    return hashlib.sha256(b"git-object-v1\0" + normalized.encode("ascii")).hexdigest()


def _accepted_commit_structure_is_exact(
    context: WorktreeContext, run: dict[str, Any], commit_sha: str
) -> bool:
    contract = run["contract"]
    accepted_diff = run["accepted_diff"]
    paths = accepted_diff["paths"]
    trailer = f"Harness-Task: {_task_key(contract['task']['id'])}"
    return (
        _commit_parents(context.root, commit_sha) == [contract["execution"]["base_sha"]]
        and _git(context.root, "branch", "--show-current")
        == contract["execution"]["branch"]
        and trailer
        in _git(
            context.root, "log", "-1", "--encoding=UTF-8", "--format=%B", commit_sha
        ).splitlines()
        and _commit_paths(context.root, commit_sha) == paths
        and _commit_tree_snapshot(context.root, commit_sha, paths)
        == accepted_diff["index_snapshot"]
    )


def _accepted_commit_is_exact(
    context: WorktreeContext, run: dict[str, Any], commit_sha: str
) -> bool:
    accepted_diff = run["accepted_diff"]
    return (
        _accepted_commit_structure_is_exact(context, run, commit_sha)
        and _path_snapshot(context.root, accepted_diff["paths"])
        == accepted_diff["snapshot"]
        and not _git(context.root, "status", "--porcelain=v1", "--untracked-files=all")
    )


def _commit_tree_snapshot(
    root: Path, commit_sha: str, paths: list[str]
) -> list[dict[str, Any]]:
    snapshot: list[dict[str, Any]] = []
    for path in paths:
        raw = _git_bytes(root, "ls-tree", "-z", commit_sha, "--", path)
        if not raw:
            snapshot.append({"path": path, "kind": "deleted", "digest": None})
            continue
        records = [record for record in raw.split(b"\0") if record]
        if len(records) != 1 or b"\t" not in records[0]:
            raise CodexDirectAdapterError("commit tree entry is ambiguous")
        header, raw_path = records[0].split(b"\t", 1)
        try:
            mode, object_type, object_id = header.decode("ascii").split(" ")
            tree_path = raw_path.decode("utf-8", errors="strict").replace("\\", "/")
        except (UnicodeDecodeError, ValueError) as exc:
            raise CodexDirectAdapterError("commit tree entry is invalid") from exc
        if tree_path != path or object_type != "blob":
            raise CodexDirectAdapterError("commit tree entry does not match accepted path")
        content_digest = _git_object_digest(object_id)
        if mode == "120000":
            snapshot.append(
                {"path": path, "kind": "symlink", "digest": content_digest}
            )
        elif mode in {"100644", "100755"}:
            snapshot.append(
                {
                    "path": path,
                    "kind": "file",
                    "executable": mode == "100755",
                    "digest": content_digest,
                }
            )
        else:
            raise CodexDirectAdapterError("commit tree entry type is unsupported")
    return snapshot


def _index_snapshot(
    root: Path,
    paths: list[str],
    *,
    env_overrides: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    snapshot: list[dict[str, Any]] = []
    for path in paths:
        raw = _run_git_bytes(
            root,
            ("ls-files", "--stage", "-z", "--", path),
            env_overrides=env_overrides,
        )
        if not raw:
            snapshot.append({"path": path, "kind": "deleted", "digest": None})
            continue
        records = [record for record in raw.split(b"\0") if record]
        if len(records) != 1 or b"\t" not in records[0]:
            raise CodexDirectAdapterError("index entry is ambiguous")
        header, raw_path = records[0].split(b"\t", 1)
        try:
            mode, object_id, stage = header.decode("ascii").split(" ")
            index_path = raw_path.decode("utf-8", errors="strict").replace("\\", "/")
        except (UnicodeDecodeError, ValueError) as exc:
            raise CodexDirectAdapterError("index entry is invalid") from exc
        if index_path != path or stage != "0":
            raise CodexDirectAdapterError("index entry does not match accepted path")
        content_digest = _git_object_digest(object_id)
        if mode == "120000":
            snapshot.append(
                {"path": path, "kind": "symlink", "digest": content_digest}
            )
        elif mode in {"100644", "100755"}:
            snapshot.append(
                {
                    "path": path,
                    "kind": "file",
                    "executable": mode == "100755",
                    "digest": content_digest,
                }
            )
        else:
            raise CodexDirectAdapterError("index entry type is unsupported")
    return snapshot


def _hermetic_config_args(root: Path) -> tuple[str, ...]:
    settings = (
        ("core.autocrlf", "false", {"false", "true", "input"}),
        ("core.eol", "native", {"native", "lf", "crlf"}),
        ("core.safecrlf", "false", {"false", "true", "warn"}),
        ("core.filemode", "true", {"false", "true"}),
        ("core.symlinks", "true", {"false", "true"}),
        ("core.ignorecase", "false", {"false", "true"}),
    )
    args: list[str] = ["-c", "core.bare=false", "-c", f"core.attributesFile={os.devnull}"]
    for key, default, allowed in settings:
        value = _git(root, "config", f"--default={default}", key).lower()
        if value not in allowed:
            raise CodexDirectError(f"repository {key} setting is unsupported")
        args.extend(("-c", f"{key}={value}"))
    return tuple(args)


@contextmanager
def _hermetic_index_environment(
    context: WorktreeContext, *, write_objects: bool
) -> Iterator[tuple[dict[str, str], Path]]:
    with tempfile.TemporaryDirectory(prefix="harness-codex-direct-") as raw_scratch:
        scratch = Path(raw_scratch)
        git_dir = scratch / "git"
        (git_dir / "objects").mkdir(parents=True)
        (git_dir / "refs").mkdir()
        (git_dir / "HEAD").write_text(
            "ref: refs/heads/harness-isolated\n", encoding="ascii"
        )
        object_directory = (
            context.common_git_dir / "objects" if write_objects else git_dir / "objects"
        )
        environment = {
            "GIT_DIR": str(git_dir),
            "GIT_WORK_TREE": str(context.root),
            "GIT_INDEX_FILE": str(scratch / "index"),
            "GIT_OBJECT_DIRECTORY": str(object_directory),
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_SYSTEM": os.devnull,
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_ATTR_NOSYSTEM": "1",
        }
        if not write_objects:
            environment["GIT_ALTERNATE_OBJECT_DIRECTORIES"] = str(
                context.common_git_dir / "objects"
            )
        yield environment, scratch / "index"


def _build_ticket_index(
    context: WorktreeContext,
    *,
    base_sha: str,
    paths: list[str],
    write_objects: bool,
) -> tuple[list[dict[str, Any]], str, bytes]:
    if any(PurePosixPath(path).name == ".gitattributes" for path in paths):
        raise CodexDirectError(
            "automatic accepted commit refuses Git attribute policy changes"
        )
    _reject_filtered_paths(context.root, paths)
    config_args = _hermetic_config_args(context.root)
    with _hermetic_index_environment(
        context, write_objects=write_objects
    ) as (environment, index_path):
        _run_git_bytes(
            context.root,
            (*config_args, "read-tree", base_sha),
            env_overrides=environment,
        )
        for batch in _path_argument_batches(paths):
            _run_git_bytes(
                context.root,
                (
                    *config_args,
                    f"--attr-source={base_sha}",
                    "add",
                    "-A",
                    "--",
                    *batch,
                ),
                env_overrides=environment,
            )
        staged_paths = _git_paths(
            context.root,
            *config_args,
            "diff",
            "--cached",
            "--name-only",
            "--no-renames",
            "--no-ext-diff",
            "--no-textconv",
            "-z",
            base_sha,
            "--",
            env_overrides=environment,
        )
        if staged_paths != paths:
            raise CodexDirectAdapterError(
                "isolated index paths do not exactly match the accepted diff"
            )
        snapshot = _index_snapshot(
            context.root, paths, env_overrides=environment
        )
        tree_sha = _git(
            context.root, *config_args, "write-tree", env_overrides=environment
        ).lower()
        if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", tree_sha):
            raise CodexDirectAdapterError("isolated Git tree identity is invalid")
        index_bytes = read_bounded_bytes(index_path, MAX_INDEX_BYTES)
        if index_bytes is None:
            raise CodexDirectAdapterError("isolated Git index was not created")
        return snapshot, tree_sha, index_bytes


def _canonical_index_snapshot(
    context: WorktreeContext, paths: list[str]
) -> list[dict[str, Any]]:
    base_sha = _git(context.root, "rev-parse", "HEAD").lower()
    snapshot, _, _ = _build_ticket_index(
        context,
        base_sha=base_sha,
        paths=paths,
        write_objects=False,
    )
    return snapshot


def _index_from_tree(
    context: WorktreeContext, tree_sha: str, paths: list[str]
) -> tuple[list[dict[str, Any]], bytes]:
    config_args = _hermetic_config_args(context.root)
    with _hermetic_index_environment(
        context, write_objects=False
    ) as (environment, index_path):
        _run_git_bytes(
            context.root,
            (*config_args, "read-tree", tree_sha),
            env_overrides=environment,
        )
        snapshot = _index_snapshot(
            context.root, paths, env_overrides=environment
        )
        index_bytes = read_bounded_bytes(index_path, MAX_INDEX_BYTES)
        if index_bytes is None:
            raise CodexDirectAdapterError("isolated Git index was not created")
        return snapshot, index_bytes


@contextmanager
def _open_index_lock(
    context: WorktreeContext,
) -> Iterator[tuple[int, Callable[[], None]]]:
    lock_path = context.git_dir / "index.lock"
    index_path = context.git_dir / "index"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor: int | None = None
    parent_descriptor: int | None = None
    installed = False
    directory_identity: tuple[int, int] | None = None
    try:
        if os.name == "nt":
            with _hold_windows_directory_chain(context.git_dir):
                directory = os.stat(context.git_dir, follow_symlinks=False)
                directory_identity = (directory.st_dev, directory.st_ino)
                descriptor = os.open(lock_path, flags, 0o600)
                current = os.stat(lock_path, follow_symlinks=False)
        else:
            parent_descriptor = _open_directory_nofollow(context.git_dir)
            directory = os.fstat(parent_descriptor)
            directory_identity = (directory.st_dev, directory.st_ino)
            descriptor = os.open(
                lock_path.name, flags, 0o600, dir_fd=parent_descriptor
            )
            current = os.stat(
                lock_path.name,
                dir_fd=parent_descriptor,
                follow_symlinks=False,
            )
        opened = os.fstat(descriptor)
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_nlink != 1
            or (opened.st_dev, opened.st_ino) != (current.st_dev, current.st_ino)
        ):
            raise OSError("Git index lock identity changed")
        if parent_descriptor is not None:
            visible_directory = os.stat(context.git_dir, follow_symlinks=False)
            if directory_identity != (
                visible_directory.st_dev,
                visible_directory.st_ino,
            ):
                raise OSError("canonical Git directory identity changed")
    except (OSError, ValueError) as exc:
        lock_created = descriptor is not None
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass
            descriptor = None
        if lock_created:
            try:
                if parent_descriptor is None:
                    with _hold_windows_directory_chain(context.git_dir):
                        lock_path.unlink(missing_ok=True)
                else:
                    os.unlink(lock_path.name, dir_fd=parent_descriptor)
            except (OSError, ValueError):
                pass
        if parent_descriptor is not None:
            os.close(parent_descriptor)
            parent_descriptor = None
        raise CodexDirectAdapterError(
            "canonical Git index lock is unavailable"
        ) from exc

    identity = (opened.st_dev, opened.st_ino)

    def install() -> None:
        nonlocal descriptor, installed
        assert descriptor is not None
        if parent_descriptor is None:
            try:
                with _hold_windows_directory_chain(context.git_dir):
                    directory = os.stat(context.git_dir, follow_symlinks=False)
                    if directory_identity != (directory.st_dev, directory.st_ino):
                        raise OSError("canonical Git directory identity changed")
                    visible = os.stat(lock_path, follow_symlinks=False)
                    if identity != (visible.st_dev, visible.st_ino):
                        raise OSError("Git index lock identity changed")
                    os.close(descriptor)
                    descriptor = None
                    os.replace(lock_path, index_path)
                    installed = True
                    visible = os.stat(index_path, follow_symlinks=False)
            except ValueError as exc:
                raise OSError("canonical Git directory is unavailable") from exc
        else:
            visible = os.stat(
                lock_path.name,
                dir_fd=parent_descriptor,
                follow_symlinks=False,
            )
            if identity != (visible.st_dev, visible.st_ino):
                raise OSError("Git index lock identity changed")
            os.replace(
                lock_path.name,
                index_path.name,
                src_dir_fd=parent_descriptor,
                dst_dir_fd=parent_descriptor,
            )
            installed = True
            visible = os.stat(
                index_path.name,
                dir_fd=parent_descriptor,
                follow_symlinks=False,
            )
            os.close(descriptor)
            descriptor = None
        if identity != (visible.st_dev, visible.st_ino):
            raise OSError("installed Git index identity changed")

    try:
        yield descriptor, install
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if not installed:
            if parent_descriptor is None:
                try:
                    with _hold_windows_directory_chain(context.git_dir):
                        directory = os.stat(context.git_dir, follow_symlinks=False)
                        if directory_identity == (directory.st_dev, directory.st_ino):
                            lock_path.unlink(missing_ok=True)
                except (OSError, ValueError):
                    pass
            else:
                try:
                    os.unlink(lock_path.name, dir_fd=parent_descriptor)
                except FileNotFoundError:
                    pass
        if parent_descriptor is not None:
            os.close(parent_descriptor)


def _write_locked_index(descriptor: int, index_bytes: bytes) -> None:
    try:
        view = memoryview(index_bytes)
        written = 0
        while written < len(view):
            count = os.write(descriptor, view[written:])
            if count <= 0:
                raise OSError("short Git index write")
            written += count
        os.fsync(descriptor)
    except OSError as exc:
        raise CodexDirectAdapterError("canonical Git index write failed") from exc


def _commit_identity_environment(root: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for config_key, author_key, committer_key in (
        ("user.name", "GIT_AUTHOR_NAME", "GIT_COMMITTER_NAME"),
        ("user.email", "GIT_AUTHOR_EMAIL", "GIT_COMMITTER_EMAIL"),
    ):
        value = _git(root, "config", "--get", config_key)
        if (
            not value
            or len(value) > 256
            or any(ord(character) < 32 or ord(character) == 127 for character in value)
        ):
            raise CodexDirectError("Git commit identity is missing or unsafe")
        values[author_key] = value
        values[committer_key] = value
    return values


def _commit_unlocked(
    context: WorktreeContext,
    *,
    task_id: str,
    message: str,
    expected_mode: str | None = None,
) -> dict[str, Any]:
    run_path, run = _load_run(context, task_id, expected_mode=expected_mode)
    if run["state"] != "accepted":
        raise CodexDirectError("local commit is unavailable before acceptance")
    _require_commit_message(message)

    current_head = _git(context.root, "rev-parse", "HEAD").lower()
    _reject_in_progress_git_operation(context)
    if run["commit_sha"] is not None:
        if current_head != run["commit_sha"] or not _accepted_commit_is_exact(
            context, run, current_head
        ):
            raise CodexDirectError("HEAD moved after the accepted local commit")
        return _control(
            run,
            commit_status="already-committed",
            commit_sha=run["commit_sha"],
        )

    contract = run["contract"]
    base_sha = contract["execution"]["base_sha"]
    owned_paths = contract["plan"]["owned_paths"]
    task_key = _task_key(task_id)
    trailer = f"Harness-Task: {task_key}"
    accepted_diff = run.get("accepted_diff", {})
    if current_head != base_sha:
        if not _accepted_commit_structure_is_exact(context, run, current_head):
            raise CodexDirectError("HEAD does not match the accepted ticket commit")
        if not _accepted_commit_is_exact(context, run, current_head):
            paths = accepted_diff["paths"]
            if (
                _path_snapshot(context.root, paths) != accepted_diff["snapshot"]
                or _changed_paths(context.root) != paths
            ):
                raise CodexDirectError(
                    "accepted ticket commit has unresolved working tree changes"
                )
            try:
                with _open_index_lock(context) as (descriptor, install_index):
                    if (
                        _git(context.root, "rev-parse", "HEAD").lower()
                        != current_head
                        or _path_snapshot(context.root, paths)
                        != accepted_diff["snapshot"]
                        or _changed_paths(context.root) != paths
                    ):
                        raise CodexDirectError(
                            "accepted ticket commit changed during index recovery"
                        )
                    recovered_snapshot, index_bytes = _index_from_tree(
                        context, current_head, paths
                    )
                    if recovered_snapshot != accepted_diff["index_snapshot"]:
                        raise CodexDirectError(
                            "accepted ticket commit index cannot be recovered exactly"
                        )
                    _write_locked_index(descriptor, index_bytes)
                    install_index()
            except OSError as exc:
                raise CodexDirectAdapterError(
                    "accepted ticket commit index recovery failed"
                ) from exc
            if not _accepted_commit_is_exact(context, run, current_head):
                raise CodexDirectAdapterError(
                    "accepted ticket commit recovery failed its postcondition"
                )
        run["commit_sha"] = current_head
        contract["writer_lease"] = {
            "holder": WRITERS[contract["execution"]["mode"]],
            "state": "released",
        }
        _add_history(run, "commit-recovered", "accepted")
        _save_run(context, run_path, run)
        return _control(
            run,
            commit_status="already-committed",
            commit_sha=current_head,
        )

    if _git(context.root, "branch", "--show-current") != contract["execution"]["branch"]:
        raise CodexDirectError("branch changed before the accepted local commit")
    changed_paths = _changed_paths(context.root)
    current_snapshot = _path_snapshot(context.root, changed_paths)
    if (
        changed_paths != accepted_diff.get("paths")
        or current_snapshot != accepted_diff.get("snapshot")
        or _snapshot_digest(current_snapshot) != accepted_diff.get("digest")
    ):
        raise CodexDirectError("working tree no longer matches the accepted diff")
    if not changed_paths or any(
        not _path_is_owned(path, owned_paths) for path in changed_paths
    ):
        raise CodexDirectError("accepted local commit contains an unowned path")

    identity_environment = _commit_identity_environment(context.root)
    try:
        with _open_index_lock(context) as (descriptor, install_index):
            branch_ref = _git(context.root, "symbolic-ref", "--quiet", "HEAD")
            if branch_ref != f"refs/heads/{contract['execution']['branch']}":
                raise CodexDirectError(
                    "branch changed before the accepted local commit"
                )
            if (
                _git(context.root, "rev-parse", "HEAD").lower() != base_sha
                or _changed_paths(context.root) != changed_paths
                or _path_snapshot(context.root, changed_paths)
                != accepted_diff["snapshot"]
            ):
                raise CodexDirectError("working tree changed before isolated staging")
            index_snapshot, tree_sha, index_bytes = _build_ticket_index(
                context,
                base_sha=base_sha,
                paths=changed_paths,
                write_objects=True,
            )
            if index_snapshot != accepted_diff.get("index_snapshot"):
                raise CodexDirectAdapterError(
                    "isolated index no longer matches the accepted canonical tree"
                )
            commit_message = f"{message}\n\n{trailer}\n".encode("utf-8")
            commit_sha = _run_git_bytes(
                context.root,
                (
                    "-c",
                    "i18n.commitEncoding=UTF-8",
                    "commit-tree",
                    tree_sha,
                    "-p",
                    base_sha,
                ),
                input_bytes=commit_message,
                env_overrides=identity_environment,
            ).decode("ascii", errors="strict").strip().lower()
            if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", commit_sha):
                raise CodexDirectAdapterError("created commit identity is invalid")
            if not _accepted_commit_structure_is_exact(context, run, commit_sha):
                raise CodexDirectAdapterError(
                    "created commit failed the ticket-scope structural postcondition"
                )
            if (
                _git(context.root, "rev-parse", "HEAD").lower() != base_sha
                or _changed_paths(context.root) != changed_paths
                or _path_snapshot(context.root, changed_paths)
                != accepted_diff["snapshot"]
            ):
                raise CodexDirectError(
                    "working tree changed during accepted commit creation"
                )
            _write_locked_index(descriptor, index_bytes)
            _git(context.root, "update-ref", branch_ref, commit_sha, base_sha)
            install_index()
    except UnicodeDecodeError as exc:
        raise CodexDirectAdapterError("created commit identity is invalid") from exc
    except OSError as exc:
        raise CodexDirectAdapterError("accepted Git index installation failed") from exc

    if not _accepted_commit_is_exact(context, run, commit_sha):
        raise CodexDirectAdapterError(
            "created commit failed the ticket-scope postcondition"
        )
    run["commit_sha"] = commit_sha
    contract["writer_lease"] = {
        "holder": WRITERS[contract["execution"]["mode"]],
        "state": "released",
    }
    _add_history(run, "local-commit-created", "accepted")
    _save_run(context, run_path, run)
    return _control(run, commit_status="created", commit_sha=commit_sha)


@_serialized
def commit_codex_direct(
    context: WorktreeContext,
    *,
    task_id: str,
    message: str,
    expected_mode: str | None = "codex-direct",
) -> dict[str, Any]:
    return _commit_unlocked(
        context,
        task_id=task_id,
        message=message,
        expected_mode=expected_mode,
    )


def _digest_or_marker(value: Any) -> bool:
    return isinstance(value, str) and (
        re.fullmatch(r"[0-9a-f]{64}", value)
        or value == "missing-or-unreadable"
    )


def _validate_collaboration_evidence(evidence: Any, run: dict[str, Any]) -> None:
    """Validate the bounded collaboration section of a recovery bundle.

    Exact key set, digest-or-marker formats, identity bound to the last
    persisted run record, and no-fallback policy flags.
    """
    invalid = "Recovery Bundle collaboration evidence is invalid"
    if not isinstance(evidence, dict):
        raise CodexDirectError(invalid)
    if set(evidence) != {
        "schema", "agent_id", "agent_state", "agent_provider",
        "bridge_handoff_digest", "bridge_trigger_digest", "sidecars",
        "lease_preserved", "daemon_restarted", "adapter_switched",
        "provider_switched",
    }:
        raise CodexDirectError(invalid)
    if evidence.get("schema") != "harness.collaboration-recovery-evidence/v1":
        raise CodexDirectError(invalid)
    for key in (
        "agent_id", "agent_state", "agent_provider", "bridge_handoff_digest",
    ):
        if evidence.get(key) != run.get(key):
            raise CodexDirectError(invalid)
    handoff_digest = evidence.get("bridge_handoff_digest")
    if not isinstance(handoff_digest, str) or not re.fullmatch(
        r"[0-9a-f]{64}", handoff_digest
    ):
        raise CodexDirectError(invalid)
    if not _digest_or_marker(evidence.get("bridge_trigger_digest")):
        raise CodexDirectError(invalid)
    sidecars = evidence.get("sidecars")
    if (
        not isinstance(sidecars, dict)
        or set(sidecars) != set(COLLABORATION_RECOVERY_SIDECARS)
        or any(not _digest_or_marker(value) for value in sidecars.values())
    ):
        raise CodexDirectError(invalid)
    if (
        evidence.get("lease_preserved") is not True
        or evidence.get("daemon_restarted") is not False
        or evidence.get("adapter_switched") is not False
        or evidence.get("provider_switched") is not False
    ):
        raise CodexDirectError(invalid)


def _validate_recovery_bundle_shape(
    bundle: dict[str, Any], run: dict[str, Any], reference: dict[str, Any]
) -> None:
    keys = {
        "schema", "task_id", "mode", "repository_id", "worktree_id", "base_sha",
        "head_sha", "branch", "repository_inspection", "diff_digest",
        "changed_paths", "changed_path_count", "changed_paths_digest",
        "changed_paths_embedded", "staged_paths", "staged_path_count",
        "staged_paths_digest", "staged_paths_embedded", "owned_paths",
        "owned_path_count", "owned_paths_digest", "owned_paths_embedded",
        "validations", "incomplete_criteria", "risks", "repair_attempts",
        "writer_lease", "adapter_switch_policy", "failure", "commit_sha",
    }
    contract = run["contract"]
    if contract["execution"]["mode"] == "codex-paseo-claude":
        if set(bundle) != keys | {"collaboration"}:
            raise CodexDirectError("Recovery Bundle is unavailable or invalid")
        _validate_collaboration_evidence(bundle.get("collaboration"), run)
    elif set(bundle) != keys:
        raise CodexDirectError("Recovery Bundle is unavailable or invalid")
    if bundle.get("schema") != "harness.recovery-bundle/v1":
        raise CodexDirectError("Recovery Bundle is unavailable or invalid")
    if (
        bundle.get("task_id") != contract["task"]["id"]
        or bundle.get("mode") != contract["execution"]["mode"]
        or bundle.get("repository_id") != contract["execution"]["repository_id"]
        or bundle.get("worktree_id") != contract["execution"]["worktree_id"]
        or bundle.get("base_sha") != contract["execution"]["base_sha"]
        or bundle.get("writer_lease") != contract["writer_lease"]
        or bundle.get("adapter_switch_policy") != "stop-and-report"
        or bundle.get("failure") != reference.get("failure")
        or bundle.get("commit_sha") != run["commit_sha"]
        or bundle.get("repair_attempts") != len(run["repairs"])
    ):
        raise CodexDirectError("Recovery Bundle is unavailable or invalid")

    for paths_key, count_key, digest_key, embedded_key in (
        ("changed_paths", "changed_path_count", "changed_paths_digest", "changed_paths_embedded"),
        ("staged_paths", "staged_path_count", "staged_paths_digest", "staged_paths_embedded"),
        ("owned_paths", "owned_path_count", "owned_paths_digest", "owned_paths_embedded"),
    ):
        paths = bundle[paths_key]
        count = bundle[count_key]
        digest = bundle[digest_key]
        embedded = bundle[embedded_key]
        if (
            not isinstance(paths, list)
            or any(not isinstance(path, str) for path in paths)
            or not isinstance(count, int)
            or isinstance(count, bool)
            or not 0 <= count <= 1_000_000
            or not isinstance(embedded, bool)
            or not isinstance(digest, str)
            or not re.fullmatch(r"[0-9a-f]{64}", digest)
            or (embedded and count != len(paths))
            or (embedded and paths != sorted(set(paths)))
            or (not embedded and paths)
        ):
            raise CodexDirectError("Recovery Bundle path evidence is invalid")
        if embedded:
            expected = _recovery_path_evidence(paths)
            if expected["digest"] != digest or not expected["embedded"]:
                raise CodexDirectError("Recovery Bundle path evidence is invalid")

    owned = _recovery_path_evidence(contract["plan"]["owned_paths"])
    if any(
        bundle[key] != value
        for key, value in {
            "owned_paths": owned["paths"],
            "owned_path_count": owned["count"],
            "owned_paths_digest": owned["digest"],
            "owned_paths_embedded": owned["embedded"],
        }.items()
    ):
        raise CodexDirectError("Recovery Bundle ownership evidence is invalid")
    expected_validations = [
        copy.deepcopy(record) for record in run["evidence_log"]
    ]
    expected_risks = [
        {"id": risk_id, **run["risks"][risk_id]}
        for risk_id in sorted(run["risks"])
    ]
    expected_incomplete = sorted(
        item["id"]
        for item in contract["plan"]["acceptance_criteria"]
        if run["criteria"].get(item["id"], {}).get("status") != "pass"
    )
    if (
        bundle["validations"] != expected_validations
        or bundle["risks"] != expected_risks
        or bundle["incomplete_criteria"] != expected_incomplete
    ):
        raise CodexDirectError("Recovery Bundle evidence is invalid")
    inspection = bundle["repository_inspection"]
    if inspection == "unavailable":
        empty = _recovery_path_evidence([])
        if any(bundle[key] is not None for key in ("head_sha", "branch", "diff_digest")) or any(
            bundle[key] != value
            for key, value in {
                "changed_paths": empty["paths"],
                "changed_path_count": empty["count"],
                "changed_paths_digest": empty["digest"],
                "changed_paths_embedded": empty["embedded"],
                "staged_paths": empty["paths"],
                "staged_path_count": empty["count"],
                "staged_paths_digest": empty["digest"],
                "staged_paths_embedded": empty["embedded"],
            }.items()
        ):
            raise CodexDirectError("Recovery Bundle inspection evidence is invalid")
    elif inspection == "current":
        if (
            not re.fullmatch(r"[0-9a-f]{40}", str(bundle["head_sha"]))
            or not isinstance(bundle["branch"], str)
            or not re.fullmatch(r"[0-9a-f]{64}", str(bundle["diff_digest"]))
        ):
            raise CodexDirectError("Recovery Bundle inspection evidence is invalid")
        if bundle["staged_path_count"] > bundle["changed_path_count"] or (
            bundle["staged_paths_embedded"]
            and bundle["changed_paths_embedded"]
            and not set(bundle["staged_paths"]) <= set(bundle["changed_paths"])
        ):
            raise CodexDirectError("Recovery Bundle inspection evidence is invalid")
        if bundle["failure"]["category"] == "repeated-failure" and not any(
            repair["fingerprint"] == bundle["failure"]["fingerprint"]
            and repair["diff_digest"] == bundle["diff_digest"]
            and repair["evidence_digest"] == _checks_digest(run)
            for repair in run["repairs"]
        ):
            raise CodexDirectError("Recovery Bundle repeated-failure premise is invalid")
    else:
        raise CodexDirectError("Recovery Bundle inspection evidence is invalid")


def _read_recovery_bundle(
    context: WorktreeContext, run_path: Path, run: dict[str, Any]
) -> dict[str, Any] | None:
    reference = run.get("recovery_bundle")
    if reference is None:
        return None
    if not isinstance(reference, dict):
        raise CodexDirectError("Recovery Bundle reference is invalid")
    if (
        reference.get("schema") != "harness.recovery-bundle-ref/v1"
        or reference.get("file") != "recovery-bundle.json"
    ):
        raise CodexDirectError("Recovery Bundle reference is invalid")
    bundle_path = run_path.parent / reference["file"]
    ensure_no_link_components(context.root, bundle_path.parent)
    bundle = read_bounded_json_object(
        bundle_path, MAX_STATE_BYTES, max_nodes=MAX_STATE_NODES
    )
    if (
        bundle.get("schema") != "harness.recovery-bundle/v1"
        or hashlib.sha256(_bounded_json(bundle).encode("utf-8")).hexdigest()
        != reference.get("digest")
    ):
        raise CodexDirectError("Recovery Bundle is unavailable or invalid")
    _validate_recovery_bundle_shape(bundle, run, reference)
    return bundle


@_serialized
def codex_direct_status(
    context: WorktreeContext,
    *,
    task_id: str,
    expected_mode: str | None = "codex-direct",
) -> dict[str, Any]:
    run_path, run = _load_run(context, task_id, expected_mode=expected_mode)
    return _control(
        run,
        checks=run["checks"],
        evidence_log=run["evidence_log"],
        criteria=run["criteria"],
        risks=run["risks"],
        repairs=run["repairs"],
        accepted_diff=run.get("accepted_diff"),
        recovery_bundle=_read_recovery_bundle(context, run_path, run),
        commit_sha=run["commit_sha"],
        history=run["history"],
    )


def _start_codex_direct_unlocked(
    context: WorktreeContext,
    contract: dict[str, Any],
    known_roots: list[Path],
) -> tuple[dict[str, Any], int]:
    task_id = contract["task"]["id"]
    mode = contract["execution"]["mode"]
    writer = WRITERS[mode]
    source_digest = _task_source_digest(contract)
    reminder_identity = f"source:{source_digest}"
    task_dir = _task_dir(context, task_id)
    run_path = task_dir / "run.json"
    ensure_no_link_components(context.root, task_dir)
    if run_path.exists() or run_path.is_symlink():
        existing = read_bounded_json_object(
            run_path, MAX_STATE_BYTES, max_nodes=MAX_STATE_NODES
        )
        if existing.get("schema") in RUN_SCHEMAS.values():
            raise CodexDirectError(
                "execution mode is already frozen and a writer lease exists for this task"
            )
        raise CodexDirectError("existing Codex Direct task state is invalid")

    expected_root = Path(contract["execution"]["canonical_worktree"]).resolve()
    if os.path.normcase(str(expected_root)) != os.path.normcase(str(context.root.resolve())):
        raise CodexDirectError("canonical worktree does not match the active worktree")

    head_sha = _git(context.root, "rev-parse", "HEAD").lower()
    if head_sha != contract["execution"]["base_sha"].lower():
        raise CodexDirectError("canonical worktree baseline is stale")
    if _git(context.root, "branch", "--show-current") != contract["execution"]["branch"]:
        raise CodexDirectError("canonical worktree branch does not match the contract")
    _reject_in_progress_git_operation(context)
    _reject_repository_filters(context.root, contract["plan"]["owned_paths"])
    if _git(context.root, "status", "--porcelain=v1", "--untracked-files=all"):
        raise CodexDirectError("canonical worktree must be clean before writer acquisition")

    for skill in contract["required_manual_skills"]:
        if skill["status"] == "invoked":
            continue
        _reject_ticket_in_other_worktree(
            context, known_roots, task_id, source_digest
        )
        if _manual_skill_was_reminded_elsewhere(
            context,
            known_roots,
            task_id=reminder_identity,
            adapter=mode,
            host=skill["host"],
            skill=skill["name"],
        ):
            result = {
                "schema": "harness.manual-skill-gate/v1",
                "task_id": task_id,
                "adapter": mode,
                "host": skill["host"],
                "skill": skill["name"],
                "native_invocation": (
                    f"/{skill['name']}"
                    if skill["host"] == "claude"
                    else f"${skill['name']}"
                ),
                "status": "already-reminded",
                "message": None,
            }
        else:
            result = check_manual_skill(
                runtime_root=context.runtime_root,
                task_id=reminder_identity,
                adapter=mode,
                host=skill["host"],
                skill=skill["name"],
                invoked=False,
                worktree_root=context.root,
            )
            result["task_id"] = task_id
        return (
            {
                "schema": CONTROL_SCHEMAS[mode],
                "task_id": task_id,
                "mode": mode,
                "state": "awaiting-user",
                "writer_lease": {"holder": writer, "state": "inactive"},
                "manual_skill": result,
            },
            3,
        )

    frozen = _runtime_contract(context, contract)
    empty_digest = hashlib.sha256(b"").hexdigest()
    run = {
        "schema": RUN_SCHEMAS[mode],
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
            "branch": contract["execution"]["branch"],
            "status_digest": empty_digest,
        },
        "checks": {},
        "evidence_log": [],
        "criteria": {},
        "risks": {},
        "repairs": [],
        "commit_sha": None,
    }
    _reject_ticket_in_other_worktree(context, known_roots, task_id, source_digest)
    ensure_no_link_components(context.root, task_dir)
    _save_run(context, run_path, run)
    return _control(run), 0


def _repository_lock_identity(path: Path) -> tuple[int, int, int, int]:
    try:
        info = path.stat()
    except OSError as exc:
        raise CodexDirectError("repository control lock is unavailable") from exc
    return (
        info.st_dev,
        info.st_ino,
        info.st_size,
        info.st_mtime_ns,
    )


def _rollback_unstable_start(
    context: WorktreeContext, contract: dict[str, Any], result: tuple[dict[str, Any], int]
) -> None:
    control, exit_code = result
    if exit_code == 0:
        run_path = _task_dir(context, contract["task"]["id"]) / "run.json"
        if run_path.is_file() and not run_path.is_symlink():
            _unlink_nofollow(run_path)
    elif exit_code == 3 and control.get("manual_skill", {}).get("status") == "reminder-emitted":
        skill = next(
            item for item in contract["required_manual_skills"] if item["status"] != "invoked"
        )
        reminder_id = manual_skill_reminder_id(
            task_id=f"source:{_task_source_digest(contract)}",
            adapter=contract["execution"]["mode"],
            host=skill["host"],
            skill=skill["name"],
        )
        marker = context.runtime_root / "manual-skill-reminders" / f"{reminder_id}.json"
        if marker.is_file() and not marker.is_symlink():
            _unlink_nofollow(marker)


def start_direct(
    context: WorktreeContext,
    contract_value: dict[str, Any],
    *,
    mode: str,
) -> tuple[dict[str, Any], int]:
    contract = validate_direct_contract(contract_value, mode)
    task_id = contract["task"]["id"]
    task_dir = _task_dir(context, task_id)
    ensure_no_link_components(context.root, task_dir)
    repository_lock = context.common_git_dir / "config"
    if (
        not repository_lock.exists()
        or not repository_lock.is_file()
        or repository_lock.is_symlink()
        or repository_lock.stat().st_size == 0
    ):
        raise CodexDirectError("repository control lock is unavailable")
    expected_lock_identity = _repository_lock_identity(repository_lock)
    known_roots = _git_worktree_roots(context)
    with bounded_file_lock(task_dir / "run.lock"):
        with _repository_mutex(context, repository_lock):
            if _repository_lock_identity(repository_lock) != expected_lock_identity:
                raise CodexDirectError("repository control lock changed before acquisition")
            result = _start_codex_direct_unlocked(context, contract, known_roots)
            if _repository_lock_identity(repository_lock) != expected_lock_identity:
                _rollback_unstable_start(context, contract, result)
                raise CodexDirectError("repository control lock changed during acquisition")
            return result


def start_codex_direct(
    context: WorktreeContext, contract_value: dict[str, Any]
) -> tuple[dict[str, Any], int]:
    return start_direct(context, contract_value, mode="codex-direct")


def start_claude_direct(
    context: WorktreeContext, contract_value: dict[str, Any]
) -> tuple[dict[str, Any], int]:
    return start_direct(context, contract_value, mode="claude-direct")
