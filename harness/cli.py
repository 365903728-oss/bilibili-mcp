#!/usr/bin/env python3
"""Shared CLI seam for Harness diagnostics, contracts, and hook projections."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from harness.capabilities import check_manual_skill, doctor_report
from harness.context import WorktreeError, discover_worktree
from harness.contracts import ContractError, validate_task_contract
from harness.events import ADAPTERS, HOOK_EVENTS, normalize_hook_event, persist_hook_event
from harness.safe_io import read_bounded_json_stream


def _print_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")))


def _load_json_file(path: Path, max_bytes: int = 256 * 1024) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink() or path.stat().st_size > max_bytes:
        raise ValueError("JSON file is unavailable, unsafe, or oversized")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("JSON file is invalid") from exc
    if not isinstance(value, dict):
        raise ValueError("JSON file must contain an object")
    return value


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="harness", description="bilibili-mcp Harness v2 CLI")
    subcommands = parser.add_subparsers(dest="command", required=True)

    doctor = subcommands.add_parser("doctor", help="report adapter and capability discovery")
    doctor.add_argument("--repo", type=Path, default=Path.cwd())
    doctor.add_argument("--json", action="store_true", help="reserved; output is always JSON")

    contract = subcommands.add_parser("contract", help="validate a typed task contract")
    contract_sub = contract.add_subparsers(dest="contract_command", required=True)
    validate = contract_sub.add_parser("validate")
    validate.add_argument("path", type=Path)

    hook = subcommands.add_parser("hook", help="normalize host hook payloads")
    hook_sub = hook.add_subparsers(dest="hook_command", required=True)
    for name in ("ingest", "replay"):
        action = hook_sub.add_parser(name)
        action.add_argument("--adapter", choices=ADAPTERS, required=True)
        action.add_argument("--event", choices=HOOK_EVENTS, required=True)
        action.add_argument("--cwd", type=Path, default=Path.cwd())
        action.add_argument("--session-id")
        if name == "replay":
            action.add_argument("--payload", type=Path, required=True)

    manual = subcommands.add_parser("manual-skill", help="enforce native manual-skill boundary")
    manual_sub = manual.add_subparsers(dest="manual_command", required=True)
    check = manual_sub.add_parser("check")
    check.add_argument("--cwd", type=Path, default=Path.cwd())
    check.add_argument("--task", required=True)
    check.add_argument("--adapter", required=True)
    check.add_argument("--host", choices=("codex", "claude"))
    check.add_argument("--skill", required=True)
    check.add_argument("--invoked", action="store_true")
    return parser


def _hook_control(*, recorded: bool, reason: str | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema": "harness.hook-control/v1",
        "recorded": recorded,
        "suppressOutput": True,
    }
    if reason:
        result["reason"] = reason
    return result


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.command == "doctor":
            context = discover_worktree(args.repo)
            report = doctor_report(
                context.root,
                common_git_dir=context.common_git_dir,
            )
            report["context"] = {
                "repository_id": context.repository_id,
                "worktree_id": context.worktree_id,
                "repository_root": str(context.root),
                "head_sha": context.head_sha,
            }
            _print_json(report)
            return 0

        if args.command == "contract":
            contract = validate_task_contract(_load_json_file(args.path))
            _print_json({"schema": "harness.contract-validation/v1", "valid": True, "task_id": contract["task"]["id"]})
            return 0

        if args.command == "hook":
            if args.hook_command == "replay":
                payload = _load_json_file(args.payload)
                _print_json(normalize_hook_event(args.adapter, args.event, payload))
                return 0

            try:
                payload = read_bounded_json_stream(sys.stdin.buffer)
            except ValueError:
                _print_json(_hook_control(recorded=False, reason="invalid-or-oversized-payload"))
                return 0
            try:
                context = discover_worktree(args.cwd)
                if args.session_id:
                    payload = {**payload, "session_id": args.session_id}
                event = normalize_hook_event(args.adapter, args.event, payload)
                persist_hook_event(context, event)
            except (ValueError, WorktreeError, OSError):
                _print_json(_hook_control(recorded=False, reason="context-or-persistence-rejected"))
                return 0
            _print_json(_hook_control(recorded=True))
            return 0

        if args.command == "manual-skill":
            context = discover_worktree(args.cwd)
            result = check_manual_skill(
                runtime_root=context.runtime_root,
                task_id=args.task,
                adapter=args.adapter,
                host=args.host,
                skill=args.skill,
                invoked=args.invoked,
                worktree_root=context.root,
            )
            _print_json(result)
            return 0 if result["status"] == "invoked" else 3
    except (ContractError, ValueError, WorktreeError, OSError) as exc:
        _print_json({"schema": "harness.error/v1", "error": str(exc)})
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
