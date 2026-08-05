#!/usr/bin/env python3
"""Record bounded failure metadata without persisting tool text or output."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any

from hook_safety import (
    append_bounded_jsonl,
    find_key,
    read_bounded_jsonl,
    read_bounded_stdin_object,
    safe_tool_class,
)


ROOT = Path(__file__).resolve().parents[2]


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, str) and len(value) <= 16:
        try:
            return int(value)
        except ValueError:
            pass
    return None


def category_for(command: Any) -> str:
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


def agent_base(agent: str) -> Path:
    if agent == "codex":
        return Path.home() / ".codex" / "memories" / "bilibili-mcp"
    return ROOT / ".claude"


def evidence_count(path: Path, candidate_id: str) -> int:
    return 1 + sum(
        1
        for row in read_bounded_jsonl(path)
        if row.get("candidate_id") == candidate_id
    )


def confidence_for(category: str, count: int) -> float:
    base = {
        "build": 0.65,
        "test": 0.65,
        "lint": 0.6,
        "package": 0.7,
        "git": 0.55,
    }.get(category, 0.4)
    return min(0.9, round(base + max(0, count - 1) * 0.05, 2))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", choices=["codex", "claude"], default="codex")
    args = parser.parse_args()

    try:
        payload = read_bounded_stdin_object()
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        print(json.dumps({"suppressOutput": True}))
        return 0

    tool = safe_tool_class(
        find_key(payload, {"tool_name", "tool", "name"})
    )
    exit_code = as_int(
        find_key(
            payload,
            {"exit_code", "exitCode", "returncode", "return_code"},
        )
    )
    stderr_present = bool(find_key(payload, {"stderr", "errorOutput"}))
    error_present = bool(find_key(payload, {"error", "message"}))
    status = find_key(payload, {"status", "outcome"})
    failed = (
        (exit_code is not None and exit_code != 0)
        or stderr_present
        or error_present
        or (
            isinstance(status, str)
            and status.lower() in {"failed", "error"}
        )
    )
    if not failed:
        print(json.dumps({"suppressOutput": True}))
        return 0

    category = category_for(find_key(payload, {"command", "cmd"}))
    row = {
        "ts": now_iso(),
        "agent": args.agent,
        "tool": tool,
        "category": category,
        "exit_code": exit_code,
        "has_stderr": stderr_present,
        "has_error": error_present,
    }
    memory_root = agent_base(args.agent) / "memory"
    append_bounded_jsonl(memory_root / "observations.jsonl", row)

    if category in {"build", "test", "lint", "package", "git"}:
        candidate_id = hashlib.sha256(
            f"v2\n{category}\n{tool}\n{exit_code}".encode("utf-8")
        ).hexdigest()[:12]
        count = evidence_count(
            memory_root / "candidates.jsonl",
            candidate_id,
        )
        confidence = confidence_for(category, count)
        candidate = {
            **row,
            "candidate_id": candidate_id,
            "scope": "project",
            "evidence_count": count,
            "confidence": confidence,
            "promotion_status": "candidate",
            "promote_after_review": count >= 2 and confidence >= 0.7,
        }
        append_bounded_jsonl(memory_root / "candidates.jsonl", candidate)

    print(json.dumps({"suppressOutput": True}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
