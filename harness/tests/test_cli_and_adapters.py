from __future__ import annotations

import io
import json
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from harness.capabilities import MAX_MANUAL_SKILL_REMINDERS, check_manual_skill, doctor_report
from harness.cli import _hook_control, main
from harness.context import discover_worktree
from harness.events import normalize_hook_event
from harness.safe_io import read_bounded_jsonl


ROOT = Path(__file__).resolve().parents[2]


class CliAndAdapterTests(unittest.TestCase):
    def test_doctor_reports_three_adapters_without_provider_or_model(self) -> None:
        report = doctor_report(ROOT)
        self.assertEqual(report["schema"], "harness.doctor/v1")
        self.assertEqual(
            [adapter["mode"] for adapter in report["adapters"]],
            ["codex-direct", "codex-paseo-claude", "claude-direct"],
        )
        rendered = json.dumps(report, sort_keys=True).lower()
        self.assertNotIn('"model"', rendered)
        self.assertNotIn('"provider"', rendered)
        self.assertIn("manual_skills", report["capabilities"])

    def test_missing_manual_skill_emits_one_native_reminder(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            runtime = Path(temp)
            first = check_manual_skill(
                runtime_root=runtime,
                task_id="github-29",
                adapter="codex-direct",
                host="codex",
                skill="implement",
                invoked=False,
            )
            second = check_manual_skill(
                runtime_root=runtime,
                task_id="github-29",
                adapter="codex-direct",
                host="codex",
                skill="implement",
                invoked=False,
            )
            self.assertEqual(first["status"], "reminder-emitted")
            self.assertEqual(first["native_invocation"], "$implement")
            self.assertIn("manually", first["message"].lower())
            self.assertEqual(second["status"], "already-reminded")
            self.assertIsNone(second["message"])
            markers = list((runtime / "manual-skill-reminders").glob("*.json"))
            self.assertEqual(len(markers), 1)
            persisted = markers[0].read_text(encoding="utf-8")
            self.assertNotIn("github-29", persisted)
            self.assertNotIn("implement", persisted)

    def test_manual_skill_reminders_use_the_unsanitized_ticket_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            runtime = Path(temp)
            long_prefix = "x" * 100
            first = check_manual_skill(
                runtime_root=runtime,
                task_id=f"{long_prefix}#30",
                adapter="codex-direct",
                host="codex",
                skill="implement",
                invoked=False,
            )
            second = check_manual_skill(
                runtime_root=runtime,
                task_id=f"{long_prefix}_30",
                adapter="codex-direct",
                host="codex",
                skill="implement",
                invoked=False,
            )
            self.assertEqual(first["status"], "reminder-emitted")
            self.assertEqual(second["status"], "reminder-emitted")
            self.assertEqual(
                len(list((runtime / "manual-skill-reminders").glob("*.json"))), 2
            )

    def test_concurrent_manual_skill_checks_emit_one_reminder(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            runtime = Path(temp)

            def check(_: int) -> str:
                return check_manual_skill(
                    runtime_root=runtime,
                    task_id="github-29",
                    adapter="codex-direct",
                    host="codex",
                    skill="implement",
                    invoked=False,
                )["status"]

            with ThreadPoolExecutor(max_workers=24) as executor:
                statuses = list(executor.map(check, range(24)))

            self.assertEqual(statuses.count("reminder-emitted"), 1)
            self.assertEqual(statuses.count("already-reminded"), 23)
            self.assertEqual(
                len(list((runtime / "manual-skill-reminders").glob("*.json"))), 1
            )

    def test_manual_skill_reminder_is_not_evicted_by_later_tickets(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            runtime = Path(temp)
            first = check_manual_skill(
                runtime_root=runtime,
                task_id="stable-ticket",
                adapter="codex-direct",
                host="codex",
                skill="implement",
                invoked=False,
            )
            for index in range(MAX_MANUAL_SKILL_REMINDERS - 1):
                check_manual_skill(
                    runtime_root=runtime,
                    task_id=f"later-ticket-{index}",
                    adapter="codex-direct",
                    host="codex",
                    skill="implement",
                    invoked=False,
                )
            with self.assertRaisesRegex(ValueError, "capacity"):
                check_manual_skill(
                    runtime_root=runtime,
                    task_id="over-capacity-ticket",
                    adapter="codex-direct",
                    host="codex",
                    skill="implement",
                    invoked=False,
                )
            repeated = check_manual_skill(
                runtime_root=runtime,
                task_id="stable-ticket",
                adapter="codex-direct",
                host="codex",
                skill="implement",
                invoked=False,
            )
            self.assertEqual(first["status"], "reminder-emitted")
            self.assertEqual(repeated["status"], "already-reminded")

    def test_invoked_manual_skill_needs_no_reminder(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            result = check_manual_skill(
                runtime_root=Path(temp),
                task_id="github-29",
                adapter="claude-direct",
                host="claude",
                skill="implement",
                invoked=True,
            )
            self.assertEqual(result["status"], "invoked")
            self.assertEqual(result["native_invocation"], "/implement")
            self.assertIsNone(result["message"])

    def test_collaboration_manual_skill_requires_an_explicit_host(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, "host"):
                check_manual_skill(
                    runtime_root=Path(temp),
                    task_id="github-29",
                    adapter="codex-paseo-claude",
                    skill="implement",
                    invoked=False,
                )

            result = check_manual_skill(
                runtime_root=Path(temp),
                task_id="github-29",
                adapter="codex-paseo-claude",
                host="claude",
                skill="implement",
                invoked=True,
            )
            self.assertEqual(result["native_invocation"], "/implement")

    def test_doctor_finds_both_codex_skill_roots_and_local_hook_conflicts(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "home"
            repo = Path(temp) / "repo"
            for root, skill in (
                (home / ".agents" / "skills", "shared-skill"),
                (home / ".codex" / "skills", "codex-native-skill"),
                (home / ".claude" / "skills", "claude-skill"),
            ):
                skill_dir = root / skill
                skill_dir.mkdir(parents=True)
                (skill_dir / "SKILL.md").write_text(f"# {skill}\n", encoding="utf-8")

            (repo / ".claude").mkdir(parents=True)
            tracked = {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "tracked"}]}]}}
            local = {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "local"}]}]}}
            (repo / ".claude" / "settings.json").write_text(json.dumps(tracked), encoding="utf-8")
            (repo / ".claude" / "settings.local.json").write_text(json.dumps(local), encoding="utf-8")

            report = doctor_report(repo, home=home)
            self.assertEqual(report["status"], "action-required")
            self.assertEqual(
                report["capabilities"]["codex_skills"],
                ["codex-native-skill", "shared-skill"],
            )
            self.assertTrue(report["hooks"]["claude_local_conflict"])
            rendered = json.dumps(report, sort_keys=True)
            self.assertNotIn('"command":', rendered)
            self.assertNotIn('"command": "tracked"', rendered)
            self.assertNotIn('"command": "local"', rendered)

    def test_doctor_blocks_overlapping_primary_worktree_codex_hooks(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            home = root / "home"
            primary = root / "primary"
            linked = root / "linked"
            common_git_dir = primary / ".git"
            for directory in (
                home / ".codex",
                primary / ".codex",
                common_git_dir,
                linked / ".codex",
            ):
                directory.mkdir(parents=True, exist_ok=True)

            tracked = {
                "hooks": {
                    "Stop": [{"hooks": [{"type": "command", "command": "tracked"}]}]
                }
            }
            legacy = {
                "hooks": {
                    "Stop": [{"hooks": [{"type": "command", "command": "legacy"}]}]
                }
            }
            (linked / ".codex" / "hooks.json").write_text(
                json.dumps(tracked), encoding="utf-8"
            )
            (primary / ".codex" / "hooks.json").write_text(
                json.dumps(legacy), encoding="utf-8"
            )

            report = doctor_report(
                linked,
                home=home,
                common_git_dir=common_git_dir,
            )
            self.assertEqual(report["status"], "action-required")
            self.assertTrue(report["hooks"]["codex_external_conflict"])
            self.assertEqual(report["hooks"]["primary_codex_commands"], 1)
            rendered = json.dumps(report, sort_keys=True)
            self.assertNotIn('"command":', rendered)
            self.assertNotIn("legacy", rendered)
            self.assertNotIn(str(primary), rendered)

    def test_hook_control_never_uses_task_acceptance_language(self) -> None:
        control = _hook_control(recorded=True)
        self.assertTrue(control["recorded"])
        self.assertNotIn("accepted", json.dumps(control).lower())

    def test_hook_control_reports_persistence_failure_without_a_traceback(self) -> None:
        output = io.StringIO()
        with patch("harness.cli.read_bounded_json_stream", return_value={}):
            with patch("harness.cli.persist_hook_event", side_effect=OSError("fixture")):
                with redirect_stdout(output):
                    status = main(
                        [
                            "hook",
                            "ingest",
                            "--adapter",
                            "codex",
                            "--event",
                            "stop",
                            "--cwd",
                            str(ROOT),
                        ]
                    )
        control = json.loads(output.getvalue())
        self.assertEqual(status, 0)
        self.assertFalse(control["recorded"])
        self.assertEqual(control["reason"], "context-or-persistence-rejected")

    def test_adapter_docs_share_one_core_and_hooks_are_portable(self) -> None:
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        claude = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        rules = (ROOT / "RULES.md").read_text(encoding="utf-8")
        codex_hooks = (ROOT / ".codex" / "hooks.json").read_text(encoding="utf-8")
        claude_hooks = (ROOT / ".claude" / "settings.json").read_text(encoding="utf-8")

        self.assertIn("RULES.md", agents)
        self.assertIn("@RULES.md", claude)
        self.assertIn("Constitutional Kernel", rules)
        self.assertNotIn("C:/Users/", agents)
        self.assertNotIn("C:\\Users\\", agents)
        self.assertNotIn("C:/Users/ZX/bilibili-mcp", codex_hooks)
        self.assertIn("'git','rev-parse','--show-toplevel'", codex_hooks)
        self.assertIn("${CLAUDE_PROJECT_DIR}", claude_hooks)
        self.assertIn("PostToolUseFailure", claude_hooks)
        self.assertIn("post-tool-use-failure", claude_hooks)
        self.assertLess(len(agents), len(rules))
        self.assertLess(len(claude), len(rules))
        context_budget = (ROOT / ".codex" / "scripts" / "context_budget.py").read_text(encoding="utf-8")
        self.assertIn('ROOT / "RULES.md"', context_budget)
        self.assertIn('"settings.json"', context_budget)
        self.assertIn('"settings.local.json"', context_budget)

    def test_package_allowlist_excludes_harness_runtime(self) -> None:
        package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
        files = package["files"]
        self.assertNotIn("harness", files)
        self.assertNotIn(".harness", files)
        self.assertNotIn("docs/agent-memory", files)

    def test_replay_cli_uses_the_same_typed_projection(self) -> None:
        fixture_root = ROOT / "harness" / "fixtures"
        semantics = []
        for adapter, fixture in (
            ("codex", "codex-post-tool-use.json"),
            ("claude", "claude-post-tool-use-failure.json"),
        ):
            event = "post-tool-use" if adapter == "codex" else "post-tool-use-failure"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "harness",
                    "hook",
                    "replay",
                    "--adapter",
                    adapter,
                    "--event",
                    event,
                    "--payload",
                    str(fixture_root / fixture),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            semantics.append(json.loads(result.stdout)["semantic"])
        self.assertEqual(semantics[0], semantics[1])

    def test_codex_hook_commands_preserve_stdin_from_a_nested_directory(self) -> None:
        raw_session = "SYNTHETIC_PROCESS_BOUNDARY_SESSION_29"
        config = json.loads((ROOT / ".codex" / "hooks.json").read_text(encoding="utf-8"))
        expected_events = {
            "SessionStart": "session-start",
            "PostToolUse": "post-tool-use",
            "PreCompact": "pre-compact",
            "Stop": "stop",
        }
        for hook_name in expected_events:
            command = config["hooks"][hook_name][0]["hooks"][0]["command"]
            result = subprocess.run(
                command,
                cwd=ROOT / "src" / "bilibili",
                input=json.dumps({"session_id": raw_session}),
                shell=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            controls = [
                json.loads(line)
                for line in result.stdout.splitlines()
                if line.strip().startswith("{")
            ]
            self.assertTrue(controls, result.stdout)
            self.assertTrue(controls[-1]["recorded"], controls[-1])
        normalized = normalize_hook_event(
            "codex", "session-start", {"session_id": raw_session}
        )
        context = discover_worktree(ROOT)
        ledger = context.runtime_root / normalized["session_id"] / "events.jsonl"
        rows = read_bounded_jsonl(ledger)
        self.assertTrue(rows)
        rendered = json.dumps(rows, sort_keys=True)
        self.assertNotIn(raw_session, str(ledger))
        self.assertNotIn(raw_session, rendered)
        self.assertEqual(rows[-1]["session_id"], normalized["session_id"])
        self.assertTrue(
            set(expected_events.values()).issubset(
                {row["semantic"]["event"] for row in rows}
            )
        )


if __name__ == "__main__":
    unittest.main()
