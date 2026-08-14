from __future__ import annotations

import io
import json
import os
import subprocess
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from harness.context import discover_worktree
from harness.events import normalize_hook_event, persist_hook_event
from harness.evolution import EvolutionError, _surface, _surface_check_names
from harness.safe_io import (
    MAX_STDIN_BYTES,
    append_bounded_jsonl,
    bounded_file_lock,
    read_bounded_json_stream,
    read_bounded_jsonl,
)


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def load_fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class HookEventTests(unittest.TestCase):
    def test_codex_and_claude_replay_to_equivalent_semantics(self) -> None:
        codex = normalize_hook_event(
            "codex", "post-tool-use", load_fixture("codex-post-tool-use.json")
        )
        claude = normalize_hook_event(
            "claude",
            "post-tool-use-failure",
            load_fixture("claude-post-tool-use-failure.json"),
        )
        self.assertEqual(codex["semantic"], claude["semantic"])
        self.assertEqual(
            codex["semantic"], load_fixture("expected-post-tool-use-semantic.json")
        )
        self.assertEqual(codex["schema"], "harness.hook-event/v1")
        self.assertEqual(claude["schema"], "harness.hook-event/v1")

    def test_claude_success_message_is_not_misclassified_as_failure(self) -> None:
        event = normalize_hook_event(
            "claude", "post-tool-use", load_fixture("claude-post-tool-use.json")
        )
        self.assertEqual(event["semantic"]["outcome"], "succeeded")
        self.assertFalse(event["semantic"]["has_error"])
        self.assertIsNone(event["semantic"]["exit_code"])

    def test_normalized_event_never_contains_raw_payload_material(self) -> None:
        payload = load_fixture("codex-post-tool-use.json")
        rendered = json.dumps(
            normalize_hook_event("codex", "post-tool-use", payload),
            sort_keys=True,
        )
        for forbidden in (
            "npm test -- --run",
            "SYNTHETIC_COOKIE_VALUE",
            "SYNTHETIC_STDERR_VALUE",
            "BILIBILI_SESSDATA",
        ):
            self.assertNotIn(forbidden, rendered)

        secret_session = "SYNTHETIC_SESSION_SECRET_VALUE"
        session_event = normalize_hook_event(
            "codex", "session-start", {"session_id": secret_session}
        )
        self.assertNotIn(secret_session, json.dumps(session_event))
        self.assertRegex(session_event["session_id"], r"^session-[0-9a-f]{20}$")

    def test_bounded_reader_fails_closed_for_oversized_or_malformed_input(self) -> None:
        with self.assertRaises(ValueError):
            read_bounded_json_stream(io.BytesIO(b"x" * (MAX_STDIN_BYTES + 1)))
        with self.assertRaises(ValueError):
            read_bounded_json_stream(io.BytesIO(b"not-json"))

    def test_nested_directory_and_linked_worktree_have_distinct_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            container = Path(temp)
            main = container / "main"
            linked = container / "linked"
            main.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=main, check=True)
            subprocess.run(
                ["git", "config", "user.email", "fixture@example.invalid"],
                cwd=main,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Harness Fixture"], cwd=main, check=True
            )
            (main / "seed.txt").write_text("seed\n", encoding="utf-8")
            subprocess.run(["git", "add", "seed.txt"], cwd=main, check=True)
            subprocess.run(["git", "commit", "-qm", "seed"], cwd=main, check=True)
            subprocess.run(
                ["git", "worktree", "add", "-qb", "fixture-linked", str(linked)],
                cwd=main,
                check=True,
            )
            nested = linked / "a" / "b"
            nested.mkdir(parents=True)

            main_context = discover_worktree(main)
            linked_context = discover_worktree(nested)
            self.assertEqual(linked_context.root, linked.resolve())
            self.assertNotEqual(main_context.worktree_id, linked_context.worktree_id)
            self.assertEqual(main_context.repository_id, linked_context.repository_id)

            event = normalize_hook_event("codex", "stop", {"session_id": "fixture"})
            ledger = persist_hook_event(linked_context, event)
            self.assertTrue(ledger.is_relative_to(linked.resolve() / ".harness"))
            rows = read_bounded_jsonl(ledger)
            self.assertEqual(len(rows), 1)
            self.assertNotIn(str(main), json.dumps(rows))
            self.assertNotIn(str(linked), json.dumps(rows))

            hostile_event = normalize_hook_event(
                "codex", "stop", {"session_id": "../../C:hostile"}
            )
            hostile = persist_hook_event(linked_context, hostile_event)
            self.assertTrue(hostile.is_relative_to(linked_context.runtime_root))
            self.assertNotIn(
                ":", hostile.relative_to(linked_context.runtime_root).parts[0]
            )
            self.assertNotIn(
                "..", hostile.relative_to(linked_context.runtime_root).parts[0]
            )

            stale_event = normalize_hook_event(
                "codex", "stop", {"session_id": "stale-lock"}
            )
            stale_ledger = (
                linked_context.runtime_root / stale_event["session_id"] / "events.jsonl"
            )
            stale_ledger.parent.mkdir(parents=True, exist_ok=True)
            stale_lock = stale_ledger.with_suffix(".jsonl.lock")
            stale_lock.write_text("stale", encoding="utf-8")
            old = time.time() - 120
            os.utime(stale_lock, (old, old))
            self.assertEqual(
                persist_hook_event(linked_context, stale_event), stale_ledger
            )
            self.assertTrue(stale_lock.exists())
            self.assertEqual(len(read_bounded_jsonl(stale_ledger)), 1)

    def test_stop_event_is_observation_not_acceptance(self) -> None:
        event = normalize_hook_event("claude", "stop", {"session_id": "fixture"})
        rendered = json.dumps(event, sort_keys=True).lower()
        self.assertNotIn("accepted", rendered)
        self.assertEqual(event["semantic"]["event"], "stop")

    def test_hook_and_loop_surface_policies_are_bounded_and_fail_closed(self) -> None:
        hook = {
            "kind": "hook",
            "adapters": [
                "codex-direct",
                "claude-direct",
                "codex-paseo-claude",
            ],
            "external_system": False,
            "entrypoint": "harness-shared-cli",
            "hook": {
                "origin": "accepted-gap",
                "phases": [
                    "replay",
                    "shadow",
                    "no-secret",
                    "multi-worktree",
                    "canary",
                    "rollback",
                ],
                "observation_only": True,
                "canary_scope": "active-worktree",
            },
            "loop": None,
        }
        loop = {
            **hook,
            "kind": "loop",
            "hook": None,
            "loop": {
                "origin": "accepted-gap",
                "max_attempts": 2,
                "no_progress_limit": 1,
                "yield_to_user": True,
                "adapter_switch_policy": "stop-and-report",
            },
        }
        self.assertEqual(_surface(hook), hook)
        self.assertEqual(_surface(loop), loop)
        self.assertEqual(_surface_check_names(hook), hook["hook"]["phases"])
        self.assertEqual(
            _surface_check_names(loop),
            [
                "bounded",
                "no-progress-stop",
                "yield-to-user",
                "no-adapter-switch",
            ],
        )
        for key, unsafe in (
            ("max_attempts", 4),
            ("no_progress_limit", 3),
            ("yield_to_user", False),
            ("adapter_switch_policy", "auto"),
        ):
            hostile = json.loads(json.dumps(loop))
            hostile["loop"][key] = unsafe
            with self.assertRaisesRegex(EvolutionError, "Loop surface policy"):
                _surface(hostile)

    def test_concurrent_jsonl_writers_do_not_corrupt_or_silently_drop_rows(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            ledger = Path(temp) / "events.jsonl"
            with ThreadPoolExecutor(max_workers=8) as executor:
                results = list(
                    executor.map(
                        lambda index: append_bounded_jsonl(ledger, {"index": index}),
                        range(24),
                    )
                )
            self.assertEqual(results, [True] * 24)
            self.assertEqual(
                sorted(row["index"] for row in read_bounded_jsonl(ledger)),
                list(range(24)),
            )

    def test_lock_initialization_rejects_hard_link_without_touching_target(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            external = root / "external.bin"
            lock_path = root / "runtime" / "state.lock"
            lock_path.parent.mkdir()
            external.write_bytes(b"")
            try:
                os.link(external, lock_path)
            except OSError as exc:
                self.skipTest(f"hard links unavailable: {exc}")

            with self.assertRaises(ValueError):
                with bounded_file_lock(lock_path):
                    self.fail("hard-linked lock must not be acquired")
            self.assertEqual(external.read_bytes(), b"")


if __name__ == "__main__":
    unittest.main()
