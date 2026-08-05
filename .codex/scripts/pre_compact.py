#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import subprocess
from pathlib import Path
from typing import Any

from plan_tracker import resolve_active_work
from hook_safety import read_bounded_stdin_object, write_bounded_text

ROOT = Path(__file__).resolve().parents[2]


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def agent_base(agent: str) -> Path:
    if agent == "codex":
        return Path.home() / ".codex" / "memories" / "bilibili-mcp"
    return ROOT / ".claude"


def git_status_count() -> int:
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(ROOT),
                "status",
                "--short",
                "--untracked-files=no",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception as exc:
        return 0
    return min(10_000, len([line for line in result.stdout.splitlines() if line]))


def read_payload() -> dict[str, Any]:
    try:
        return read_bounded_stdin_object()
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return {}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", choices=["codex", "claude"], default="codex")
    args = parser.parse_args()

    base = agent_base(args.agent)
    runtime = base / "runtime"
    runtime.mkdir(parents=True, exist_ok=True)

    read_payload()
    dirty_count = git_status_count()
    active_work = resolve_active_work()

    lines = [
        f"# {args.agent} pre-compact checkpoint",
        f"Generated: {now_iso()}",
        "Repository: current bilibili-mcp worktree",
        "",
        "## Current Goal",
        "PreCompact triggered.",
        "",
        "## Git Status",
        f"Tracked changed paths: {dirty_count}",
        "",
        "## Active Work",
        active_work.name,
        "",
        "## Resume Guidance",
        "- Re-read AGENTS.md, CLAUDE.md, and docs/agent-memory before substantial work.",
        "- Treat runtime observations as candidates only; promote durable lessons manually.",
        "- If debugging was in progress, inspect latest observation-summary.md before continuing.",
    ]

    output = "\n".join(lines) + "\n"
    write_bounded_text(
        runtime / "pre-compact-checkpoint.md",
        output,
        64 * 1024,
    )
    print(json.dumps({"suppressOutput": True}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
