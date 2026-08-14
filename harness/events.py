"""Host-specific hook payloads projected into a shared redacted event."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from harness.context import WorktreeContext
from harness.safe_io import (
    append_bounded_jsonl,
    ensure_no_link_components,
    find_key,
    safe_tool_class,
)


ADAPTERS = ("codex", "claude")
HOOK_EVENTS = (
    "session-start",
    "post-tool-use",
    "post-tool-use-failure",
    "pre-compact",
    "stop",
)
OPAQUE_SESSION_RE = re.compile(r"^session-[0-9a-f]{20}$")
CLAUDE_FAILURE_EXIT_RE = re.compile(r"^Exit code\s+(-?\d+)(?:\r?\n|$)")


def _opaque_session_id(value: Any) -> str:
    raw = value if isinstance(value, str) and value else "missing"
    digest = hashlib.sha256(f"harness-session-v1\0{raw}".encode("utf-8")).hexdigest()
    return f"session-{digest[:20]}"


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return max(-32768, min(32767, value))
    if isinstance(value, str) and len(value) <= 8:
        try:
            return max(-32768, min(32767, int(value)))
        except ValueError:
            return None
    return None


def _category(command: Any) -> str:
    if not isinstance(command, str):
        return "shell"
    lower = command[:4096].lower()
    if "npm run build" in lower or "tsc" in lower:
        return "build"
    if "npm test" in lower or "vitest" in lower or " test" in lower:
        return "test"
    if "lint" in lower:
        return "lint"
    if "npm pack" in lower or "npm publish" in lower:
        return "package"
    if lower.startswith("git ") or " git " in lower:
        return "git"
    return "shell"


def _timestamp(payload: dict[str, Any]) -> str:
    raw = find_key(payload, {"event_timestamp", "timestamp"})
    if isinstance(raw, str) and len(raw) <= 40:
        candidate = raw.replace("Z", "+00:00")
        try:
            parsed = dt.datetime.fromisoformat(candidate)
            if parsed.tzinfo is not None:
                return (
                    parsed.astimezone(dt.timezone.utc)
                    .isoformat(timespec="seconds")
                    .replace("+00:00", "Z")
                )
        except ValueError:
            pass
    return (
        dt.datetime.now(dt.timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def _tool_outcome(
    adapter: str,
    event: str,
    payload: dict[str, Any],
) -> tuple[str, int | None, bool, bool]:
    """Return canonical event, exit code, error marker, and failure state.

    Claude separates successful and failed tool completions into distinct Hook
    events. Codex reports both through PostToolUse. Keep that host distinction at
    the adapter edge and project both payloads into one semantic event.
    """

    if event == "post-tool-use-failure":
        error = payload.get("error")
        match = CLAUDE_FAILURE_EXIT_RE.match(error) if isinstance(error, str) else None
        exit_code = _as_int(match.group(1)) if match else None
        return "post-tool-use", exit_code, True, True

    if event != "post-tool-use":
        return event, None, False, False

    if adapter == "claude":
        # Claude documents PostToolUse as success-only. A normal response may
        # legitimately contain fields such as `message` or `stderr`.
        return event, None, False, False

    response = payload.get("tool_response")
    if not isinstance(response, dict):
        response = {}
    exit_code = _as_int(
        find_key(response, {"exit_code", "exitCode", "returncode", "return_code"})
    )
    explicit_error = find_key(response, {"error", "errorOutput"})
    raw_status = response.get("status", response.get("outcome"))
    failed = (
        (exit_code is not None and exit_code != 0)
        or bool(explicit_error)
        or (isinstance(raw_status, str) and raw_status.lower() in {"failed", "error"})
    )
    return event, exit_code, failed, failed


def normalize_hook_event(
    adapter: str, event: str, payload: dict[str, Any]
) -> dict[str, Any]:
    if adapter not in ADAPTERS:
        raise ValueError("unsupported hook adapter")
    if event not in HOOK_EVENTS:
        raise ValueError("unsupported hook event")
    if not isinstance(payload, dict):
        raise ValueError("hook payload must be an object")

    tool = safe_tool_class(find_key(payload, {"tool_name", "tool", "name"}))
    canonical_event, exit_code, has_error, failed = _tool_outcome(
        adapter, event, payload
    )
    semantic = {
        "event": canonical_event,
        "tool_class": tool,
        "category": (
            _category(find_key(payload, {"command", "cmd"}))
            if tool == "shell"
            else "shell"
        ),
        "outcome": "failed" if failed else "succeeded",
        "exit_code": exit_code,
        "has_error": has_error,
    }
    session_id = _opaque_session_id(find_key(payload, {"session_id", "sessionId"}))
    provenance = {"adapter": adapter, "host_event": event}
    sensitivity = "metadata"
    terminal_state = "stopped" if canonical_event == "stop" else "active"
    digest_source = json.dumps(
        {
            "session_id": session_id,
            "provenance": provenance,
            "sensitivity": sensitivity,
            "terminal_state": terminal_state,
            "semantic": semantic,
        },
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(digest_source.encode("utf-8")).hexdigest()
    return {
        "schema": "harness.hook-event/v1",
        "timestamp": _timestamp(payload),
        "source_adapter": adapter,
        "provenance": provenance,
        "sensitivity": sensitivity,
        "digest": digest,
        "terminal_state": terminal_state,
        "session_id": session_id,
        "event_id": digest[:20],
        "semantic": semantic,
    }


def persist_hook_event(
    context: WorktreeContext,
    event: dict[str, Any],
) -> Path:
    session_id = event.get("session_id")
    if not isinstance(session_id, str) or not OPAQUE_SESSION_RE.fullmatch(session_id):
        raise ValueError("hook event contains an invalid opaque session id")
    ledger = context.runtime_root / session_id / "events.jsonl"
    ensure_no_link_components(context.root, ledger.parent)
    stored = {
        **event,
        "repository_id": context.repository_id,
        "worktree_id": context.worktree_id,
        "head_sha": context.head_sha,
    }
    if not append_bounded_jsonl(ledger, stored):
        raise ValueError("hook ledger is locked or unsafe")
    return ledger
