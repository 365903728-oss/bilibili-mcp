#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from plan_tracker import resolve_active_work, task_section_completed_count
from hook_safety import (
    read_bounded_json_object,
    read_bounded_jsonl,
    safe_agent,
    safe_category,
    safe_tool_class,
    write_bounded_text,
)

ROOT = Path(__file__).resolve().parents[2]
PROPOSAL_PATH = ROOT / "docs" / "agent-memory" / "pending-learning-proposals.md"
CANDIDATE_ID_RE = re.compile(r"^[0-9a-f]{12}$")


def now_date() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d")


def codex_memory() -> Path:
    return Path.home() / ".codex" / "memories" / "bilibili-mcp" / "memory"


def claude_memory() -> Path:
    return ROOT / ".claude" / "memory"


def runtime_dir(source: str) -> Path:
    if source == "codex":
        return Path.home() / ".codex" / "memories" / "bilibili-mcp" / "runtime"
    return ROOT / ".claude" / "runtime"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return read_bounded_jsonl(path)


def stable_candidates() -> list[dict[str, Any]]:
    candidates = read_jsonl(codex_memory() / "candidates.jsonl") + read_jsonl(claude_memory() / "candidates.jsonl")
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in candidates:
        cid = item.get("candidate_id")
        if not isinstance(cid, str) or not CANDIDATE_ID_RE.fullmatch(cid):
            continue
        grouped[cid].append(item)

    proposals: list[dict[str, Any]] = []
    for cid, items in grouped.items():
        latest = items[-1]
        try:
            recorded_evidence = int(latest.get("evidence_count") or 1)
        except (TypeError, ValueError, OverflowError):
            recorded_evidence = 1
        evidence_count = min(10_000, max(len(items), recorded_evidence, 1))
        try:
            confidence = float(latest.get("confidence") or 0.4)
        except (TypeError, ValueError, OverflowError):
            confidence = 0.4
        if not math.isfinite(confidence):
            confidence = 0.4
        confidence = min(1.0, max(0.0, confidence))
        if (
            evidence_count < 2
            and confidence < 0.7
            and latest.get("promote_after_review") is not True
        ):
            continue
        proposals.append(
            {
                "candidate_id": cid,
                "type": "lesson",
                "target": "docs/agent-memory/lessons-learned.md",
                "confidence": max(confidence, 0.7 if evidence_count >= 2 else confidence),
                "evidence_count": evidence_count,
                "agents": sorted(
                    {safe_agent(item.get("agent", "unknown")) for item in items}
                )[:32],
                "category": safe_category(latest.get("category")),
                "tool": safe_tool_class(latest.get("tool")),
                "exit_code": latest.get("exit_code")
                if isinstance(latest.get("exit_code"), int)
                else None,
                "status": "pending",
            }
        )
    return sorted(proposals, key=lambda item: (-item["confidence"], -item["evidence_count"], item["candidate_id"]))


def phase_boundary_message(source: str, proposal_count: int) -> str | None:
    runtime = runtime_dir(source)
    runtime.mkdir(parents=True, exist_ok=True)
    state_path = runtime / "learning-proposal-phase-state.json"
    reminder_path = runtime / "learning-proposal-reminder.md"

    previous_work = None
    previous = 0
    state = read_bounded_json_object(state_path, 16 * 1024)
    try:
        previous = min(10_000, max(0, int(state.get("completed_phase_count", 0))))
    except (TypeError, ValueError, OverflowError):
        previous = 0
    raw_previous_work = state.get("active_work") or state.get("active_plan")
    previous_work = (
        Path(raw_previous_work).name
        if isinstance(raw_previous_work, str)
        else None
    )

    active_work = resolve_active_work()
    completed = task_section_completed_count(active_work)
    if previous_work and previous_work != active_work.name:
        previous = 0

    write_bounded_text(
        state_path,
        json.dumps(
            {
                "completed_phase_count": completed,
                "updated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                "active_work": active_work.name,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        16 * 1024,
    )

    if completed > previous and proposal_count > 0:
        message = (
            f"Learning proposal review reminder: completed plan phases increased "
            f"from {previous} to {completed} for {active_work.name}. Review "
            "docs/agent-memory/pending-learning-proposals.md and approve with "
            "the agreed approval phrase if the proposals should be promoted."
        )
        write_bounded_text(reminder_path, message + "\n", 8 * 1024)
        return message
    return None


def render(proposals: list[dict[str, Any]]) -> str:
    lines = [
        "# Pending Learning Proposals",
        "",
        "This file is generated by `.codex/scripts/generate_learning_proposals.py`.",
        "It is a review queue only. Do not treat entries as formal memory until the user approves promotion.",
        "",
        "Approval phrase: `批准本轮 learning proposals`.",
        "",
        f"Generated: {now_date()}",
        "",
    ]

    if not proposals:
        lines.extend(
            [
                "## No Proposals",
                "",
                "No candidate currently meets the promotion threshold.",
                "",
                "Threshold: repeated evidence, confidence >= 0.7, or explicit `promote_after_review` signal.",
            ]
        )
        return "\n".join(lines) + "\n"

    for index, proposal in enumerate(proposals, start=1):
        lines.extend(
            [
                f"## Proposal {now_date()}-{index:02d}",
                "",
                f"Type: {proposal['type']}",
                f"Status: {proposal['status']}",
                f"Candidate ID: `{proposal['candidate_id']}`",
                f"Confidence: {proposal['confidence']}",
                f"Evidence count: {proposal['evidence_count']}",
                f"Agents: {', '.join(proposal['agents'])}",
                f"Suggested target: `{proposal['target']}`",
                "",
                "### Evidence",
                "",
                f"- Category: `{proposal['category']}`",
                f"- Tool class: `{proposal['tool']}`",
                f"- Exit code: `{proposal['exit_code']}`",
                "",
                "### Proposed Entry",
                "",
                f"- Lesson: repeated `{proposal['category']}` failures were observed for the bounded tool class `{proposal['tool']}`.",
                f"- Evidence: Candidate `{proposal['candidate_id']}` appeared {proposal['evidence_count']} time(s) across {', '.join(proposal['agents'])}.",
                "- Future behavior: Before promoting this lesson, Codex should confirm the failure is not synthetic, transient, or already covered by existing project memory.",
                "",
                "### Review Checklist",
                "",
                "- [ ] Verified against real task context, not only a synthetic dry run.",
                "- [ ] Contains no Cookie, token, `.env`, or secret values.",
                "- [ ] Will affect future Codex planning or Claude Code execution.",
                "- [ ] Not already captured in `docs/agent-memory/`.",
                "",
            ]
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=["codex", "claude", "manual"], default="manual")
    args = parser.parse_args()

    proposals = stable_candidates()
    PROPOSAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    write_bounded_text(PROPOSAL_PATH, render(proposals), 128 * 1024)
    reminder = phase_boundary_message(args.source, len(proposals))
    print(json.dumps({"suppressOutput": True}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
