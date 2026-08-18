from __future__ import annotations

import io
import json
import os
import stat
import subprocess
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from harness.context import discover_worktree
from harness.events import normalize_hook_event, persist_hook_event
from harness.evolution import EvolutionError, _surface, _surface_check_names
from harness.safe_io import (
    MAX_STDIN_BYTES,
    _ensure_directory_nofollow,
    _rmdir_nofollow,
    _unlink_nofollow,
    append_bounded_jsonl,
    bounded_file_lock,
    ensure_no_link_components,
    read_bounded_json_stream,
    read_bounded_jsonl,
    write_bounded_text,
)


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def load_fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class HookEventTests(unittest.TestCase):
    @unittest.skipUnless(os.name == "nt", "Windows 8.3 aliases only")
    def test_link_guard_accepts_equivalent_windows_short_aliases(self) -> None:
        boundary = Path(r"C:\Users\runneradmin\AppData\Local\Temp\repo")
        target = Path(r"C:\Users\RUNNER~1\AppData\Local\Temp\repo\handoff.md")

        def expand(path: Path) -> Path:
            return Path(str(path).replace("RUNNER~1", "runneradmin"))

        with (
            patch("harness.safe_io._windows_long_path", side_effect=expand),
            patch("harness.safe_io._is_link_like", return_value=False),
        ):
            ensure_no_link_components(boundary, target)

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

    def test_typed_events_bind_redacted_provenance_and_terminal_state(self) -> None:
        payload = {"session_id": "fixture", "tool_name": "Read"}
        codex = normalize_hook_event("codex", "post-tool-use", payload)
        claude = normalize_hook_event("claude", "post-tool-use", payload)
        stopped = normalize_hook_event("claude", "stop", payload)

        self.assertEqual(
            codex["provenance"],
            {"adapter": "codex", "host_event": "post-tool-use"},
        )
        self.assertEqual(codex["sensitivity"], "metadata")
        self.assertEqual(codex["terminal_state"], "active")
        self.assertEqual(stopped["terminal_state"], "stopped")
        self.assertRegex(codex["digest"], r"^[0-9a-f]{64}$")
        self.assertNotEqual(codex["digest"], claude["digest"])

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

    def test_jsonl_reader_rejects_a_symlink_replacement_during_open(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            ledger = root / "events.jsonl"
            external = root / "external.jsonl"
            probe = root / "symlink-probe"
            ledger.write_text('{"source":"ledger"}\n', encoding="utf-8")
            external.write_text('{"source":"external"}\n', encoding="utf-8")
            try:
                probe.symlink_to(external)
            except OSError as exc:
                self.skipTest(f"symlinks unavailable: {exc}")
            probe.unlink()

            real_path_open = Path.open
            real_os_open = os.open
            swapped = False

            def swap() -> None:
                nonlocal swapped
                if swapped:
                    return
                swapped = True
                ledger.unlink()
                ledger.symlink_to(external)

            def raced_path_open(candidate: Path, *args: object, **kwargs: object):
                if candidate == ledger:
                    swap()
                return real_path_open(candidate, *args, **kwargs)

            def raced_os_open(
                candidate: os.PathLike[str] | str | bytes,
                flags: int,
                mode: int = 0o777,
                *,
                dir_fd: int | None = None,
            ) -> int:
                if Path(candidate) == ledger or (
                    dir_fd is not None and Path(candidate).name == ledger.name
                ):
                    swap()
                if dir_fd is None:
                    return real_os_open(candidate, flags, mode)
                return real_os_open(candidate, flags, mode, dir_fd=dir_fd)

            with (
                patch.object(Path, "open", new=raced_path_open),
                patch("harness.safe_io.os.open", new=raced_os_open),
            ):
                self.assertEqual(read_bounded_jsonl(ledger), [])

    def test_jsonl_reader_rejects_growth_beyond_its_opened_byte_bound(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            ledger = Path(temp) / "events.jsonl"
            ledger.write_bytes(b"prefix\n" + b"x" * 63 + b"\n")
            late_rows = b'{"late":1}\n'
            real_path_open = Path.open
            real_fstat = os.fstat
            grown = False

            def grow() -> None:
                nonlocal grown
                if grown:
                    return
                grown = True
                with real_path_open(ledger, "ab") as handle:
                    handle.write(late_rows)

            def raced_path_open(candidate: Path, *args: object, **kwargs: object):
                if candidate == ledger:
                    grow()
                return real_path_open(candidate, *args, **kwargs)

            def raced_fstat(descriptor: int):
                opened = real_fstat(descriptor)
                grow()
                return opened

            with (
                patch.object(Path, "open", new=raced_path_open),
                patch("harness.safe_io.os.fstat", new=raced_fstat),
            ):
                self.assertEqual(read_bounded_jsonl(ledger, max_bytes=64), [])

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

    @unittest.skipUnless(os.name == "nt", "Windows compatibility regression")
    def test_atomic_writes_do_not_require_windows_fchmod(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "state.txt"
            with patch.object(
                os,
                "fchmod",
                create=True,
                side_effect=AttributeError("fchmod is unavailable"),
            ):
                write_bounded_text(target, "trusted\n", 1024)
            self.assertEqual(target.read_text(encoding="utf-8"), "trusted\n")

    @unittest.skipIf(os.name == "nt", "directory-relative descriptors are POSIX-only")
    def test_atomic_writers_fail_closed_when_parent_path_is_replaced(self) -> None:
        for name, writer in (
            ("state.txt", lambda path: write_bounded_text(path, "trusted\n", 1024)),
            ("events.jsonl", lambda path: append_bounded_jsonl(path, {"trusted": True})),
        ):
            for replace_ancestor in (False, True):
                with (
                    self.subTest(name=name, replace_ancestor=replace_ancestor),
                    tempfile.TemporaryDirectory() as temp,
                ):
                    root = Path(temp)
                    scope = root / "scope"
                    runtime = scope / "runtime"
                    displaced = root / "displaced"
                    external = root / "external"
                    runtime.mkdir(parents=True)
                    (external / "runtime").mkdir(parents=True)
                    replaced = scope if replace_ancestor else runtime
                    external_link = external if replace_ancestor else external / "runtime"
                    external_target = external / "runtime" / name
                    target = runtime / name
                    real_mkstemp = tempfile.mkstemp
                    real_open = os.open
                    swapped = False

                    def swap_parent() -> None:
                        nonlocal swapped
                        if swapped:
                            return
                        replaced.rename(displaced)
                        replaced.symlink_to(external_link, target_is_directory=True)
                        swapped = True

                    def raced_mkstemp(*args: object, **kwargs: object):
                        if Path(kwargs["dir"]) == runtime:
                            swap_parent()
                        return real_mkstemp(*args, **kwargs)

                    def raced_open(
                        candidate: os.PathLike[str] | str | bytes,
                        flags: int,
                        mode: int = 0o777,
                        *,
                        dir_fd: int | None = None,
                    ) -> int:
                        if dir_fd is None and Path(candidate) == runtime:
                            swap_parent()
                        elif (
                            dir_fd is not None
                            and not flags & os.O_CREAT
                            and Path(candidate).name == replaced.name
                        ):
                            swap_parent()
                        if dir_fd is None:
                            return real_open(candidate, flags, mode)
                        return real_open(candidate, flags, mode, dir_fd=dir_fd)

                    try:
                        with (
                            patch("harness.safe_io.tempfile.mkstemp", new=raced_mkstemp),
                            patch("harness.safe_io.os.open", new=raced_open),
                        ):
                            if name == "events.jsonl":
                                self.assertFalse(writer(target))
                            else:
                                with self.assertRaises((ValueError, OSError)):
                                    writer(target)
                        self.assertTrue(swapped)
                        self.assertFalse(external_target.exists())
                    finally:
                        if replaced.is_symlink():
                            replaced.unlink()
                        if displaced.exists():
                            displaced.rename(replaced)

    @unittest.skipIf(os.name == "nt", "directory-relative descriptors are POSIX-only")
    def test_atomic_writer_generates_temp_name_before_opening_parent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "state.txt"
            real_open = os.open
            opened = 0

            def recording_open(*args: object, **kwargs: object) -> int:
                nonlocal opened
                opened += 1
                return real_open(*args, **kwargs)

            with (
                patch("harness.safe_io.os.open", new=recording_open),
                patch(
                    "harness.safe_io.secrets.token_hex",
                    side_effect=OSError("random source failed"),
                ),
            ):
                with self.assertRaisesRegex(OSError, "random source failed"):
                    write_bounded_text(target, "trusted\n", 1024)
            self.assertEqual(opened, 0)

    @unittest.skipIf(os.name == "nt", "directory fsync is POSIX-only")
    def test_atomic_writer_fsyncs_parent_after_replace(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "state.txt"
            real_fsync = os.fsync
            synced_modes: list[int] = []

            def recording_fsync(descriptor: int) -> None:
                synced_modes.append(os.fstat(descriptor).st_mode)
                real_fsync(descriptor)

            with patch("harness.safe_io.os.fsync", new=recording_fsync):
                write_bounded_text(target, "trusted\n", 1024)

            self.assertTrue(any(stat.S_ISDIR(mode) for mode in synced_modes))

    @unittest.skipIf(os.name == "nt", "directory fsync is POSIX-only")
    def test_directory_creation_fsyncs_each_parent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "runtime" / "task"
            real_fsync = os.fsync
            synced_modes: list[int] = []

            def recording_fsync(descriptor: int) -> None:
                synced_modes.append(os.fstat(descriptor).st_mode)
                real_fsync(descriptor)

            with patch("harness.safe_io.os.fsync", new=recording_fsync):
                _ensure_directory_nofollow(target)

            self.assertEqual(len(synced_modes), 2)
            self.assertTrue(all(stat.S_ISDIR(mode) for mode in synced_modes))

    @unittest.skipIf(os.name == "nt", "directory fsync is POSIX-only")
    def test_unlink_fsyncs_parent_before_returning(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "run.json"
            target.write_text("executing\n", encoding="utf-8")
            real_fsync = os.fsync
            synced_modes: list[int] = []

            def recording_fsync(descriptor: int) -> None:
                synced_modes.append(os.fstat(descriptor).st_mode)
                real_fsync(descriptor)

            with patch("harness.safe_io.os.fsync", new=recording_fsync):
                _unlink_nofollow(target)

            self.assertFalse(target.exists())
            self.assertEqual(len(synced_modes), 1)
            self.assertTrue(stat.S_ISDIR(synced_modes[0]))

    @unittest.skipIf(os.name == "nt", "directory fsync is POSIX-only")
    def test_rmdir_fsyncs_parent_before_returning(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "ephemeral"
            target.mkdir()
            real_fsync = os.fsync
            synced_modes: list[int] = []

            def recording_fsync(descriptor: int) -> None:
                synced_modes.append(os.fstat(descriptor).st_mode)
                real_fsync(descriptor)

            with patch("harness.safe_io.os.fsync", new=recording_fsync):
                _rmdir_nofollow(target)

            self.assertFalse(target.exists())
            self.assertEqual(len(synced_modes), 1)
            self.assertTrue(stat.S_ISDIR(synced_modes[0]))

    @unittest.skipIf(os.name == "nt", "directory-relative descriptors are POSIX-only")
    def test_atomic_writer_closes_parent_when_temp_cleanup_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "state.txt"
            real_open = os.open
            real_close = os.close
            parent_descriptor: int | None = None
            closed: list[int] = []

            def recording_open(
                candidate: os.PathLike[str] | str | bytes,
                flags: int,
                mode: int = 0o777,
                *,
                dir_fd: int | None = None,
            ) -> int:
                nonlocal parent_descriptor
                if dir_fd is None:
                    descriptor = real_open(candidate, flags, mode)
                    if Path(candidate) == target.parent:
                        parent_descriptor = descriptor
                    return descriptor
                descriptor = real_open(candidate, flags, mode, dir_fd=dir_fd)
                if parent_descriptor is None and Path(candidate).name == target.parent.name:
                    parent_descriptor = descriptor
                return descriptor

            def recording_close(descriptor: int) -> None:
                closed.append(descriptor)
                real_close(descriptor)

            with (
                patch("harness.safe_io.os.open", new=recording_open),
                patch("harness.safe_io.os.close", new=recording_close),
                patch("harness.safe_io.os.replace", side_effect=OSError("replace failed")),
                patch("harness.safe_io.os.unlink", side_effect=OSError("cleanup failed")),
            ):
                with self.assertRaisesRegex(OSError, "cleanup failed"):
                    write_bounded_text(target, "trusted\n", 1024)

            self.assertIsNotNone(parent_descriptor)
            self.assertIn(parent_descriptor, closed)

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

    @unittest.skipIf(os.name == "nt", "directory-relative descriptors are POSIX-only")
    def test_lock_open_is_anchored_when_parent_is_replaced(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            runtime = root / "runtime"
            displaced = root / "displaced"
            external = root / "external"
            runtime.mkdir()
            external.mkdir()
            lock_path = runtime / "state.lock"
            real_open = os.open
            swapped = False

            def raced_open(
                candidate: os.PathLike[str] | str | bytes,
                flags: int,
                mode: int = 0o777,
                *,
                dir_fd: int | None = None,
            ) -> int:
                nonlocal swapped
                if not swapped and (
                    Path(candidate) == lock_path
                    or (dir_fd is not None and Path(candidate).name == lock_path.name)
                ):
                    runtime.rename(displaced)
                    runtime.symlink_to(external, target_is_directory=True)
                    swapped = True
                if dir_fd is None:
                    return real_open(candidate, flags, mode)
                return real_open(candidate, flags, mode, dir_fd=dir_fd)

            try:
                with patch("harness.safe_io.os.open", new=raced_open):
                    with self.assertRaisesRegex(ValueError, "lock directory changed"):
                        with bounded_file_lock(lock_path):
                            pass
                self.assertTrue(swapped)
                self.assertFalse((external / lock_path.name).exists())
                self.assertTrue((displaced / lock_path.name).is_file())
            finally:
                if runtime.is_symlink():
                    runtime.unlink()
                if displaced.exists():
                    displaced.rename(runtime)

    @unittest.skipIf(os.name == "nt", "open lock files already block directory rename")
    def test_nested_lock_rejects_replaced_parent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            runtime = root / "runtime"
            displaced = root / "displaced"
            runtime.mkdir()
            lock_path = runtime / "state.lock"
            state_path = runtime / "state.json"

            with self.assertRaisesRegex(ValueError, "runtime lock is unavailable"):
                with bounded_file_lock(lock_path):
                    runtime.rename(displaced)
                    runtime.mkdir()
                    state_path.write_text("replacement\n", encoding="utf-8")
                    with bounded_file_lock(runtime / "nested.lock"):
                        write_bounded_text(state_path, "transaction\n", 1024)

            self.assertEqual(state_path.read_text(encoding="utf-8"), "replacement\n")
            self.assertFalse((displaced / "state.json").exists())

    @unittest.skipIf(os.name == "nt", "directory-relative descriptors are POSIX-only")
    def test_nested_lock_does_not_create_through_replaced_ancestor(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            scope = root / "scope"
            runtime = scope / "runtime"
            displaced = root / "displaced"
            external = root / "external"
            runtime.mkdir(parents=True)
            external.mkdir()

            try:
                with self.assertRaisesRegex(ValueError, "runtime lock is unavailable"):
                    with bounded_file_lock(runtime / "outer.lock"):
                        scope.rename(displaced)
                        scope.symlink_to(external, target_is_directory=True)
                        with bounded_file_lock(runtime / "inner.lock"):
                            pass
                self.assertFalse((external / "runtime").exists())
            finally:
                if scope.is_symlink():
                    scope.unlink()
                if displaced.exists():
                    displaced.rename(scope)

    @unittest.skipIf(os.name == "nt", "directory-relative descriptors are POSIX-only")
    def test_lock_creation_does_not_follow_a_swapped_missing_parent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            scope = root / "scope"
            runtime = scope / "runtime"
            displaced = root / "displaced"
            external = root / "external"
            scope.mkdir()
            external.mkdir()
            real_mkdir = os.mkdir
            swapped = False

            def raced_mkdir(
                candidate: os.PathLike[str] | str | bytes,
                mode: int = 0o777,
                *,
                dir_fd: int | None = None,
            ) -> None:
                nonlocal swapped
                if not swapped and (
                    Path(candidate) == runtime or Path(candidate).name == runtime.name
                ):
                    scope.rename(displaced)
                    scope.symlink_to(external, target_is_directory=True)
                    swapped = True
                real_mkdir(candidate, mode, dir_fd=dir_fd)

            try:
                with patch("harness.safe_io.os.mkdir", new=raced_mkdir):
                    with self.assertRaisesRegex(ValueError, "runtime lock is unavailable"):
                        with bounded_file_lock(runtime / "task" / "run.lock"):
                            pass
                self.assertTrue(swapped)
                self.assertFalse((external / "runtime").exists())
            finally:
                if scope.is_symlink():
                    scope.unlink()
                if displaced.exists():
                    displaced.rename(scope)

    @unittest.skipIf(os.name == "nt", "directory flock is POSIX-only")
    def test_replaced_lock_inode_cannot_admit_a_second_writer(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            runtime = Path(temp) / "runtime"
            runtime.mkdir()
            lock_path = runtime / "run.lock"
            contender: list[str] = []

            def try_second_writer() -> None:
                try:
                    with bounded_file_lock(lock_path):
                        contender.append("acquired")
                except ValueError:
                    contender.append("rejected")

            with self.assertRaisesRegex(ValueError, "runtime lock file changed"):
                with bounded_file_lock(lock_path):
                    lock_path.unlink()
                    lock_path.write_text("replacement", encoding="utf-8")
                    with ThreadPoolExecutor(max_workers=1) as executor:
                        executor.submit(try_second_writer).result(timeout=10)

            self.assertEqual(contender, ["rejected"])


if __name__ == "__main__":
    unittest.main()
