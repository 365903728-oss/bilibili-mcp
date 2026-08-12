#!/usr/bin/env python3
"""Shared CLI seam for Harness diagnostics, contracts, and hook projections."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Sequence

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from harness.capabilities import check_manual_skill, doctor_report
from harness.codex_direct import (
    GUARDED_ACTIONS,
    CodexDirectAdapterError,
    CodexDirectError,
    accept_codex_direct,
    advance_codex_direct,
    begin_repair,
    codex_direct_status,
    commit_codex_direct,
    enter_recovery,
    guard_codex_direct,
    judge_criterion,
    record_check,
    record_risk,
    start_direct,
)
from harness.context import WorktreeError, discover_worktree
from harness.contracts import ContractError, validate_task_contract
from harness.events import ADAPTERS, HOOK_EVENTS, normalize_hook_event, persist_hook_event
from harness.safe_io import read_bounded_bytes, read_bounded_json_stream


def _print_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")))


def _load_json_file(path: Path, max_bytes: int = 256 * 1024) -> dict[str, Any]:
    raw = read_bounded_bytes(path, max_bytes)
    if raw is None:
        raise ValueError("JSON file is unavailable, unsafe, or oversized")
    try:
        value = json.loads(raw.decode("utf-8", errors="strict"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("JSON file is invalid") from exc
    if not isinstance(value, dict):
        raise ValueError("JSON file must contain an object")
    return value


def _add_direct_parser(
    subcommands: argparse._SubParsersAction[argparse.ArgumentParser],
    name: str,
    label: str,
) -> None:
    direct = subcommands.add_parser(
        name, help=f"run the {label} accepted-ticket loop"
    )
    actions = direct.add_subparsers(dest="direct_command", required=True)
    start = actions.add_parser("start")
    start.add_argument("path", type=Path)
    start.add_argument("--cwd", type=Path, default=Path.cwd())
    guard = actions.add_parser("guard")
    guard.add_argument("--cwd", type=Path, default=Path.cwd())
    guard.add_argument("--task", required=True)
    guard.add_argument("--action", choices=sorted(GUARDED_ACTIONS), required=True)
    guard.add_argument("--path")
    advance = actions.add_parser("advance")
    advance.add_argument("--cwd", type=Path, default=Path.cwd())
    advance.add_argument("--task", required=True)
    advance.add_argument("--to", choices=("verifying", "reviewing"), required=True)
    evidence = actions.add_parser("record-check")
    evidence.add_argument("--cwd", type=Path, default=Path.cwd())
    evidence.add_argument("--task", required=True)
    evidence.add_argument("--check", required=True)
    evidence.add_argument("--status", choices=("pass", "fail", "skipped"), required=True)
    evidence.add_argument("--source", choices=("command", "inspection", "review"), required=True)
    evidence.add_argument("--exit-code", type=int)
    evidence.add_argument(
        "--sensitivity", choices=("public", "metadata", "secret-free"), required=True
    )
    evidence.add_argument("--digest", required=True)
    evidence.add_argument("--reason-code")
    judge = actions.add_parser("judge")
    judge.add_argument("--cwd", type=Path, default=Path.cwd())
    judge.add_argument("--task", required=True)
    judge.add_argument("--criterion", required=True)
    judge.add_argument("--status", choices=("pass", "fail"), required=True)
    judge.add_argument("--evidence-digest", required=True)
    risk = actions.add_parser("risk")
    risk.add_argument("--cwd", type=Path, default=Path.cwd())
    risk.add_argument("--task", required=True)
    risk.add_argument("--risk", required=True)
    risk.add_argument("--severity", choices=("low", "medium", "high", "critical"), required=True)
    risk.add_argument("--status", choices=("open", "accepted", "resolved"), required=True)
    risk.add_argument("--digest", required=True)
    accept = actions.add_parser("accept")
    accept.add_argument("--cwd", type=Path, default=Path.cwd())
    accept.add_argument("--task", required=True)
    accept.add_argument("--message", default="chore(harness): create accepted ticket commit")
    repair = actions.add_parser("repair")
    repair.add_argument("--cwd", type=Path, default=Path.cwd())
    repair.add_argument("--task", required=True)
    repair.add_argument("--fingerprint", required=True)
    recover = actions.add_parser("recover")
    recover.add_argument("--cwd", type=Path, default=Path.cwd())
    recover.add_argument("--task", required=True)
    recover.add_argument("--category", choices=("adapter-failure",), required=True)
    recover.add_argument("--fingerprint", required=True)
    commit = actions.add_parser("commit")
    commit.add_argument("--cwd", type=Path, default=Path.cwd())
    commit.add_argument("--task", required=True)
    commit.add_argument("--message", required=True)
    status = actions.add_parser("status")
    status.add_argument("--cwd", type=Path, default=Path.cwd())
    status.add_argument("--task", required=True)


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

    _add_direct_parser(subcommands, "codex-direct", "Codex Direct")
    _add_direct_parser(subcommands, "claude-direct", "Claude Direct")
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
    context = None
    recovery_task_id = None
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

        if args.command in {"codex-direct", "claude-direct"}:
            context = discover_worktree(args.cwd)
            if args.direct_command == "start":
                contract_value = _load_json_file(args.path)
                candidate_task_id = contract_value.get("task", {}).get("id")
                if isinstance(candidate_task_id, str):
                    recovery_task_id = candidate_task_id
                result, exit_code = start_direct(
                    context,
                    contract_value,
                    mode=args.command,
                )
            elif args.direct_command == "guard":
                result, exit_code = guard_codex_direct(
                    context,
                    task_id=args.task,
                    action=args.action,
                    path=args.path,
                    expected_mode=args.command,
                )
            elif args.direct_command == "advance":
                result = advance_codex_direct(
                    context,
                    task_id=args.task,
                    target=args.to,
                    expected_mode=args.command,
                )
                exit_code = 0
            elif args.direct_command == "record-check":
                result = record_check(
                    context,
                    task_id=args.task,
                    check_id=args.check,
                    status=args.status,
                    source=args.source,
                    exit_code=args.exit_code,
                    sensitivity=args.sensitivity,
                    digest=args.digest,
                    reason_code=args.reason_code,
                    expected_mode=args.command,
                )
                exit_code = 0
            elif args.direct_command == "judge":
                result = judge_criterion(
                    context,
                    task_id=args.task,
                    criterion_id=args.criterion,
                    status=args.status,
                    evidence_digest=args.evidence_digest,
                    expected_mode=args.command,
                )
                exit_code = 0
            elif args.direct_command == "risk":
                result = record_risk(
                    context,
                    task_id=args.task,
                    risk_id=args.risk,
                    severity=args.severity,
                    status=args.status,
                    digest=args.digest,
                    expected_mode=args.command,
                )
                exit_code = 0
            elif args.direct_command == "accept":
                result = accept_codex_direct(
                    context,
                    task_id=args.task,
                    message=args.message,
                    expected_mode=args.command,
                )
                exit_code = 0
            elif args.direct_command == "repair":
                result, exit_code = begin_repair(
                    context,
                    task_id=args.task,
                    fingerprint=args.fingerprint,
                    expected_mode=args.command,
                )
            elif args.direct_command == "recover":
                result, exit_code = enter_recovery(
                    context,
                    task_id=args.task,
                    category=args.category,
                    fingerprint=args.fingerprint,
                    expected_mode=args.command,
                )
            elif args.direct_command == "commit":
                result = commit_codex_direct(
                    context,
                    task_id=args.task,
                    message=args.message,
                    expected_mode=args.command,
                )
                exit_code = 0
            else:
                result = codex_direct_status(
                    context,
                    task_id=args.task,
                    expected_mode=args.command,
                )
                exit_code = 0
            _print_json(result)
            return exit_code
    except CodexDirectAdapterError as exc:
        task_id = getattr(args, "task", None) or recovery_task_id
        if args.command in {"codex-direct", "claude-direct"} and isinstance(task_id, str):
            fingerprint = hashlib.sha256(
                f"adapter-failure-v1\0{exc}".encode("utf-8")
            ).hexdigest()
            try:
                result, exit_code = enter_recovery(
                    context or discover_worktree(args.cwd),
                    task_id=task_id,
                    category="adapter-failure",
                    fingerprint=fingerprint,
                    expected_mode=args.command,
                )
                _print_json(result)
                return exit_code
            except (CodexDirectError, ValueError, WorktreeError, OSError):
                pass
        _print_json({"schema": "harness.error/v1", "error": str(exc)})
        return 2
    except (CodexDirectError, ContractError, ValueError, WorktreeError, OSError) as exc:
        _print_json({"schema": "harness.error/v1", "error": str(exc)})
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
