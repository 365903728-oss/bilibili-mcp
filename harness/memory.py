"""Deterministic typed memory projected only from accepted Harness evidence."""

from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import re
import stat
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from harness.codex_direct import (
    CodexDirectError,
    _commit_parents,
    _commit_paths,
    _commit_tree_snapshot,
    _git_bytes,
    _git_paths,
    _load_run,
    _snapshot_digest,
    _task_dir,
    _valid_snapshot,
    codex_direct_status,
)
from harness.context import WorktreeContext
from harness.safe_io import (
    _atomic_write_bytes,
    _ensure_directory_nofollow,
    _unlink_nofollow,
    append_bounded_jsonl,
    bounded_file_lock,
    ensure_no_link_components,
    read_bounded_bytes,
    read_bounded_json_object,
    validate_json_shape,
)


STORE_PATH = Path("docs/agent-memory/typed-memory.json")
PROJECTION_PATH = Path("docs/agent-memory/current-memory.json")
CAPABILITY_SOURCE_PATH = (
    Path(__file__).resolve().parent
    / "capability-packages"
    / "bilibili-mcp-memory"
    / "canonical.json"
)
MAX_ENVELOPE_BYTES = 256 * 1024
MAX_STORE_BYTES = 1024 * 1024
MAX_PROJECTION_BYTES = 128 * 1024
MAX_TRANSACTION_BYTES = 4 * 1024
MAX_PROJECTION_NODES = 12_000
MAX_RECORDS = 512
MAX_CURRENT_RECORDS = 64
MAX_CANDIDATES = 64
MAX_PROVENANCE = 64
MAX_VALUE_BYTES = 8 * 1024
MAX_CLOCK_SKEW = timedelta(minutes=5)
MEMORY_TYPES = {
    "fact",
    "decision",
    "lesson",
    "failure-fingerprint",
    "capability-gap",
    "execution-result",
}
EVIDENCE_KINDS = {
    "user-correction",
    "reproducible-fact",
    "accepted-decision",
    "process-observation",
    "reproducible-failure",
    "verified-capability-gap",
    "accepted-execution-result",
    "external-claim",
    "model-inference",
    "weak-observation",
}
SENSITIVITIES = {"public", "metadata", "secret-free"}
SENSITIVE_FIELD_PREFIXES = {
    "accesskey",
    "accesstoken",
    "apikey",
    "authorization",
    "bilijct",
    "cookie",
    "credential",
    "dedeuserid",
    "environmentdump",
    "envdump",
    "githubpat",
    "githubtoken",
    "ghtoken",
    "npmtoken",
    "password",
    "privatekey",
    "rawcommand",
    "rawoutput",
    "rawstderr",
    "rawstdout",
    "refreshtoken",
    "secret",
    "sessdata",
    "sshkey",
    "stderr",
    "stdout",
    "token",
}
SENSITIVE_FIELD_SUFFIXES = {
    "content",
    "data",
    "dump",
    "field",
    "fields",
    "header",
    "headers",
    "material",
    "value",
    "values",
}
SUBJECT_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,127}")
TASK_RE = re.compile(r"[A-Za-z0-9_.:#-]{1,128}")
TIMESTAMP_RE = re.compile(
    r"(?:19|20)\d{2}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])"
    r"T(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\dZ"
)
FORBIDDEN_KEYS = {
    "accesskey",
    "accesstoken",
    "apikey",
    "args",
    "arguments",
    "argv",
    "auth",
    "authorization",
    "bilijct",
    "cmd",
    "command",
    "commands",
    "cookie",
    "cookies",
    "credential",
    "credentials",
    "dedeuserid",
    "dedeuseridckmd5",
    "env",
    "environment",
    "environmentdump",
    "environmentvariables",
    "envdump",
    "headers",
    "idtoken",
    "logs",
    "output",
    "rawoutput",
    "password",
    "program",
    "prompt",
    "rawcommand",
    "rawstderr",
    "rawstdout",
    "refreshtoken",
    "requestheaders",
    "responseheaders",
    "script",
    "secret",
    "secrets",
    "sessdata",
    "sessionid",
    "shell",
    "executable",
    "stderr",
    "stdout",
    "token",
    "tokens",
}
SECRET_TEXT = (
    re.compile(r"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----", re.IGNORECASE),
    re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bnpm_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bsk-(?:ant-)?[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{16,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
    re.compile(
        r"(?i)\b(?:BILIBILI_)?(?:SESSDATA|BILI_JCT|DEDEUSERID|DEDEUSERID__CKMD5)"
        r"[\"']?\s*[:=]\s*[\"']?\S+"
    ),
    re.compile(r"(?i)\bCookie\s*[:=]"),
    re.compile(r"(?i)\bBearer\s+\S+"),
    re.compile(r"(?i)\bBasic\s+[A-Za-z0-9+/=]{8,}\b"),
    re.compile(r"(?i)\b(?:password|passwd|token|credential|secret)\s*[:=]\s*\S+"),
    re.compile(r"(?m)^[A-Z_][A-Z0-9_]{1,63}=\S+"),
)
FORBIDDEN_TEXT = (
    *SECRET_TEXT,
    re.compile(
        r"(?i)^\s*(?:\$\s*)?(?:awk|bash|cargo|cat|cd|cmake|cmd|curl|docker|"
        r"dotnet|echo|env|export|find|git|gh|go|grep|helm|java|javac|kubectl|"
        r"ls|make|node|npm|npx|perl|php|pip|powershell|printenv|pytest|python(?:3)?|"
        r"pwd|pwsh|rg|rsync|ruby|scp|sed|set|sh|ssh|tar|tsc|unzip|uv|vitest|"
        r"wget|zip)\b(?:\s|$)"
    ),
    re.compile(r"^\s*[A-Z][A-Za-z]+-[A-Z][A-Za-z]+\b"),
    re.compile(r"(?:^|\s)(?:--?[A-Za-z][A-Za-z0-9-]*|[|&;<>]{1,2})(?:\s|$)"),
    re.compile(r"(?i)^\s*(?:command|stdout|stderr|environment)\s*:"),
    re.compile(r"(?i)^\s*[A-Za-z0-9_.-]+\.(?:bat|cmd|com|exe|ps1|sh)\b"),
    re.compile(
        r"(?i)^\s*(?:(?:[A-Za-z]:[\\/])|(?:\.\.?[\\/]))\S+\.(?:bat|cmd|com|exe|ps1|sh)\b"
    ),
)


class MemoryProjectionError(ValueError):
    """Raised when memory input or persistence crosses the governed boundary."""


def _canonical_bytes(value: Any) -> bytes:
    try:
        validate_json_shape(value, max_nodes=12_000, max_depth=12)
        return json.dumps(
            value,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise MemoryProjectionError(
            "memory JSON is invalid or exceeds structural limits"
        ) from exc


def _pretty_bytes(value: Any, limit: int) -> bytes:
    _canonical_bytes(value)
    encoded = (
        json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2, allow_nan=False)
        + "\n"
    ).encode("utf-8")
    if len(encoded) > limit:
        raise MemoryProjectionError("memory artifact exceeds its byte limit")
    return encoded


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _exact_keys(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise MemoryProjectionError(f"{label} must use the exact typed contract")
    return value


def _forbidden_key(key: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]", "", key.lower())
    return normalized in FORBIDDEN_KEYS


def _forbidden_subject(subject: str) -> bool:
    if "\n" in subject or "\r" in subject or any(ord(char) < 32 for char in subject):
        return True
    if _forbidden_key(subject):
        return True
    separated = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", "_", subject)
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", separated)
    normalized = re.sub(r"[^a-z0-9]", "", separated.lower())
    if any(
        normalized == prefix
        or normalized.removeprefix(prefix) in SENSITIVE_FIELD_SUFFIXES
        for prefix in SENSITIVE_FIELD_PREFIXES
        if normalized.startswith(prefix)
    ):
        return True
    return any(pattern.search(subject) for pattern in FORBIDDEN_TEXT) or any(
        _forbidden_key(part) for part in re.split(r"[^A-Za-z0-9]+", separated) if part
    )


def _validate_safe_value(value: Any, *, depth: int = 0) -> None:
    if depth > 8:
        raise MemoryProjectionError("memory value exceeds its depth limit")
    if (
        value is None
        or isinstance(value, bool)
        or (isinstance(value, int) and not isinstance(value, bool))
    ):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise MemoryProjectionError("memory value contains a non-finite number")
        return
    if isinstance(value, str):
        if len(value.encode("utf-8")) > MAX_VALUE_BYTES:
            raise MemoryProjectionError("memory value exceeds its byte limit")
        if "\n" in value or "\r" in value or any(ord(char) < 32 for char in value):
            raise MemoryProjectionError(
                "raw output or multiline text is not valid memory"
            )
        if any(pattern.search(value) for pattern in FORBIDDEN_TEXT):
            raise MemoryProjectionError(
                "secret-like or raw operational text is not valid memory"
            )
        return
    if isinstance(value, list):
        if len(value) > 64:
            raise MemoryProjectionError("memory value exceeds its item limit")
        for item in value:
            _validate_safe_value(item, depth=depth + 1)
        return
    if isinstance(value, dict):
        if len(value) > 64:
            raise MemoryProjectionError("memory value exceeds its field limit")
        for key, item in value.items():
            if (
                not isinstance(key, str)
                or not key
                or len(key) > 128
                or _forbidden_subject(key)
            ):
                raise MemoryProjectionError("memory value contains a forbidden field")
            _validate_safe_value(item, depth=depth + 1)
        return
    raise MemoryProjectionError("memory value must be bounded JSON")


def _validate_candidate(value: Any) -> dict[str, Any]:
    candidate = _exact_keys(
        value,
        {
            "type",
            "subject",
            "value",
            "evidence_kind",
            "evidence_digest",
            "sensitivity",
            "valid_from",
        },
        "memory candidate",
    )
    if candidate["type"] not in MEMORY_TYPES:
        raise MemoryProjectionError("memory candidate type is invalid")
    if (
        not isinstance(candidate["subject"], str)
        or not SUBJECT_RE.fullmatch(candidate["subject"])
        or _forbidden_subject(candidate["subject"])
    ):
        raise MemoryProjectionError("memory candidate subject is invalid")
    _validate_safe_value(candidate["subject"])
    if candidate["evidence_kind"] not in EVIDENCE_KINDS:
        raise MemoryProjectionError("memory evidence kind is invalid")
    if candidate["sensitivity"] not in SENSITIVITIES:
        raise MemoryProjectionError("memory sensitivity class is invalid")
    if not isinstance(candidate["evidence_digest"], str) or not re.fullmatch(
        r"[0-9a-f]{64}", candidate["evidence_digest"]
    ):
        raise MemoryProjectionError("memory evidence digest is invalid")
    if not isinstance(candidate["valid_from"], str) or not TIMESTAMP_RE.fullmatch(
        candidate["valid_from"]
    ):
        raise MemoryProjectionError("memory validity start is invalid")
    try:
        valid_from = datetime.strptime(
            candidate["valid_from"], "%Y-%m-%dT%H:%M:%SZ"
        ).replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise MemoryProjectionError("memory validity start is invalid") from exc
    if valid_from > datetime.now(timezone.utc) + MAX_CLOCK_SKEW:
        raise MemoryProjectionError("memory validity start is in the future")
    _validate_safe_value(candidate["value"])
    if len(_canonical_bytes(candidate["value"])) > MAX_VALUE_BYTES:
        raise MemoryProjectionError("memory value exceeds its byte limit")
    return copy.deepcopy(candidate)


def _validated_envelope(value: Any) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    envelope = _exact_keys(value, {"schema", "source", "candidates"}, "memory envelope")
    if envelope["schema"] != "harness.memory-evidence/v1":
        raise MemoryProjectionError("memory envelope schema is unsupported")
    source = _exact_keys(envelope["source"], {"task_id", "commit_sha"}, "memory source")
    if (
        not isinstance(source["task_id"], str)
        or not TASK_RE.fullmatch(source["task_id"])
        or _forbidden_subject(source["task_id"])
    ):
        raise MemoryProjectionError("memory source task identity is invalid")
    if not isinstance(source["commit_sha"], str) or not re.fullmatch(
        r"[0-9a-f]{40}", source["commit_sha"]
    ):
        raise MemoryProjectionError("memory source commit is invalid")
    candidates = envelope["candidates"]
    if not isinstance(candidates, list) or not 1 <= len(candidates) <= MAX_CANDIDATES:
        raise MemoryProjectionError("memory envelope candidate count is invalid")
    validated = [_validate_candidate(item) for item in candidates]
    evidence_digest = _memory_envelope_digest(source, validated)
    if any(item["evidence_digest"] != evidence_digest for item in validated):
        raise MemoryProjectionError(
            "memory evidence digest does not bind the canonical envelope content"
        )
    return copy.deepcopy(source), validated


def _memory_envelope_digest(
    source: dict[str, Any], candidates: list[dict[str, Any]]
) -> str:
    material = {
        "schema": "harness.memory-evidence-material/v1",
        "task_id": source["task_id"],
        "candidates": sorted(
            (
                {
                    key: copy.deepcopy(candidate[key])
                    for key in (
                        "type",
                        "subject",
                        "value",
                        "evidence_kind",
                        "sensitivity",
                        "valid_from",
                    )
                }
                for candidate in candidates
            ),
            key=_canonical_bytes,
        ),
    }
    return _digest(material)


def memory_envelope_digest(envelope: dict[str, Any]) -> str:
    """Return the semantic digest that an accepted check must record."""

    raw = _exact_keys(envelope, {"schema", "source", "candidates"}, "memory envelope")
    if raw["schema"] != "harness.memory-evidence/v1":
        raise MemoryProjectionError("memory envelope schema is unsupported")
    source = _exact_keys(raw["source"], {"task_id", "commit_sha"}, "memory source")
    if (
        not isinstance(source["task_id"], str)
        or not TASK_RE.fullmatch(source["task_id"])
        or _forbidden_subject(source["task_id"])
    ):
        raise MemoryProjectionError("memory source task identity is invalid")
    if not isinstance(source["commit_sha"], str) or not re.fullmatch(
        r"[0-9a-f]{40}", source["commit_sha"]
    ):
        raise MemoryProjectionError("memory source commit is invalid")
    candidates = raw["candidates"]
    if not isinstance(candidates, list) or not 1 <= len(candidates) <= MAX_CANDIDATES:
        raise MemoryProjectionError("memory envelope candidate count is invalid")
    material_candidates: list[dict[str, Any]] = []
    for candidate in candidates:
        material_candidates.append(_validate_candidate(candidate))
    return _memory_envelope_digest(source, material_candidates)


def _accepted_evidence(
    context: WorktreeContext, source: dict[str, Any]
) -> tuple[dict[str, Any], set[str]]:
    status = codex_direct_status(context, task_id=source["task_id"], expected_mode=None)
    accepted_diff = status.get("accepted_diff")
    lease = status.get("writer_lease")
    if (
        status.get("state") != "accepted"
        or status.get("commit_sha") != source["commit_sha"]
        or not isinstance(accepted_diff, dict)
        or not isinstance(accepted_diff.get("diff_digest"), str)
        or lease
        not in (
            {"holder": "codex", "state": "released"},
            {"holder": "claude", "state": "released"},
        )
    ):
        raise MemoryProjectionError("memory source is not an accepted committed task")
    diff_digest = accepted_diff["diff_digest"]
    checks = status.get("checks")
    if not isinstance(checks, dict):
        raise MemoryProjectionError("accepted memory evidence is unavailable")
    passing = {
        item["digest"]
        for item in checks.values()
        if isinstance(item, dict)
        and item.get("status") == "pass"
        and item.get("diff_digest") == diff_digest
        and isinstance(item.get("digest"), str)
        and re.fullmatch(r"[0-9a-f]{64}", item["digest"])
    }
    if not passing:
        raise MemoryProjectionError("accepted memory evidence is unavailable")
    return status, passing


def _acceptance_receipt(
    context: WorktreeContext,
    status: dict[str, Any],
    source: dict[str, Any],
    evidence_digest: str,
) -> dict[str, Any]:
    accepted = status["accepted_diff"]
    try:
        parents = _commit_parents(context.root, source["commit_sha"])
        paths = _commit_paths(context.root, source["commit_sha"])
        if not paths and not parents:
            paths = _git_paths(
                context.root,
                "ls-tree",
                "-r",
                "--name-only",
                "-z",
                source["commit_sha"],
            )
        snapshot = _commit_tree_snapshot(context.root, source["commit_sha"], paths)
    except CodexDirectError as exc:
        raise MemoryProjectionError("accepted memory receipt is unavailable") from exc
    if (
        len(parents) > 1
        or not paths
        or paths != sorted(set(paths))
        or not _valid_snapshot(snapshot, paths)
    ):
        raise MemoryProjectionError("accepted memory receipt is unavailable")
    material = {
        "schema": "harness.accepted-task-receipt/v1",
        "task_id": source["task_id"],
        "terminal_state": "accepted",
        "commit_sha": source["commit_sha"],
        "base_sha": parents[0] if parents else None,
        "diff_digest": accepted["diff_digest"],
        "paths": copy.deepcopy(paths),
        "index_snapshot": copy.deepcopy(snapshot),
        "index_digest": _snapshot_digest(snapshot),
        "evidence_digest": evidence_digest,
    }
    return {**material, "receipt_digest": _digest(material)}


def _empty_store() -> dict[str, Any]:
    return {"schema": "harness.typed-memory-store/v1", "records": []}


def _validate_store(store: Any) -> dict[str, Any]:
    _exact_keys(store, {"schema", "records"}, "typed memory store")
    if store.get("schema") != "harness.typed-memory-store/v1" or not isinstance(
        store.get("records"), list
    ):
        raise MemoryProjectionError("typed memory store is invalid")
    records = store["records"]
    if len(records) > MAX_RECORDS or any(
        not isinstance(item, dict) for item in records
    ):
        raise MemoryProjectionError("typed memory store exceeds its record limit")
    if len({item.get("record_id") for item in records}) != len(records):
        raise MemoryProjectionError("typed memory store contains duplicate records")
    for record in records:
        _validate_record(record)
    by_id = {item["record_id"]: item for item in records}
    for record in records:
        previous = record["supersedes"]
        following = record["superseded_by"]
        if previous is not None and (
            previous not in by_id
            or by_id[previous]["superseded_by"] != record["record_id"]
        ):
            raise MemoryProjectionError("typed memory supersession chain is invalid")
        if following is not None and (
            following not in by_id
            or by_id[following]["supersedes"] != record["record_id"]
            or record["validity"]["to"] != by_id[following]["validity"]["from"]
        ):
            raise MemoryProjectionError("typed memory supersession chain is invalid")
    expected = copy.deepcopy(records)
    _recompute_supersession(expected)
    expected_by_id = {item["record_id"]: item for item in expected}
    if any(
        (
            record["validity"]["to"],
            record["supersedes"],
            record["superseded_by"],
        )
        != (
            expected_by_id[record["record_id"]]["validity"]["to"],
            expected_by_id[record["record_id"]]["supersedes"],
            expected_by_id[record["record_id"]]["superseded_by"],
        )
        for record in records
    ):
        raise MemoryProjectionError("typed memory supersession chain is invalid")
    return copy.deepcopy(store)


def _load_store_bytes(raw: bytes) -> dict[str, Any]:
    try:
        parsed = json.loads(raw.decode("utf-8", errors="strict"))
        validate_json_shape(parsed, max_nodes=12_000, max_depth=12)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise MemoryProjectionError("typed memory store is invalid") from exc
    if not isinstance(parsed, dict):
        raise MemoryProjectionError("typed memory store is invalid")
    return _validate_store(parsed)


def _record_id(candidate: dict[str, Any]) -> str:
    valid_from = candidate.get("valid_from")
    if valid_from is None and isinstance(candidate.get("validity"), dict):
        valid_from = candidate["validity"].get("from")
    identity: dict[str, Any] = {
        "type": candidate["type"],
        "subject": candidate["subject"],
        "value": candidate["value"],
    }
    if candidate["type"] == "fact":
        identity["valid_from"] = valid_from
    return f"mem-{_digest(identity)}"


def _validate_record(record: Any) -> None:
    item = _exact_keys(
        record,
        {
            "record_id",
            "type",
            "subject",
            "value",
            "source",
            "provenance",
            "validation",
            "sensitivity",
            "validity",
            "supersedes",
            "superseded_by",
            "evidence_digest",
        },
        "typed memory record",
    )
    if (
        item["type"] not in MEMORY_TYPES
        or not isinstance(item["subject"], str)
        or not SUBJECT_RE.fullmatch(item["subject"])
        or _forbidden_subject(item["subject"])
        or item["source"] != "accepted-task"
        or item["validation"] not in {"accepted", "proposed", "deferred"}
        or item["sensitivity"] not in SENSITIVITIES
        or not isinstance(item["record_id"], str)
        or not re.fullmatch(r"mem-[0-9a-f]{64}", item["record_id"])
        or item["record_id"] != _record_id(item)
        or not isinstance(item["evidence_digest"], str)
        or not re.fullmatch(r"[0-9a-f]{64}", item["evidence_digest"])
    ):
        raise MemoryProjectionError("typed memory record is invalid")
    _validate_safe_value(item["subject"])
    _validate_safe_value(item["value"])
    provenance = item["provenance"]
    if not isinstance(provenance, list) or not 1 <= len(provenance) <= MAX_PROVENANCE:
        raise MemoryProjectionError("typed memory provenance is invalid")
    for source in provenance:
        provenance_keys = {
            "source",
            "task_id",
            "commit_sha",
            "evidence_digest",
            "evidence_kind",
            "sensitivity",
            "valid_from",
        }
        if item["type"] == "capability-gap":
            provenance_keys.add("acceptance_receipt")
        _exact_keys(
            source,
            provenance_keys,
            "typed memory provenance",
        )
        if (
            source["source"] != "accepted-task"
            or not isinstance(source["task_id"], str)
            or not TASK_RE.fullmatch(source["task_id"])
            or _forbidden_subject(source["task_id"])
            or not isinstance(source["commit_sha"], str)
            or not re.fullmatch(r"[0-9a-f]{40}", source["commit_sha"])
            or not isinstance(source["evidence_digest"], str)
            or not re.fullmatch(r"[0-9a-f]{64}", source["evidence_digest"])
            or source["evidence_kind"] not in EVIDENCE_KINDS
            or source["sensitivity"] not in SENSITIVITIES
            or not isinstance(source["valid_from"], str)
            or not TIMESTAMP_RE.fullmatch(source["valid_from"])
        ):
            raise MemoryProjectionError("typed memory provenance is invalid")
        try:
            datetime.strptime(source["valid_from"], "%Y-%m-%dT%H:%M:%SZ")
        except ValueError as exc:
            raise MemoryProjectionError("typed memory provenance is invalid") from exc
        if item["type"] == "capability-gap":
            receipt = _exact_keys(
                source["acceptance_receipt"],
                {
                    "schema",
                    "task_id",
                    "terminal_state",
                    "commit_sha",
                    "base_sha",
                    "diff_digest",
                    "paths",
                    "index_snapshot",
                    "index_digest",
                    "evidence_digest",
                    "receipt_digest",
                },
                "accepted task receipt",
            )
            material = {key: value for key, value in receipt.items() if key != "receipt_digest"}
            paths = receipt["paths"]
            if (
                receipt["schema"] != "harness.accepted-task-receipt/v1"
                or receipt["task_id"] != source["task_id"]
                or receipt["terminal_state"] != "accepted"
                or receipt["commit_sha"] != source["commit_sha"]
                or receipt["evidence_digest"] != source["evidence_digest"]
                or any(
                    not isinstance(receipt[key], str)
                    or not re.fullmatch(r"[0-9a-f]{64}", receipt[key])
                    for key in ("diff_digest", "index_digest", "receipt_digest")
                )
                or (
                    receipt["base_sha"] is not None
                    and (
                        not isinstance(receipt["base_sha"], str)
                        or not re.fullmatch(r"[0-9a-f]{40}", receipt["base_sha"])
                    )
                )
                or not isinstance(paths, list)
                or not paths
                or paths != sorted(set(paths))
                or any(not isinstance(path, str) for path in paths)
                or not _valid_snapshot(receipt["index_snapshot"], paths)
                or receipt["index_digest"]
                != _snapshot_digest(receipt["index_snapshot"])
                or receipt["receipt_digest"] != _digest(material)
            ):
                raise MemoryProjectionError("accepted task receipt is invalid")
    if len({_canonical_bytes(source) for source in provenance}) != len(provenance):
        raise MemoryProjectionError("typed memory provenance is duplicated")
    validity = _exact_keys(item["validity"], {"from", "to"}, "memory validity")
    if (
        not isinstance(validity["from"], str)
        or not TIMESTAMP_RE.fullmatch(validity["from"])
        or (
            validity["to"] is not None
            and (
                not isinstance(validity["to"], str)
                or not TIMESTAMP_RE.fullmatch(validity["to"])
                or validity["to"] < validity["from"]
            )
        )
    ):
        raise MemoryProjectionError("memory validity interval is invalid")
    try:
        datetime.strptime(validity["from"], "%Y-%m-%dT%H:%M:%SZ")
        if validity["to"] is not None:
            datetime.strptime(validity["to"], "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise MemoryProjectionError("memory validity interval is invalid") from exc
    for key in ("supersedes", "superseded_by"):
        if item[key] is not None and (
            not isinstance(item[key], str)
            or not re.fullmatch(r"mem-[0-9a-f]{64}", item[key])
        ):
            raise MemoryProjectionError("typed memory supersession link is invalid")
    if item["validation"] != _validation(item) or item[
        "evidence_digest"
    ] != _evidence_digest(provenance):
        raise MemoryProjectionError("typed memory validation evidence is invalid")
    sensitivity_order = {"public": 0, "metadata": 1, "secret-free": 2}
    if item["sensitivity"] != max(
        (source["sensitivity"] for source in provenance),
        key=sensitivity_order.__getitem__,
    ) or validity["from"] != min(source["valid_from"] for source in provenance):
        raise MemoryProjectionError("typed memory provenance summary is invalid")


def _provenance(
    context: WorktreeContext,
    source: dict[str, Any],
    candidate: dict[str, Any],
    status: dict[str, Any],
) -> dict[str, Any]:
    result = {
        "source": "accepted-task",
        "task_id": source["task_id"],
        "commit_sha": source["commit_sha"],
        "evidence_digest": candidate["evidence_digest"],
        "evidence_kind": candidate["evidence_kind"],
        "sensitivity": candidate["sensitivity"],
        "valid_from": candidate["valid_from"],
    }
    if candidate["type"] == "capability-gap":
        result["acceptance_receipt"] = _acceptance_receipt(
            context, status, source, candidate["evidence_digest"]
        )
    return result


def _validation(record: dict[str, Any]) -> str:
    provenance = record["provenance"]
    kinds = {item["evidence_kind"] for item in provenance}
    if "user-correction" in kinds:
        return "accepted"
    if record["type"] == "fact" and "reproducible-fact" in kinds:
        return "accepted"
    if record["type"] == "decision" and "accepted-decision" in kinds:
        return "accepted"
    if record["type"] == "failure-fingerprint" and "reproducible-failure" in kinds:
        return "accepted"
    if record["type"] == "capability-gap" and "verified-capability-gap" in kinds:
        return "accepted"
    if record["type"] == "execution-result" and "accepted-execution-result" in kinds:
        return "accepted"
    if record["type"] == "lesson" and "process-observation" in kinds:
        if (
            len(
                {
                    item["task_id"]
                    for item in provenance
                    if item["evidence_kind"] == "process-observation"
                }
            )
            >= 2
        ):
            return "accepted"
    if kinds == {"external-claim"}:
        return "deferred"
    return "proposed"


def _evidence_digest(provenance: list[dict[str, Any]]) -> str:
    digests = sorted({item["evidence_digest"] for item in provenance})
    return digests[0] if len(digests) == 1 else _digest(digests)


def _merge_candidate(
    context: WorktreeContext,
    records: list[dict[str, Any]],
    source: dict[str, Any],
    candidate: dict[str, Any],
    status: dict[str, Any],
) -> None:
    record_id = _record_id(candidate)
    record = next(
        (item for item in records if item.get("record_id") == record_id), None
    )
    provenance = _provenance(context, source, candidate, status)
    if record is None:
        if len(records) >= MAX_RECORDS:
            raise MemoryProjectionError("typed memory store is full")
        record = {
            "record_id": record_id,
            "type": candidate["type"],
            "subject": candidate["subject"],
            "value": copy.deepcopy(candidate["value"]),
            "source": "accepted-task",
            "provenance": [provenance],
            "validation": "proposed",
            "sensitivity": candidate["sensitivity"],
            "validity": {"from": candidate["valid_from"], "to": None},
            "supersedes": None,
            "superseded_by": None,
            "evidence_digest": candidate["evidence_digest"],
        }
        records.append(record)
    elif provenance not in record["provenance"]:
        if len(record["provenance"]) >= MAX_PROVENANCE:
            raise MemoryProjectionError("typed memory provenance exceeds its limit")
        record["provenance"].append(provenance)
        record["provenance"].sort(
            key=lambda item: (
                item["task_id"],
                item["commit_sha"],
                item["evidence_digest"],
                item["evidence_kind"],
            )
        )
    sensitivity_order = {"public": 0, "metadata": 1, "secret-free": 2}
    record["validity"]["from"] = min(
        item["valid_from"] for item in record["provenance"]
    )
    record["sensitivity"] = max(
        (item["sensitivity"] for item in record["provenance"]),
        key=sensitivity_order.__getitem__,
    )
    record["validation"] = _validation(record)
    record["evidence_digest"] = _evidence_digest(record["provenance"])


def _recompute_supersession(records: list[dict[str, Any]]) -> None:
    for record in records:
        record["supersedes"] = None
        record["superseded_by"] = None
        record["validity"]["to"] = None
    subjects = {
        record["subject"]
        for record in records
        if record["type"] == "fact" and record["validation"] == "accepted"
    }
    for subject in subjects:
        facts = sorted(
            (
                record
                for record in records
                if record["type"] == "fact"
                and record["validation"] == "accepted"
                and record["subject"] == subject
            ),
            key=lambda item: (item["validity"]["from"], item["record_id"]),
        )
        if len({item["validity"]["from"] for item in facts}) != len(facts):
            raise MemoryProjectionError(
                "accepted evidence contains ambiguous current facts"
            )
        for previous, current in zip(facts, facts[1:]):
            previous["superseded_by"] = current["record_id"]
            previous["validity"]["to"] = current["validity"]["from"]
            current["supersedes"] = previous["record_id"]


def _projection(records: list[dict[str, Any]], store_digest: str) -> dict[str, Any]:
    current = [
        copy.deepcopy(record)
        for record in records
        if record["validation"] == "accepted" and record["validity"]["to"] is None
    ]
    current.sort(
        key=lambda item: (item["validity"]["from"], item["record_id"]), reverse=True
    )
    projection: dict[str, Any] = {
        "schema": "harness.current-memory/v1",
        "limit": MAX_CURRENT_RECORDS,
        "store_digest": store_digest,
        "records": [],
    }
    for record in current[:MAX_CURRENT_RECORDS]:
        candidate = {**projection, "records": [*projection["records"], record]}
        try:
            _pretty_bytes(candidate, MAX_PROJECTION_BYTES)
        except MemoryProjectionError:
            break
        projection = candidate
    return projection


def _write_exact(root: Path, relative: Path, content: bytes, limit: int) -> None:
    if len(content) > limit:
        raise MemoryProjectionError("memory artifact exceeds its byte limit")
    path = root / relative
    ensure_no_link_components(root, path.parent)
    if path.is_symlink():
        raise MemoryProjectionError("memory artifact path cannot be a link")
    _ensure_directory_nofollow(path.parent)
    _atomic_write_bytes(path, content)
    if read_bounded_bytes(path, limit) != content:
        raise MemoryProjectionError("memory artifact persistence was not durable")


def _write_transaction_marker(path: Path, marker: dict[str, Any]) -> None:
    content = _pretty_bytes(marker, MAX_TRANSACTION_BYTES)
    _ensure_directory_nofollow(path.parent)
    if path.is_symlink():
        raise MemoryProjectionError("memory transaction marker is unsafe")
    _atomic_write_bytes(path, content)
    if read_bounded_json_object(path, MAX_TRANSACTION_BYTES) != marker:
        raise MemoryProjectionError("memory transaction marker was not durable")


def _clear_transaction_marker(path: Path) -> None:
    try:
        _unlink_nofollow(path, missing_ok=True)
    except OSError as exc:
        raise MemoryProjectionError(
            "memory transaction marker could not be cleared"
        ) from exc


def _artifact_bytes(path: Path, limit: int) -> bytes | None:
    content = read_bounded_bytes(path, limit)
    if content is None and (path.exists() or path.is_symlink()):
        raise MemoryProjectionError("memory artifact is unavailable or unsafe")
    return content


def _restore_artifact(
    root: Path, relative: Path, content: bytes | None, limit: int
) -> None:
    path = root / relative
    if content is None:
        try:
            _unlink_nofollow(path, missing_ok=True)
        except OSError as exc:
            raise MemoryProjectionError("memory artifact rollback failed") from exc
    elif read_bounded_bytes(path, limit) != content:
        _write_exact(root, relative, content, limit)


def _head_artifact_bytes(root: Path, relative: Path, limit: int) -> bytes | None:
    repository_path = relative.as_posix()
    try:
        paths = _git_paths(
            root,
            "ls-tree",
            "-r",
            "--name-only",
            "-z",
            "HEAD",
            "--",
            repository_path,
        )
        if repository_path not in paths:
            return None
        content = _git_bytes(root, "show", f"HEAD:{repository_path}")
    except CodexDirectError as exc:
        raise MemoryProjectionError(
            "trusted memory baseline is unavailable"
        ) from exc
    if len(content) > limit:
        raise MemoryProjectionError("trusted memory baseline exceeds its byte limit")
    return content


def _recover_memory_transaction(
    context: WorktreeContext,
    marker_path: Path,
    *,
    target_task_id: str,
    envelope_digest: str,
) -> None:
    if not marker_path.exists() and not marker_path.is_symlink():
        return
    marker = read_bounded_json_object(marker_path, MAX_TRANSACTION_BYTES)
    expected_keys = {
        "schema",
        "before_store_digest",
        "before_projection_digest",
        "target_task_digest",
        "envelope_digest",
        "before_store_exists",
        "before_projection_exists",
    }
    digest_keys = expected_keys - {
        "schema",
        "before_store_exists",
        "before_projection_exists",
    }
    if (
        set(marker) != expected_keys
        or marker.get("schema") != "harness.memory-transaction/v1"
        or any(
            not isinstance(marker.get(key), str)
            or not re.fullmatch(r"[0-9a-f]{64}", marker[key])
            for key in digest_keys
        )
        or not isinstance(marker.get("before_store_exists"), bool)
        or not isinstance(marker.get("before_projection_exists"), bool)
        or marker["before_store_exists"] != marker["before_projection_exists"]
    ):
        raise MemoryProjectionError("memory transaction marker is invalid")
    if (
        marker["target_task_digest"]
        != hashlib.sha256(target_task_id.encode("utf-8")).hexdigest()
        or marker["envelope_digest"] != envelope_digest
    ):
        raise MemoryProjectionError("memory transaction does not match this projection")

    store_path = context.root / STORE_PATH
    projection_path = context.root / PROJECTION_PATH
    store_bytes = _artifact_bytes(store_path, MAX_STORE_BYTES)
    projection_bytes = _artifact_bytes(projection_path, MAX_PROJECTION_BYTES)
    store_digest = hashlib.sha256(store_bytes or b"").hexdigest()
    projection_digest = hashlib.sha256(projection_bytes or b"").hexdigest()

    trusted_store = _head_artifact_bytes(
        context.root, STORE_PATH, MAX_STORE_BYTES
    )
    trusted_projection = _head_artifact_bytes(
        context.root, PROJECTION_PATH, MAX_PROJECTION_BYTES
    )
    if (
        (trusted_store is not None) != marker["before_store_exists"]
        or (trusted_projection is not None) != marker["before_projection_exists"]
        or hashlib.sha256(trusted_store or b"").hexdigest()
        != marker["before_store_digest"]
        or hashlib.sha256(trusted_projection or b"").hexdigest()
        != marker["before_projection_digest"]
    ):
        raise MemoryProjectionError("memory transaction requires manual recovery")
    if trusted_store is not None:
        trusted = _load_store_bytes(trusted_store)
        trusted_store_digest = hashlib.sha256(trusted_store).hexdigest()
        expected_projection = _pretty_bytes(
            _projection(trusted["records"], trusted_store_digest),
            MAX_PROJECTION_BYTES,
        )
        if trusted_projection != expected_projection:
            raise MemoryProjectionError("trusted memory baseline is inconsistent")
    if (
        store_digest == marker["before_store_digest"]
        and projection_digest == marker["before_projection_digest"]
        and (store_bytes is not None) == marker["before_store_exists"]
        and (projection_bytes is not None) == marker["before_projection_exists"]
    ):
        _clear_transaction_marker(marker_path)
        return
    _restore_artifact(context.root, STORE_PATH, trusted_store, MAX_STORE_BYTES)
    _restore_artifact(
        context.root, PROJECTION_PATH, trusted_projection, MAX_PROJECTION_BYTES
    )
    _clear_transaction_marker(marker_path)


def _validate_artifact_path(root: Path, relative: Path) -> Path:
    path = root / relative
    ensure_no_link_components(root, path.parent)
    is_junction = getattr(path, "is_junction", None)
    if path.is_symlink() or bool(is_junction and is_junction()):
        raise MemoryProjectionError("memory artifact path is unsafe")
    if path.exists():
        visible = path.stat(follow_symlinks=False)
        if not stat.S_ISREG(visible.st_mode) or visible.st_nlink != 1:
            raise MemoryProjectionError("memory artifact path is unsafe")
    return path


def _audit(
    context: WorktreeContext,
    *,
    source: dict[str, Any],
    target_task_id: str,
    envelope_digest: str,
    before_store: str,
    before_projection: str,
    after_store: str,
    after_projection: str,
    changed: bool,
    record_count: int,
    current_count: int,
) -> str:
    operation_id = _digest(
        {
            "envelope_digest": envelope_digest,
            "target_task_id": target_task_id,
            "before_store": before_store,
            "before_projection": before_projection,
            "after_store": after_store,
            "after_projection": after_projection,
        }
    )
    row = {
        "schema": "harness.memory-audit/v1",
        "operation_id": operation_id,
        "source_task_digest": hashlib.sha256(
            source["task_id"].encode("utf-8")
        ).hexdigest(),
        "target_task_digest": hashlib.sha256(
            target_task_id.encode("utf-8")
        ).hexdigest(),
        "source_commit_sha": source["commit_sha"],
        "envelope_digest": envelope_digest,
        "before_store_digest": before_store,
        "before_projection_digest": before_projection,
        "after_store_digest": after_store,
        "after_projection_digest": after_projection,
        "changed": changed,
        "status": "success",
        "record_count": record_count,
        "current_count": current_count,
    }
    audit_path = context.runtime_root / "memory" / "audit.jsonl"
    ensure_no_link_components(context.root, audit_path.parent)
    if audit_path.exists() and audit_path.stat().st_nlink != 1:
        raise MemoryProjectionError("memory audit path is unsafe")
    persisted = append_bounded_jsonl(audit_path, row, unique_field="operation_id")
    if persisted is False:
        raise MemoryProjectionError("memory audit persistence failed")
    return operation_id


@contextmanager
def _target_memory_writer(context: WorktreeContext, task_id: str):
    task_dir = _task_dir(context, task_id)
    ensure_no_link_components(context.root, task_dir)
    with bounded_file_lock(task_dir / "run.lock"):
        _, run = _load_run(context, task_id, expected_mode=None)
        contract = run["contract"]
        mode = contract["execution"]["mode"]
        writer = {"codex-direct": "codex", "claude-direct": "claude"}.get(mode)
        if (
            run["state"] not in {"executing", "repairing"}
            or writer is None
            or contract["writer_lease"] != {"holder": writer, "state": "active"}
            or sorted(contract["plan"]["owned_paths"])
            != sorted([STORE_PATH.as_posix(), PROJECTION_PATH.as_posix()])
        ):
            raise MemoryProjectionError(
                "memory target task lacks an active Codex writer or exact memory-only paths"
            )
        yield


def project_memory(
    context: WorktreeContext,
    envelope: dict[str, Any],
    *,
    target_task_id: str,
) -> dict[str, Any]:
    """Project one bounded accepted-evidence envelope into formal memory."""

    if (
        not isinstance(target_task_id, str)
        or not TASK_RE.fullmatch(target_task_id)
        or _forbidden_subject(target_task_id)
    ):
        raise MemoryProjectionError("memory target task identity is invalid")
    if len(_canonical_bytes(envelope)) > MAX_ENVELOPE_BYTES:
        raise MemoryProjectionError("memory envelope exceeds its byte limit")
    source, candidates = _validated_envelope(envelope)
    if source["task_id"] == target_task_id:
        raise MemoryProjectionError("memory source and target tasks must be distinct")
    status, passing = _accepted_evidence(context, source)
    if any(candidate["evidence_digest"] not in passing for candidate in candidates):
        raise MemoryProjectionError(
            "memory candidate does not cite passing accepted evidence"
        )

    store_path = _validate_artifact_path(context.root, STORE_PATH)
    projection_path = _validate_artifact_path(context.root, PROJECTION_PATH)
    lock_path = context.runtime_root / "memory" / "project.lock"
    marker_path = context.runtime_root / "memory" / "project-transaction.json"
    envelope_digest = _digest(envelope)
    with _target_memory_writer(context, target_task_id):
        with bounded_file_lock(lock_path):
            _recover_memory_transaction(
                context,
                marker_path,
                target_task_id=target_task_id,
                envelope_digest=envelope_digest,
            )
            before_store_bytes = _artifact_bytes(store_path, MAX_STORE_BYTES)
            before_projection_bytes = _artifact_bytes(
                projection_path, MAX_PROJECTION_BYTES
            )
            if (before_store_bytes is None) != (before_projection_bytes is None):
                raise MemoryProjectionError("memory artifact pair is incomplete")
            store = (
                _empty_store()
                if before_store_bytes is None
                else _load_store_bytes(before_store_bytes)
            )
            if before_store_bytes is not None:
                before_store_digest = hashlib.sha256(before_store_bytes).hexdigest()
                expected_before_projection = _pretty_bytes(
                    _projection(store["records"], before_store_digest),
                    MAX_PROJECTION_BYTES,
                )
                if before_projection_bytes != expected_before_projection:
                    raise MemoryProjectionError("memory artifact pair is inconsistent")
            records = store["records"]
            for candidate in candidates:
                _merge_candidate(context, records, source, candidate, status)
            _recompute_supersession(records)
            records.sort(key=lambda item: item["record_id"])
            store_bytes = _pretty_bytes(store, MAX_STORE_BYTES)
            store_digest = hashlib.sha256(store_bytes).hexdigest()
            projection = _projection(records, store_digest)
            projection_bytes = _pretty_bytes(projection, MAX_PROJECTION_BYTES)
            changed = (
                before_store_bytes != store_bytes
                or before_projection_bytes != projection_bytes
            )
            before_store_digest = hashlib.sha256(before_store_bytes or b"").hexdigest()
            before_projection_digest = hashlib.sha256(
                before_projection_bytes or b""
            ).hexdigest()
            if changed:
                marker = {
                    "schema": "harness.memory-transaction/v1",
                    "before_store_digest": before_store_digest,
                    "before_projection_digest": before_projection_digest,
                    "target_task_digest": hashlib.sha256(
                        target_task_id.encode("utf-8")
                    ).hexdigest(),
                    "envelope_digest": envelope_digest,
                    "before_store_exists": before_store_bytes is not None,
                    "before_projection_exists": before_projection_bytes is not None,
                }
                _write_transaction_marker(marker_path, marker)
                try:
                    if before_store_bytes != store_bytes:
                        _write_exact(
                            context.root, STORE_PATH, store_bytes, MAX_STORE_BYTES
                        )
                    if before_projection_bytes != projection_bytes:
                        _write_exact(
                            context.root,
                            PROJECTION_PATH,
                            projection_bytes,
                            MAX_PROJECTION_BYTES,
                        )
                except Exception:
                    try:
                        _restore_artifact(
                            context.root,
                            STORE_PATH,
                            before_store_bytes,
                            MAX_STORE_BYTES,
                        )
                        _restore_artifact(
                            context.root,
                            PROJECTION_PATH,
                            before_projection_bytes,
                            MAX_PROJECTION_BYTES,
                        )
                        _clear_transaction_marker(marker_path)
                    except Exception as rollback_error:
                        raise MemoryProjectionError(
                            "memory transaction rollback failed"
                        ) from rollback_error
                    raise
                _clear_transaction_marker(marker_path)
            projection_digest = hashlib.sha256(projection_bytes).hexdigest()
            operation_id = _audit(
                context,
                source=source,
                target_task_id=target_task_id,
                envelope_digest=envelope_digest,
                before_store=before_store_digest,
                before_projection=before_projection_digest,
                after_store=store_digest,
                after_projection=projection_digest,
                changed=changed,
                record_count=len(records),
                current_count=len(projection["records"]),
            )
    return {
        "schema": "harness.memory-projection-result/v1",
        "status": "success",
        "changed": changed,
        "operation_id": operation_id,
        "record_count": len(records),
        "current_count": len(projection["records"]),
        "store_digest": store_digest,
        "projection_digest": projection_digest,
    }


def startup_memory(context: WorktreeContext) -> dict[str, Any]:
    """Load only the bounded current projection used at session startup."""

    path = _validate_artifact_path(context.root, PROJECTION_PATH)
    store_path = _validate_artifact_path(context.root, STORE_PATH)
    status = _git_bytes(
        context.root,
        "status",
        "--porcelain=v1",
        "-z",
        "--",
        STORE_PATH.as_posix(),
        PROJECTION_PATH.as_posix(),
    )
    if status:
        raise MemoryProjectionError("current memory projection is not accepted in HEAD")
    tracked_raw = _git_bytes(
        context.root,
        "ls-files",
        "-z",
        "--",
        STORE_PATH.as_posix(),
        PROJECTION_PATH.as_posix(),
    )
    tracked = {item for item in tracked_raw.split(b"\0") if item}
    expected_tracked = {
        STORE_PATH.as_posix().encode("utf-8"),
        PROJECTION_PATH.as_posix().encode("utf-8"),
    }
    if not path.exists():
        if store_path.exists():
            raise MemoryProjectionError("current memory projection is missing")
        projection = {
            "schema": "harness.current-memory/v1",
            "limit": MAX_CURRENT_RECORDS,
            "store_digest": hashlib.sha256(
                _pretty_bytes(_empty_store(), MAX_STORE_BYTES)
            ).hexdigest(),
            "records": [],
        }
    else:
        if tracked != expected_tracked:
            raise MemoryProjectionError(
                "current memory artifacts are not tracked in HEAD"
            )
        projection_bytes = read_bounded_bytes(path, MAX_PROJECTION_BYTES)
        if projection_bytes is None:
            raise MemoryProjectionError("current memory projection is invalid")
        store_bytes = read_bounded_bytes(store_path, MAX_STORE_BYTES)
        try:
            if path.stat().st_nlink != 1 or store_path.stat().st_nlink != 1:
                raise MemoryProjectionError(
                    "current memory artifacts cannot be hard links"
                )
            projection = json.loads(projection_bytes.decode("utf-8", errors="strict"))
            validate_json_shape(
                projection, max_nodes=MAX_PROJECTION_NODES, max_depth=12
            )
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            raise MemoryProjectionError("current memory projection is invalid") from exc
        if (
            projection.get("schema") != "harness.current-memory/v1"
            or projection.get("limit") != MAX_CURRENT_RECORDS
            or not isinstance(projection.get("store_digest"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", projection["store_digest"])
            or not isinstance(projection.get("records"), list)
            or len(projection["records"]) > MAX_CURRENT_RECORDS
        ):
            raise MemoryProjectionError("current memory projection is invalid")
        if (
            store_bytes is None
            or hashlib.sha256(store_bytes).hexdigest() != projection["store_digest"]
        ):
            raise MemoryProjectionError(
                "current memory projection is not bound to its store"
            )
        store = _load_store_bytes(store_bytes)
        expected = _projection(store["records"], projection["store_digest"])
        if _pretty_bytes(expected, MAX_PROJECTION_BYTES) != projection_bytes:
            raise MemoryProjectionError(
                "current memory projection is not deterministic"
            )
        for record in projection["records"]:
            _validate_record(record)
            if (
                record["validation"] != "accepted"
                or record["validity"]["to"] is not None
            ):
                raise MemoryProjectionError("current memory projection is invalid")
        current_facts: set[str] = set()
        for record in projection["records"]:
            if record["type"] == "fact" and record["subject"] in current_facts:
                raise MemoryProjectionError(
                    "current memory projection has conflicting current facts"
                )
            if record["type"] == "fact":
                current_facts.add(record["subject"])
    return {
        "schema": "harness.memory-startup/v1",
        "projection_digest": hashlib.sha256(
            _pretty_bytes(projection, MAX_PROJECTION_BYTES)
        ).hexdigest(),
        "records": copy.deepcopy(projection["records"]),
    }


def _json_text(value: Any) -> str:
    return (
        json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2, allow_nan=False)
        + "\n"
    )


def compile_host_package(
    *,
    name: str,
    version: str,
    owner: str,
    host: str,
    source_label: str,
    source_digest: str,
    files: dict[str, str],
    max_files: int,
    max_bytes: int,
    extended_manifest: bool = False,
) -> dict[str, str]:
    """Add one deterministic manifest to bounded canonical host files."""

    if host not in {"codex", "claude"}:
        raise MemoryProjectionError("capability host is invalid")
    if (
        not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", name)
        or not re.fullmatch(r"\d+\.\d+\.\d+", version)
        or not isinstance(owner, str)
        or not owner
        or len(owner) > 128
        or not isinstance(source_label, str)
        or not source_label
        or len(source_label) > 128
        or not re.fullmatch(r"[0-9a-f]{64}", source_digest)
        or not isinstance(max_files, int)
        or not 1 <= max_files <= 64
        or not isinstance(max_bytes, int)
        or not 1024 <= max_bytes <= 1024 * 1024
        or not isinstance(files, dict)
        or not files
        or "manifest.json" in files
        or not isinstance(extended_manifest, bool)
    ):
        raise MemoryProjectionError("capability package metadata is invalid")
    package: dict[str, str] = {}
    for raw_path, content in sorted(files.items()):
        path = PurePosixPath(raw_path)
        if (
            not isinstance(raw_path, str)
            or not raw_path
            or path.is_absolute()
            or any(part in {"", ".", ".."} for part in path.parts)
            or not isinstance(content, str)
        ):
            raise MemoryProjectionError("capability package file is invalid")
        package[path.as_posix()] = content
    if len(package) + 1 > max_files:
        raise MemoryProjectionError(
            "capability package file count exceeds its manifest"
        )
    manifest: dict[str, Any] = {
        "schema": "harness.capability-manifest/v1",
        "name": name,
        "version": version,
        "owner": owner,
        "host": host,
        "source": source_label,
        "source_digest": source_digest,
        "files": {
            path: hashlib.sha256(content.encode("utf-8")).hexdigest()
            for path, content in package.items()
        },
    }
    if extended_manifest:
        manifest.update(
            {
                "canonical_digest": source_digest,
                "total_bytes": sum(
                    len(content.encode("utf-8")) for content in package.values()
                ),
            }
        )
    package["manifest.json"] = _json_text(manifest)
    total_bytes = sum(len(content.encode("utf-8")) for content in package.values())
    if total_bytes > max_bytes:
        raise MemoryProjectionError("capability package bytes exceed its manifest")
    return package


def compile_memory_capability(host: str) -> dict[str, str]:
    """Compile one thin host package from the canonical memory capability."""

    if host not in {"codex", "claude"}:
        raise MemoryProjectionError("memory capability host is invalid")
    source = read_bounded_json_object(
        CAPABILITY_SOURCE_PATH, 64 * 1024, max_nodes=2_000, max_depth=10
    )
    _exact_keys(
        source,
        {
            "schema",
            "name",
            "version",
            "owner",
            "description",
            "skill_body",
            "interface",
            "evaluation",
        },
        "memory capability source",
    )
    if (
        source["schema"] != "harness.memory-capability-source/v1"
        or source["name"] != "bilibili-mcp-memory"
        or not re.fullmatch(r"\d+\.\d+\.\d+", str(source["version"]))
        or not isinstance(source["description"], str)
        or not isinstance(source["skill_body"], list)
        or not source["skill_body"]
        or any(not isinstance(item, str) or not item for item in source["skill_body"])
    ):
        raise MemoryProjectionError("memory capability source is invalid")
    interface = copy.deepcopy(source["interface"])
    evaluation = copy.deepcopy(source["evaluation"])
    if (
        not isinstance(interface, dict)
        or interface.get("schema") != "harness.capability-interface/v1"
        or interface.get("name") != source["name"]
        or interface.get("version") != source["version"]
        or not isinstance(evaluation, dict)
        or evaluation.get("schema") != "harness.capability-evaluation/v1"
        or evaluation.get("name") != source["name"]
        or evaluation.get("interface_version") != source["version"]
    ):
        raise MemoryProjectionError("memory capability metadata is inconsistent")
    skill = "\n".join(
        [
            "---",
            f"name: {source['name']}",
            f"description: {source['description']}",
            "---",
            "",
            "# Bilibili MCP typed memory router",
            "",
            f"Host package: {host}",
            f"Interface version: {source['version']}",
            "",
            *(f"- {line}" for line in source["skill_body"]),
            "",
        ]
    )
    return compile_host_package(
        name=source["name"],
        version=source["version"],
        owner=source["owner"],
        host=host,
        source_label="canonical.json",
        source_digest=_digest(source),
        files={
            "SKILL.md": skill,
            "interface.json": _json_text(interface),
            "evaluation.json": _json_text(evaluation),
        },
        max_files=4,
        max_bytes=64 * 1024,
    )
