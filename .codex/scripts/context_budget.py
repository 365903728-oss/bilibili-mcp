#!/usr/bin/env python3
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "docs" / "agent-memory" / "context-budget-report.md"


def estimate_tokens(text: str) -> int:
    return max(1, round(len(text) / 4))


def file_tokens(path: Path) -> tuple[int, int]:
    if not path.exists():
        return 0, 0
    text = path.read_text(encoding="utf-8", errors="ignore")
    return len(text.splitlines()), estimate_tokens(text)


def count_json_hooks(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return 0
    hooks = data.get("hooks", data)
    if not isinstance(hooks, dict):
        return 0
    total = 0
    for entries in hooks.values():
        if isinstance(entries, list):
            total += len(entries)
    return total


def main() -> int:
    files = [
        ROOT / "RULES.md",
        ROOT / "AGENTS.md",
        ROOT / "CLAUDE.md",
        ROOT / "docs" / "agent-memory" / "README.md",
        ROOT / "docs" / "agent-memory" / "active-work.md",
    ]
    rows: list[tuple[str, int, int]] = []
    for path in files:
        lines, tokens = file_tokens(path)
        rows.append((str(path.relative_to(ROOT)), lines, tokens))

    hook_count = sum(
        count_json_hooks(path)
        for path in (
            ROOT / ".codex" / "hooks.json",
            ROOT / ".claude" / "settings.json",
            ROOT / ".claude" / "settings.local.json",
        )
    )
    total_tokens = sum(row[2] for row in rows)
    status = "OK"
    if total_tokens > 12000 or hook_count > 12:
        status = "REVIEW"
    if total_tokens > 20000 or hook_count > 20:
        status = "HIGH"

    lines = [
        "# Context Budget Report",
        "",
        f"Status: {status}",
        f"Estimated always-relevant documentation tokens: {total_tokens}",
        f"Configured project hook entries: {hook_count}",
        "",
        "## Files",
        "",
        "| File | Lines | Est. tokens |",
        "|---|---:|---:|",
    ]
    for name, line_count, tokens in rows:
        lines.append(f"| `{name}` | {line_count} | {tokens} |")

    lines.extend([
        "",
        "## Guidance",
        "",
        "- Keep RULES.md canonical and AGENTS.md/CLAUDE.md as thin adapter deltas.",
        "- Keep hooks project-local and avoid loading broad external rules by default.",
        "- Prefer on-demand skills over always-loaded instructions.",
        "- Re-run this script after adding MCP servers, broad rules, or large agent docs.",
    ])

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
