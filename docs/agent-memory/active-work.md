# Active Work

Workflow: Matt Pocock skills with GitHub Issues, bounded Codex-to-Claude handoffs, and Paseo CLI execution.

Active work: none. GitHub Issue #16's backward-compatible `get_video_transcript` structured-output pilot is implemented in commit `29f663a`; the issue remains open with `ready-for-human` for tracker closure.

Status: all planned gates pass. The stale ignored `.env` credential override was removed, a fresh process reports `source: global_config` and `logged_in: true`, SDK 1.27.1 proves exact legacy-text/structured-content equality for `BV1vL411G7N7`, and Codex CLI 0.144.6 displays the legacy JSON without output-schema failure. The exposed session still requires rotation, but product acceptance is complete and delivery to `origin/master` is authorized. Version `1.7.2` remains the published npm/GitHub release; no version or release action is authorized for Issue #16.

Codex launches and reviews one bounded Claude Code implementation agent through Paseo. The user does not manually transfer prompts between Codex and Claude Code.

Files under `docs/superpowers/` are historical records only. They are not current instructions and must not trigger any `superpowers:*` skill.

Controlled-learning proposals remain manual. GitHub ticket progress does not enable local phase-count reminders.
