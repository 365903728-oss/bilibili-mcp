# Context Budget Report

Status: OK
Estimated always-relevant documentation tokens: 7911
Configured project hook entries: 9

## Files

| File | Lines | Est. tokens |
|---|---:|---:|
| `RULES.md` | 379 | 4428 |
| `AGENTS.md` | 63 | 706 |
| `CLAUDE.md` | 55 | 608 |
| `docs\agent-memory\README.md` | 72 | 823 |
| `docs\agent-memory\active-work.md` | 89 | 1346 |

## Guidance

- Keep RULES.md canonical and AGENTS.md/CLAUDE.md as thin adapter deltas.
- Keep hooks project-local and avoid loading broad external rules by default.
- Prefer on-demand skills over always-loaded instructions.
- Re-run this script after adding MCP servers, broad rules, or large agent docs.
