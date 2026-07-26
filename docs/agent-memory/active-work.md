# Active Work

Workflow: Matt Pocock skills with GitHub Issues, bounded Codex-to-Claude handoffs, and Paseo CLI execution.

Active work: GitHub Issues #18 and #19 are delivered to `master` and closed. GitHub Issue #20 is the next untriaged compatibility follow-up.

Status: Commits `8cad77c` (v1.8.0 source preparation) and `2c87750` (production dependency refresh) are on `origin/master`. Package/lock version is `1.8.0`; build and all 299 tests passed immediately before push. Three production advisories are cleared, while one underlying moderate Hono `serveStatic` advisory remains statically unreachable and awaits an upstream Node 18-compatible SDK fix. Version `1.7.2` remains the published npm/GitHub release, and the README links remain on that real release until v1.8.0 publication is separately authorized.

Codex launches and reviews one bounded Claude Code implementation agent through Paseo. The user does not manually transfer prompts between Codex and Claude Code.

Files under `docs/superpowers/` are historical records only. They are not current instructions and must not trigger any `superpowers:*` skill.

Controlled-learning proposals remain manual. GitHub ticket progress does not enable local phase-count reminders.
