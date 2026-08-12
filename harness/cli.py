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
from harness.memory import (
    MAX_ENVELOPE_BYTES,
    memory_envelope_digest,
    project_memory,
    startup_memory,
)
from harness.paseo_collaboration import (
    COLLAB_GUARD_ACTIONS,
    PaseoCollaborationError,
    bootstrap,
    collaboration_accept,
    collaboration_advance,
    collaboration_commit,
    collaboration_guard,
    collaboration_judge,
    collaboration_record_check,
    collaboration_record_risk,
    collaboration_status,
    dispatch,
    preflight,
    recover,
    repair,
    report,
)
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


MODE_BY_COMMAND = {
    "codex-direct": "codex-direct",
    "claude-direct": "claude-direct",
    "codex-paseo-claude": "codex-paseo-claude",
}


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

    memory = subcommands.add_parser(
        "memory", help="project accepted typed evidence and load bounded current memory"
    )
    memory_sub = memory.add_subparsers(dest="memory_command", required=True)
    project = memory_sub.add_parser("project")
    project.add_argument("path", type=Path)
    project.add_argument("--cwd", type=Path, default=Path.cwd())
    project.add_argument("--task", required=True)
    digest = memory_sub.add_parser("digest")
    digest.add_argument("path", type=Path)
    digest.add_argument("--cwd", type=Path, default=Path.cwd())
    startup = memory_sub.add_parser("startup")
    startup.add_argument("--cwd", type=Path, default=Path.cwd())

    _add_direct_parser(subcommands, "codex-direct", "Codex Direct")
    _add_direct_parser(subcommands, "claude-direct", "Claude Direct")

    # --- codex-paseo-claude (collaboration loop + full lifecycle) ---
    paseo = subcommands.add_parser(
        "codex-paseo-claude", help="run the Codex–Paseo–Claude collaboration loop"
    )
    paseo_actions = paseo.add_subparsers(dest="direct_command", required=True)

    preflight_act = paseo_actions.add_parser("preflight")
    preflight_act.add_argument("--cwd", type=Path, default=Path.cwd())
    preflight_act.add_argument("--provider")

    boot_act = paseo_actions.add_parser("bootstrap")
    boot_act.add_argument("path", type=Path)
    boot_act.add_argument("--cwd", type=Path, default=Path.cwd())
    boot_act.add_argument("--provider")

    disp_act = paseo_actions.add_parser("dispatch")
    disp_act.add_argument("--cwd", type=Path, default=Path.cwd())
    disp_act.add_argument("--task", required=True)
    disp_act.add_argument("--handoff", type=Path, required=True)

    report_act = paseo_actions.add_parser("report")
    report_act.add_argument("path", type=Path)
    report_act.add_argument("--cwd", type=Path, default=Path.cwd())
    report_act.add_argument("--task", required=True)

    repair_act = paseo_actions.add_parser("repair")
    repair_act.add_argument("--cwd", type=Path, default=Path.cwd())
    repair_act.add_argument("--task", required=True)
    repair_act.add_argument("--review", type=Path, required=True)

    recover_act = paseo_actions.add_parser("recover")
    recover_act.add_argument("--cwd", type=Path, default=Path.cwd())
    recover_act.add_argument("--task", required=True)
    recover_act.add_argument("--reason")

    # --- lifecycle commands (shared with codex-direct/claude-direct) ---
    guard_act = paseo_actions.add_parser("guard")
    guard_act.add_argument("--cwd", type=Path, default=Path.cwd())
    guard_act.add_argument("--task", required=True)
    guard_act.add_argument("--action", choices=sorted(COLLAB_GUARD_ACTIONS), required=True)
    guard_act.add_argument("--actor", choices=("codex", "claude"), required=True)
    guard_act.add_argument("--path")

    status_act = paseo_actions.add_parser("status")
    status_act.add_argument("--cwd", type=Path, default=Path.cwd())
    status_act.add_argument("--task", required=True)

    advance_act = paseo_actions.add_parser("advance")
    advance_act.add_argument("--cwd", type=Path, default=Path.cwd())
    advance_act.add_argument("--task", required=True)
    advance_act.add_argument("--to", choices=("verifying", "reviewing"), required=True)

    check_act = paseo_actions.add_parser("record-check")
    check_act.add_argument("--cwd", type=Path, default=Path.cwd())
    check_act.add_argument("--task", required=True)
    check_act.add_argument("--check", required=True)
    check_act.add_argument("--status", choices=("pass", "fail", "skipped"), required=True)
    check_act.add_argument("--source", choices=("command", "inspection", "review"), required=True)
    check_act.add_argument("--exit-code", type=int)
    check_act.add_argument("--sensitivity", choices=("public", "metadata", "secret-free"), required=True)
    check_act.add_argument("--digest", required=True)
    check_act.add_argument("--reason-code")

    judge_act = paseo_actions.add_parser("judge")
    judge_act.add_argument("--cwd", type=Path, default=Path.cwd())
    judge_act.add_argument("--task", required=True)
    judge_act.add_argument("--criterion", required=True)
    judge_act.add_argument("--status", choices=("pass", "fail"), required=True)
    judge_act.add_argument("--evidence-digest", required=True)

    risk_act = paseo_actions.add_parser("risk")
    risk_act.add_argument("--cwd", type=Path, default=Path.cwd())
    risk_act.add_argument("--task", required=True)
    risk_act.add_argument("--risk", required=True)
    risk_act.add_argument("--severity", choices=("low", "medium", "high", "critical"), required=True)
    risk_act.add_argument("--status", choices=("open", "accepted", "resolved"), required=True)
    risk_act.add_argument("--digest", required=True)

    accept_act = paseo_actions.add_parser("accept")
    accept_act.add_argument("--cwd", type=Path, default=Path.cwd())
    accept_act.add_argument("--task", required=True)
    accept_act.add_argument("--message", default="chore(harness): create accepted ticket commit")

    commit_act = paseo_actions.add_parser("commit")
    commit_act.add_argument("--cwd", type=Path, default=Path.cwd())
    commit_act.add_argument("--task", required=True)
    commit_act.add_argument("--message", required=True)

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
            doctor_payload = doctor_report(
                context.root,
                common_git_dir=context.common_git_dir,
            )
            doctor_payload["context"] = {
                "repository_id": context.repository_id,
                "worktree_id": context.worktree_id,
                "repository_root": str(context.root),
                "head_sha": context.head_sha,
            }
            _print_json(doctor_payload)
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

        if args.command == "memory":
            context = discover_worktree(args.cwd)
            if args.memory_command == "project":
                result = project_memory(
                    context,
                    _load_json_file(args.path, MAX_ENVELOPE_BYTES),
                    target_task_id=args.task,
                )
            elif args.memory_command == "digest":
                result = {
                    "schema": "harness.memory-evidence-digest/v1",
                    "evidence_digest": memory_envelope_digest(
                        _load_json_file(args.path, MAX_ENVELOPE_BYTES)
                    ),
                }
            else:
                result = startup_memory(context)
            _print_json(result)
            return 0

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

        if args.command == "codex-paseo-claude":
            context = discover_worktree(args.cwd)
            if args.direct_command == "preflight":
                result = preflight(
                    context,
                    provider_override=args.provider,
                )
                exit_code = 0 if result["available"] else 1
                _print_json(result)
                return exit_code
            elif args.direct_command == "bootstrap":
                contract_value = _load_json_file(args.path)
                task_value = contract_value.get("task", {})
                candidate_task_id = (
                    task_value.get("id") if isinstance(task_value, dict) else None
                )
                if isinstance(candidate_task_id, str):
                    recovery_task_id = candidate_task_id
                result, exit_code = bootstrap(
                    context,
                    contract_value,
                    provider_override=args.provider,
                )
                _print_json(result)
                return exit_code
            elif args.direct_command == "dispatch":
                result = dispatch(
                    context,
                    task_id=args.task,
                    handoff_path=args.handoff,
                )
                _print_json(result)
                return 0
            elif args.direct_command == "report":
                report_value = _load_json_file(args.path)
                result = report(
                    context,
                    task_id=args.task,
                    report_value=report_value,
                )
                _print_json(result)
                return 0
            elif args.direct_command == "repair":
                result, exit_code = repair(
                    context,
                    task_id=args.task,
                    review_path=args.review,
                )
                _print_json(result)
                return exit_code
            elif args.direct_command == "recover":
                fingerprint = hashlib.sha256(
                    f"recovery-v1\0{getattr(args, 'reason', '')}".encode("utf-8")
                ).hexdigest()
                result, exit_code = recover(
                    context,
                    task_id=args.task,
                    category="adapter-failure",
                    fingerprint=fingerprint,
                )
                _print_json(result)
                return exit_code
            elif args.direct_command == "guard":
                result, exit_code = collaboration_guard(
                    context,
                    task_id=args.task,
                    action=args.action,
                    actor=args.actor,
                    path=args.path,
                )
                _print_json(result)
                return exit_code
            elif args.direct_command == "status":
                result = collaboration_status(context, task_id=args.task)
                _print_json(result)
                return 0
            elif args.direct_command == "advance":
                result = collaboration_advance(
                    context, task_id=args.task, target=args.to
                )
                _print_json(result)
                return 0
            elif args.direct_command == "record-check":
                result = collaboration_record_check(
                    context,
                    task_id=args.task,
                    check_id=args.check,
                    status=args.status,
                    source=args.source,
                    exit_code=args.exit_code,
                    sensitivity=args.sensitivity,
                    digest=args.digest,
                    reason_code=args.reason_code,
                )
                _print_json(result)
                return 0
            elif args.direct_command == "judge":
                result = collaboration_judge(
                    context,
                    task_id=args.task,
                    criterion_id=args.criterion,
                    status=args.status,
                    evidence_digest=args.evidence_digest,
                )
                _print_json(result)
                return 0
            elif args.direct_command == "risk":
                result = collaboration_record_risk(
                    context,
                    task_id=args.task,
                    risk_id=args.risk,
                    severity=args.severity,
                    status=args.status,
                    digest=args.digest,
                )
                _print_json(result)
                return 0
            elif args.direct_command == "accept":
                result = collaboration_accept(
                    context,
                    task_id=args.task,
                    message=args.message,
                )
                _print_json(result)
                return 0
            elif args.direct_command == "commit":
                result = collaboration_commit(
                    context,
                    task_id=args.task,
                    message=args.message,
                )
                _print_json(result)
                return 0
            return 2
    except (CodexDirectAdapterError, PaseoCollaborationError) as exc:
        task_id = getattr(args, "task", None) or recovery_task_id
        expected_mode = MODE_BY_COMMAND.get(args.command, args.command)
        if args.command in {"codex-direct", "claude-direct", "codex-paseo-claude"} and isinstance(task_id, str):
            fingerprint = hashlib.sha256(
                f"adapter-failure-v1\0{exc}".encode("utf-8")
            ).hexdigest()
            try:
                result, exit_code = enter_recovery(
                    context or discover_worktree(args.cwd),
                    task_id=task_id,
                    category="adapter-failure",
                    fingerprint=fingerprint,
                    expected_mode=expected_mode,
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
