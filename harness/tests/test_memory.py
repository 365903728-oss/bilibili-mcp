from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from harness import memory as memory_module
from harness.context import discover_worktree
from harness.memory import (
    MAX_PROJECTION_BYTES,
    MemoryProjectionError,
    _target_memory_writer,
    compile_memory_capability,
    memory_envelope_digest,
    project_memory,
    startup_memory,
)


ROOT = Path(__file__).resolve().parents[2]


@contextmanager
def target_writer_gate(allowed: bool):
    if not allowed:
        raise MemoryProjectionError("memory target task gate failed")
    yield


def clean_memory_git(root: Path, *args: str) -> bytes:
    if args and args[0] == "ls-files":
        return (
            b"docs/agent-memory/current-memory.json\0"
            b"docs/agent-memory/typed-memory.json\0"
        )
    if args and args[0] in {"ls-tree", "show"}:
        return subprocess.run(
            ["git", "-C", str(root), *args],
            check=True,
            capture_output=True,
            env=isolated_environment(),
        ).stdout
    return b""


def isolated_environment() -> dict[str, str]:
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.upper().startswith(("GIT_", "SSH_", "GCM_"))
        and not any(
            marker in key.upper()
            for marker in (
                "TOKEN",
                "SECRET",
                "PASSWORD",
                "COOKIE",
                "CREDENTIAL",
                "API_KEY",
                "ACCESS_KEY",
                "AUTH",
                "SESSDATA",
                "BILI_JCT",
                "DEDEUSERID",
            )
        )
    }
    environment.update(
        {
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0",
            "GCM_INTERACTIVE": "Never",
        }
    )
    return environment


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=isolated_environment(),
    ).stdout.strip()


class MemoryProjectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / "repo"
        self.repo.mkdir()
        git(self.repo, "init", "-b", "main")
        git(self.repo, "config", "user.name", "Harness Test")
        git(self.repo, "config", "user.email", "harness@example.invalid")
        (self.repo / ".gitignore").write_text(".harness/\n", encoding="utf-8")
        (self.repo / "README.md").write_text("seed\n", encoding="utf-8")
        git(self.repo, "add", ".gitignore", "README.md")
        git(self.repo, "commit", "-m", "seed")
        self.context = discover_worktree(self.repo)
        self.commit_sha = git(self.repo, "rev-parse", "HEAD")
        self.clean_memory_status = patch(
            "harness.memory._git_bytes", side_effect=clean_memory_git
        )
        self.clean_memory_status.start()
        self.addCleanup(self.clean_memory_status.stop)

    def accepted_status(self, evidence_digest: str) -> dict[str, object]:
        return {
            "state": "accepted",
            "commit_sha": self.commit_sha,
            "writer_lease": {"holder": "codex", "state": "released"},
            "accepted_diff": {"diff_digest": hashlib.sha256(b"diff").hexdigest()},
            "checks": {
                "verified": {
                    "status": "pass",
                    "digest": evidence_digest,
                    "diff_digest": hashlib.sha256(b"diff").hexdigest(),
                }
            },
        }

    def envelope(self, **candidate_overrides: object) -> dict[str, object]:
        candidate: dict[str, object] = {
            "type": "fact",
            "subject": "product.tool-count",
            "value": 10,
            "evidence_kind": "reproducible-fact",
            "evidence_digest": "0" * 64,
            "sensitivity": "public",
            "valid_from": "2026-08-12T12:00:00Z",
        }
        candidate.update(candidate_overrides)
        envelope: dict[str, object] = {
            "schema": "harness.memory-evidence/v1",
            "source": {
                "task_id": "source-task",
                "commit_sha": self.commit_sha,
            },
            "candidates": [candidate],
        }
        digest = memory_envelope_digest(envelope)
        if "evidence_digest" not in candidate_overrides:
            for item in envelope["candidates"]:
                item["evidence_digest"] = digest
        return envelope

    def project(
        self,
        envelope: dict[str, object] | None = None,
        status: dict[str, object] | None = None,
        guard: tuple[dict[str, object], int] | None = None,
    ) -> dict[str, object]:
        envelope = envelope or self.envelope()
        evidence_digest = envelope["candidates"][0]["evidence_digest"]
        allowed = guard is None or guard[1] == 0
        with (
            patch(
                "harness.memory.codex_direct_status",
                return_value=status or self.accepted_status(evidence_digest),
            ),
            patch(
                "harness.memory._target_memory_writer",
                return_value=target_writer_gate(allowed),
            ),
        ):
            return project_memory(
                self.context, envelope, target_task_id="memory-target"
            )

    def startup(self) -> dict[str, object]:
        def accepted_artifact(root: Path, relative: Path, limit: int) -> bytes | None:
            path = root / relative
            content = path.read_bytes() if path.exists() else None
            if content is not None:
                self.assertLessEqual(len(content), limit)
            return content

        with patch(
            "harness.memory._head_artifact_bytes", side_effect=accepted_artifact
        ):
            return startup_memory(self.context)

    def test_verified_fact_projects_one_typed_current_record(self) -> None:
        result = self.project()

        self.assertEqual(result["schema"], "harness.memory-projection-result/v1")
        self.assertEqual(result["status"], "success")
        self.assertTrue(result["changed"])
        store = json.loads(
            (self.repo / "docs/agent-memory/typed-memory.json").read_text(encoding="utf-8")
        )
        projection = json.loads(
            (self.repo / "docs/agent-memory/current-memory.json").read_text(encoding="utf-8")
        )
        self.assertEqual(len(store["records"]), 1)
        record = store["records"][0]
        self.assertRegex(record["record_id"], r"^mem-[0-9a-f]{64}$")
        self.assertEqual(record["source"], "accepted-task")
        self.assertEqual(record["validation"], "accepted")
        self.assertEqual(record["sensitivity"], "public")
        self.assertEqual(record["evidence_digest"], self.envelope()["candidates"][0]["evidence_digest"])
        self.assertEqual(record["validity"], {"from": "2026-08-12T12:00:00Z", "to": None})
        self.assertEqual(record["supersedes"], None)
        self.assertEqual(projection["records"], [record])

    @unittest.skipIf(os.name == "nt", "directory-relative descriptors are POSIX-only")
    def test_memory_writers_fail_closed_when_parent_becomes_a_symlink(self) -> None:
        for name, writer in (
            (
                "typed-memory.json",
                lambda root, target: memory_module._write_exact(
                    root, Path("agent-memory") / target.name, b"{}\n", 1024
                ),
            ),
            (
                "project-transaction.json",
                lambda root, target: memory_module._write_transaction_marker(
                    target, {"schema": "test"}
                ),
            ),
        ):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp:
                root = Path(temp) / "root"
                parent = root / "agent-memory"
                displaced = Path(temp) / "displaced"
                external = Path(temp) / "external"
                parent.mkdir(parents=True)
                external.mkdir()
                target = parent / name
                real_mkstemp = tempfile.mkstemp
                real_open = os.open
                swapped = False

                def swap_parent() -> None:
                    nonlocal swapped
                    if swapped:
                        return
                    parent.rename(displaced)
                    parent.symlink_to(external, target_is_directory=True)
                    swapped = True

                def raced_mkstemp(*args: object, **kwargs: object):
                    if Path(kwargs["dir"]) == parent:
                        swap_parent()
                    return real_mkstemp(*args, **kwargs)

                def raced_open(
                    candidate: os.PathLike[str] | str | bytes,
                    flags: int,
                    mode: int = 0o777,
                    *,
                    dir_fd: int | None = None,
                ) -> int:
                    if (
                        dir_fd is not None
                        and flags & os.O_DIRECTORY
                        and Path(candidate).name == parent.name
                    ):
                        swap_parent()
                    if dir_fd is None:
                        return real_open(candidate, flags, mode)
                    return real_open(candidate, flags, mode, dir_fd=dir_fd)

                try:
                    with (
                        patch("tempfile.mkstemp", new=raced_mkstemp),
                        patch("harness.safe_io.os.open", new=raced_open),
                    ):
                        with self.assertRaises((OSError, ValueError)):
                            writer(root, target)
                    self.assertTrue(swapped)
                    self.assertFalse((external / name).exists())
                finally:
                    if parent.is_symlink():
                        parent.unlink()
                    if displaced.exists():
                        displaced.rename(parent)

    def test_memory_directory_creation_refuses_a_swapped_ancestor(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "root"
            external = Path(temp) / "external"
            root.mkdir()
            external.mkdir()
            docs = root / "docs"
            real_guard = memory_module.ensure_no_link_components
            swapped = False

            def swap_after_guard(boundary: Path, target: Path) -> None:
                nonlocal swapped
                real_guard(boundary, target)
                if swapped:
                    return
                if os.name == "nt":
                    subprocess.run(
                        ["cmd", "/c", "mklink", "/J", str(docs), str(external)],
                        check=True,
                        capture_output=True,
                    )
                else:
                    docs.symlink_to(external, target_is_directory=True)
                swapped = True

            try:
                with patch(
                    "harness.memory.ensure_no_link_components",
                    side_effect=swap_after_guard,
                ):
                    with self.assertRaises((OSError, ValueError)):
                        memory_module._write_exact(
                            root,
                            Path("docs/agent-memory/typed-memory.json"),
                            b"{}\n",
                            1024,
                        )
                self.assertTrue(swapped)
                self.assertFalse((external / "agent-memory").exists())
            finally:
                if docs.is_junction():
                    os.rmdir(docs)
                elif docs.is_symlink():
                    docs.unlink()

    @unittest.skipIf(os.name == "nt", "directory-relative descriptors are POSIX-only")
    def test_memory_deletes_fail_closed_when_parent_is_a_symlink(self) -> None:
        for name, delete in (
            (
                "typed-memory.json",
                lambda root, target: memory_module._restore_artifact(
                    root, Path("agent-memory") / target.name, None, 1024
                ),
            ),
            (
                "project-transaction.json",
                lambda _root, target: memory_module._clear_transaction_marker(target),
            ),
        ):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp:
                root = Path(temp) / "root"
                parent = root / "agent-memory"
                displaced = Path(temp) / "displaced"
                external = Path(temp) / "external"
                parent.mkdir(parents=True)
                external.mkdir()
                target = parent / name
                external_target = external / name
                external_target.write_text("outside\n", encoding="utf-8")
                parent.rename(displaced)
                parent.symlink_to(external, target_is_directory=True)
                try:
                    with self.assertRaises((OSError, ValueError)):
                        delete(root, target)
                    self.assertEqual(
                        external_target.read_text(encoding="utf-8"), "outside\n"
                    )
                finally:
                    parent.unlink(missing_ok=True)
                    displaced.rename(parent)

    @unittest.skipUnless(os.name == "nt", "NTFS junctions are Windows-only")
    def test_memory_writes_and_deletes_refuse_parent_junctions(self) -> None:
        for operation in ("write-race", "delete"):
            with self.subTest(operation=operation), tempfile.TemporaryDirectory() as temp:
                root = Path(temp) / "root"
                parent = root / "agent-memory"
                displaced = Path(temp) / "displaced"
                external = Path(temp) / "external"
                parent.mkdir(parents=True)
                external.mkdir()
                target = parent / "typed-memory.json"
                external_target = external / target.name
                real_mkstemp = tempfile.mkstemp
                attempted = False

                def install_junction() -> None:
                    nonlocal attempted
                    attempted = True
                    parent.rename(displaced)
                    subprocess.run(
                        ["cmd", "/c", "mklink", "/J", str(parent), str(external)],
                        check=True,
                        capture_output=True,
                    )

                def raced_mkstemp(*args: object, **kwargs: object):
                    if Path(kwargs["dir"]) == parent:
                        install_junction()
                    return real_mkstemp(*args, **kwargs)

                try:
                    if operation == "write-race":
                        with patch("tempfile.mkstemp", new=raced_mkstemp):
                            with self.assertRaises((OSError, ValueError)):
                                memory_module._write_exact(
                                    root,
                                    Path("agent-memory") / target.name,
                                    b"{}\n",
                                    1024,
                                )
                        self.assertTrue(attempted)
                    else:
                        external_target.write_text("outside\n", encoding="utf-8")
                        install_junction()
                        with self.assertRaises((OSError, ValueError)):
                            memory_module._restore_artifact(
                                root,
                                Path("agent-memory") / target.name,
                                None,
                                1024,
                            )
                        self.assertEqual(
                            external_target.read_text(encoding="utf-8"), "outside\n"
                        )
                    if operation == "write-race":
                        self.assertFalse(external_target.exists())
                finally:
                    if parent.is_junction():
                        os.rmdir(parent)
                    if displaced.exists():
                        displaced.rename(parent)

    def test_replay_is_idempotent_and_no_change_is_audited(self) -> None:
        first = self.project()
        store_path = self.repo / "docs/agent-memory/typed-memory.json"
        projection_path = self.repo / "docs/agent-memory/current-memory.json"
        first_store = store_path.read_bytes()
        first_projection = projection_path.read_bytes()

        second = self.project()

        self.assertTrue(first["changed"])
        self.assertFalse(second["changed"])
        self.assertEqual(store_path.read_bytes(), first_store)
        self.assertEqual(projection_path.read_bytes(), first_projection)
        store = json.loads(first_store)
        self.assertEqual(len(store["records"]), 1)
        audit_path = self.context.runtime_root / "memory/audit.jsonl"
        audits = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()]
        self.assertEqual([item["changed"] for item in audits], [True, False])
        self.assertTrue(all(item["status"] == "success" for item in audits))
        self.assertTrue(all("target_task_digest" in item for item in audits))

    def test_projection_failure_restores_both_memory_artifacts(self) -> None:
        self.project()
        store_path = self.repo / "docs/agent-memory/typed-memory.json"
        projection_path = self.repo / "docs/agent-memory/current-memory.json"
        before_store = store_path.read_bytes()
        before_projection = projection_path.read_bytes()
        real_write_exact = memory_module._write_exact
        failed = False

        def fail_projection_once(
            root: Path, relative: Path, content: bytes, limit: int
        ) -> None:
            nonlocal failed
            if relative == memory_module.PROJECTION_PATH and not failed:
                failed = True
                raise MemoryProjectionError("synthetic projection failure")
            real_write_exact(root, relative, content, limit)

        with patch("harness.memory._write_exact", side_effect=fail_projection_once):
            with self.assertRaisesRegex(
                MemoryProjectionError, "synthetic projection failure"
            ):
                self.project(
                    self.envelope(
                        value=11,
                        valid_from="2026-08-12T13:00:00Z",
                    )
                )

        self.assertEqual(store_path.read_bytes(), before_store)
        self.assertEqual(projection_path.read_bytes(), before_projection)
        self.assertFalse(
            (self.context.runtime_root / "memory/project-transaction.json").exists()
        )

    def test_interrupted_memory_transaction_recovers_from_its_marker(self) -> None:
        self.project()
        git(
            self.repo,
            "add",
            "docs/agent-memory/typed-memory.json",
            "docs/agent-memory/current-memory.json",
        )
        git(self.repo, "commit", "-m", "trusted memory baseline")
        envelope = self.envelope(
            value=11,
            valid_from="2026-08-12T13:00:00Z",
        )
        real_write_exact = memory_module._write_exact
        stopped = False

        def stop_after_store(
            root: Path, relative: Path, content: bytes, limit: int
        ) -> None:
            nonlocal stopped
            real_write_exact(root, relative, content, limit)
            if relative == memory_module.STORE_PATH and not stopped:
                stopped = True
                raise SystemExit("synthetic process stop")

        with patch("harness.memory._write_exact", side_effect=stop_after_store):
            with self.assertRaisesRegex(SystemExit, "synthetic process stop"):
                self.project(envelope)

        marker = self.context.runtime_root / "memory/project-transaction.json"
        self.assertTrue(marker.is_file())
        store_path = self.repo / "docs/agent-memory/typed-memory.json"
        valid_store_bytes = store_path.read_bytes()
        valid_marker_bytes = marker.read_bytes()
        trusted_store = json.loads(
            git(
                self.repo,
                "show",
                "HEAD:docs/agent-memory/typed-memory.json",
            )
        )
        forged_record = json.loads(json.dumps(trusted_store["records"][0]))
        forged_record["subject"] = "forged.promotion"
        forged_record["value"] = 99
        forged_record["record_id"] = memory_module._record_id(forged_record)
        forged_record["validity"]["to"] = None
        forged_record["supersedes"] = None
        forged_record["superseded_by"] = None
        forged_prior = json.loads(json.dumps(trusted_store))
        forged_prior["records"].append(forged_record)
        forged_prior["records"].sort(key=lambda record: record["record_id"])
        forged_prior_bytes = memory_module._pretty_bytes(
            forged_prior, memory_module.MAX_STORE_BYTES
        )
        forged_prior_digest = hashlib.sha256(forged_prior_bytes).hexdigest()
        forged_prior_projection = memory_module._pretty_bytes(
            memory_module._projection(
                forged_prior["records"], forged_prior_digest
            ),
            memory_module.MAX_PROJECTION_BYTES,
        )
        forged_store = json.loads(valid_store_bytes)
        forged_store["records"].append(forged_record)
        forged_store["records"].sort(key=lambda record: record["record_id"])
        forged_store_bytes = memory_module._pretty_bytes(
            forged_store, memory_module.MAX_STORE_BYTES
        )
        forged_marker = json.loads(valid_marker_bytes)
        forged_marker["before_store_digest"] = forged_prior_digest
        forged_marker["before_projection_digest"] = hashlib.sha256(
            forged_prior_projection
        ).hexdigest()
        store_path.write_bytes(forged_store_bytes)
        marker.write_bytes(
            memory_module._pretty_bytes(
                forged_marker, memory_module.MAX_TRANSACTION_BYTES
            )
        )
        with self.assertRaisesRegex(MemoryProjectionError, "manual recovery"):
            self.project(envelope)
        store_path.write_bytes(valid_store_bytes)
        marker.write_bytes(valid_marker_bytes)
        with self.assertRaisesRegex(MemoryProjectionError, "does not match"):
            self.project(
                self.envelope(
                    value=12,
                    valid_from="2026-08-12T14:00:00Z",
                )
            )
        recovered = self.project(envelope)
        self.assertFalse(marker.exists())
        self.assertTrue(recovered["changed"])
        self.assertEqual(
            [record["value"] for record in self.startup()["records"]],
            [11],
        )

    def test_interrupted_transaction_recovers_duplicate_candidate_envelope(
        self,
    ) -> None:
        self.project()
        git(
            self.repo,
            "add",
            "docs/agent-memory/typed-memory.json",
            "docs/agent-memory/current-memory.json",
        )
        git(self.repo, "commit", "-m", "trusted memory baseline")
        envelope = self.envelope(
            value=11,
            valid_from="2026-08-12T13:00:00Z",
        )
        envelope["candidates"].append(
            json.loads(json.dumps(envelope["candidates"][0]))
        )
        evidence_digest = memory_envelope_digest(envelope)
        for candidate in envelope["candidates"]:
            candidate["evidence_digest"] = evidence_digest
        real_write_exact = memory_module._write_exact
        stopped = False

        def stop_after_store(
            root: Path, relative: Path, content: bytes, limit: int
        ) -> None:
            nonlocal stopped
            real_write_exact(root, relative, content, limit)
            if relative == memory_module.STORE_PATH and not stopped:
                stopped = True
                raise SystemExit("synthetic process stop")

        with patch("harness.memory._write_exact", side_effect=stop_after_store):
            with self.assertRaisesRegex(SystemExit, "synthetic process stop"):
                self.project(envelope)

        recovered = self.project(envelope)
        self.assertTrue(recovered["changed"])
        self.assertFalse(
            (self.context.runtime_root / "memory/project-transaction.json").exists()
        )

    def test_new_current_fact_supersedes_the_old_projection(self) -> None:
        self.project()

        self.project(
            self.envelope(
                value=11,
                valid_from="2026-08-12T13:00:00Z",
            )
        )

        store = json.loads(
            (self.repo / "docs/agent-memory/typed-memory.json").read_text(encoding="utf-8")
        )
        old, new = sorted(store["records"], key=lambda item: item["validity"]["from"])
        self.assertEqual(old["validity"]["to"], "2026-08-12T13:00:00Z")
        self.assertEqual(old["superseded_by"], new["record_id"])
        self.assertEqual(new["supersedes"], old["record_id"])
        projection = self.startup()
        self.assertEqual([item["value"] for item in projection["records"]], [11])

    def test_newest_fact_can_return_to_a_previously_seen_value(self) -> None:
        self.project()
        self.project(self.envelope(value=11, valid_from="2026-08-12T13:00:00Z"))

        self.project(self.envelope(value=10, valid_from="2026-08-12T14:00:00Z"))

        store = json.loads(
            (self.repo / "docs/agent-memory/typed-memory.json").read_text(encoding="utf-8")
        )
        facts = sorted(store["records"], key=lambda item: item["validity"]["from"])
        self.assertEqual([item["value"] for item in facts], [10, 11, 10])
        self.assertEqual(
            [item["validity"]["to"] for item in facts],
            ["2026-08-12T13:00:00Z", "2026-08-12T14:00:00Z", None],
        )
        self.assertEqual(
            [item["value"] for item in self.startup()["records"]], [10]
        )

    def test_conflicting_facts_at_the_same_validity_start_are_rejected(self) -> None:
        self.project()

        with self.assertRaisesRegex(MemoryProjectionError, "ambiguous current facts"):
            self.project(self.envelope(value=11))

        projection = self.startup()
        self.assertEqual([item["value"] for item in projection["records"]], [10])

    def test_user_correction_promotes_once_but_one_task_cannot_promote_a_lesson(self) -> None:
        correction = self.envelope(
            type="lesson",
            subject="process.corrected-rule",
            value="Use the accepted current diff",
            evidence_kind="user-correction",
        )
        repeated = self.envelope(
            type="lesson",
            subject="process.general-rule",
            value="Inspect the shared seam",
            evidence_kind="process-observation",
        )
        repeated["candidates"].append(
            {**repeated["candidates"][0]}
        )
        repeated_digest = memory_envelope_digest(repeated)
        for item in repeated["candidates"]:
            item["evidence_digest"] = repeated_digest
        status = self.accepted_status(repeated_digest)

        self.project(correction)
        self.project(repeated, status)

        records = json.loads(
            (self.repo / "docs/agent-memory/typed-memory.json").read_text(encoding="utf-8")
        )["records"]
        by_subject = {item["subject"]: item for item in records}
        self.assertEqual(by_subject["process.corrected-rule"]["validation"], "accepted")
        self.assertEqual(by_subject["process.general-rule"]["validation"], "proposed")
        self.assertEqual(len(by_subject["process.general-rule"]["provenance"]), 1)

    def test_independent_second_task_promotes_general_lesson(self) -> None:
        lesson = self.envelope(
            type="lesson",
            subject="process.general-rule",
            value="Inspect the shared seam",
            evidence_kind="process-observation",
        )
        self.project(lesson)
        second_commit = "b" * 40
        second = json.loads(json.dumps(lesson))
        second["source"] = {"task_id": "source-task-2", "commit_sha": second_commit}
        second["candidates"][0]["valid_from"] = "2026-08-11T12:00:00Z"
        second_digest = memory_envelope_digest(second)
        second["candidates"][0]["evidence_digest"] = second_digest
        status = self.accepted_status(second_digest)
        status["commit_sha"] = second_commit
        status["checks"] = {
            "verified": {
                "status": "pass",
                "digest": second_digest,
                "diff_digest": status["accepted_diff"]["diff_digest"],
            }
        }

        self.project(second, status)

        record = json.loads(
            (self.repo / "docs/agent-memory/typed-memory.json").read_text(encoding="utf-8")
        )["records"][0]
        self.assertEqual(record["validation"], "accepted")
        self.assertEqual(
            {item["task_id"] for item in record["provenance"]},
            {"source-task", "source-task-2"},
        )
        self.assertEqual(len(self.startup()["records"]), 1)

    def test_weak_evidence_from_an_independent_task_does_not_promote_a_lesson(self) -> None:
        lesson = self.envelope(
            type="lesson",
            subject="process.general-rule",
            value="Inspect the shared seam",
            evidence_kind="process-observation",
        )
        self.project(lesson)
        second_commit = "b" * 40
        weak = json.loads(json.dumps(lesson))
        weak["source"] = {"task_id": "source-task-2", "commit_sha": second_commit}
        weak["candidates"][0]["evidence_kind"] = "external-claim"
        weak_digest = memory_envelope_digest(weak)
        weak["candidates"][0]["evidence_digest"] = weak_digest
        status = self.accepted_status(weak_digest)
        status["commit_sha"] = second_commit

        self.project(weak, status)

        record = json.loads(
            (self.repo / "docs/agent-memory/typed-memory.json").read_text(encoding="utf-8")
        )["records"][0]
        self.assertEqual(record["validation"], "proposed")
        self.assertEqual(self.startup()["records"], [])

    def test_weak_claims_are_stored_only_as_non_authoritative_records(self) -> None:
        envelope = self.envelope()
        envelope["candidates"] = [
            {
                **envelope["candidates"][0],
                "type": "fact",
                "subject": f"weak.{index}",
                "value": f"Unverified claim {index}",
                "evidence_kind": kind,
            }
            for index, kind in enumerate(
                ("external-claim", "model-inference", "weak-observation"), start=1
            )
        ]
        digest = memory_envelope_digest(envelope)
        for item in envelope["candidates"]:
            item["evidence_digest"] = digest

        self.project(envelope)

        records = json.loads(
            (self.repo / "docs/agent-memory/typed-memory.json").read_text(encoding="utf-8")
        )["records"]
        self.assertEqual(
            {item["validation"] for item in records}, {"deferred", "proposed"}
        )
        self.assertEqual(self.startup()["records"], [])

    def test_secret_and_raw_operational_values_are_rejected_without_persistence(self) -> None:
        cases: tuple[object, ...] = (
            {"token": "not-a-real-token"},
            {"api_key": "not-a-real-key"},
            {"access_token": "synthetic-access-token"},
            {"authorization": "Basic c3ludGhldGlj"},
            {"SESSDATA": "synthetic-cookie"},
            {"argv": ["git", "status"]},
            {"environment_variables": {"SAFE_NAME": "synthetic"}},
            {"sessdata_value": "synthetic-opaque-cookie-material"},
            {"cookie_value": "synthetic-opaque-cookie-material"},
            {"raw_output": "On branch main"},
            {"env_dump": {"Path": "C:\\Windows"}},
            {"sessdataValue": "synthetic-opaque-cookie-material"},
            {"accessTokenValue": "synthetic-opaque-token"},
            {"environmentDumpValue": {"Path": "C:\\Windows"}},
            {"biliJctValue": "synthetic-opaque-cookie-material"},
            {"dedeUserIdValue": "synthetic-opaque-cookie-material"},
            {"SESSDATAValue": "synthetic-opaque-cookie-material"},
            {"githubPATValue": "synthetic-opaque-token-material"},
            {"npmTokenValue": "synthetic-opaque-token-material"},
            ["cmd.exe", "/c", "whoami"],
            ["powershell.exe", "/c", "whoami"],
            {"program": "cmd.exe", "arguments": ["/c", "whoami"]},
            "git push origin main",
            "docker build .",
            "rg -n TODO .",
            "Get-ChildItem Env:",
            "C:\\Windows\\System32\\cmd.exe /c whoami",
            ".\\script.ps1 /Mode test",
            "pwd",
            "Bearer synthetic-access-token",
            "sk-synthetic-access-token-1234567890",
            "line one\nline two",
            "Cookie: SESSDATA=synthetic",
            "TOKEN=value-that-must-not-persist",
        )
        for value in cases:
            with self.subTest(value=value):
                with self.assertRaises(MemoryProjectionError):
                    self.project(self.envelope(value=value))
        self.assertFalse((self.repo / "docs/agent-memory/typed-memory.json").exists())
        self.assertFalse((self.repo / "docs/agent-memory/current-memory.json").exists())

    def test_lowercase_prose_is_not_mistaken_for_a_raw_command(self) -> None:
        result = self.project(
            self.envelope(
                type="lesson",
                subject="process.plain-prose",
                value="inspect the shared seam before editing",
                evidence_kind="user-correction",
            )
        )

        self.assertTrue(result["changed"])

        structured = self.project(
            self.envelope(
                subject="product.safe-structure",
                value={"items": ["alpha", "beta"], "count": 2},
            )
        )
        self.assertTrue(structured["changed"])

    def test_invalid_validity_timestamp_is_rejected(self) -> None:
        with self.assertRaisesRegex(MemoryProjectionError, "validity start"):
            self.project(self.envelope(valid_from="2026-02-31T12:00:00Z"))

        with self.assertRaisesRegex(MemoryProjectionError, "future"):
            self.project(self.envelope(valid_from="2099-01-01T00:00:00Z"))

    def test_source_requires_a_released_known_writer(self) -> None:
        envelope = self.envelope()
        status = self.accepted_status(envelope["candidates"][0]["evidence_digest"])
        status["writer_lease"] = {"holder": "other", "state": "released"}

        with self.assertRaisesRegex(MemoryProjectionError, "accepted committed task"):
            self.project(envelope, status)

    def test_secret_like_subject_is_rejected(self) -> None:
        for subject in (
            "credential.github_pat_abcdefghijklmnopqrstuvwxyz123456",
            "SESSDATA",
            "access_token",
        ):
            with self.subTest(subject=subject):
                with self.assertRaises(MemoryProjectionError):
                    self.project(self.envelope(subject=subject, value="opaque-value"))
        self.assertFalse((self.repo / "docs/agent-memory/typed-memory.json").exists())

    def test_project_requires_an_active_target_writer_for_both_memory_paths(self) -> None:
        blocked = ({"decision": "blocked", "reason_code": "path-not-owned"}, 5)

        with self.assertRaisesRegex(MemoryProjectionError, "target task"):
            self.project(guard=blocked)

        self.assertFalse((self.repo / "docs/agent-memory/typed-memory.json").exists())
        self.assertFalse((self.repo / "docs/agent-memory/current-memory.json").exists())

    def test_tampered_top_level_store_fields_fail_closed(self) -> None:
        store_path = self.repo / "docs/agent-memory/typed-memory.json"
        store_path.parent.mkdir(parents=True)
        for key in ("secret", "raw_stdout"):
            with self.subTest(key=key):
                store_path.write_text(
                    json.dumps(
                        {
                            "schema": "harness.typed-memory-store/v1",
                            "records": [],
                            key: "synthetic-operational-material",
                        }
                    ),
                    encoding="utf-8",
                )
                with self.assertRaises(MemoryProjectionError):
                    self.project()

    def test_target_writer_is_direct_and_exactly_memory_only(self) -> None:
        run = {
            "state": "executing",
            "contract": {
                "execution": {"mode": "codex-direct"},
                "writer_lease": {"holder": "codex", "state": "active"},
                "plan": {
                    "owned_paths": [
                        "docs/agent-memory/typed-memory.json",
                        "docs/agent-memory/current-memory.json",
                    ]
                },
            },
        }
        task_dir = self.context.runtime_root / "tasks" / "target-test"
        with (
            patch("harness.memory._task_dir", return_value=task_dir),
            patch("harness.memory._load_run", return_value=(task_dir / "run.json", run)),
        ):
            with _target_memory_writer(self.context, "memory-target"):
                pass
            claude = json.loads(json.dumps(run))
            claude["contract"]["execution"]["mode"] = "claude-direct"
            claude["contract"]["writer_lease"]["holder"] = "claude"
            with patch(
                "harness.memory._load_run",
                return_value=(task_dir / "run.json", claude),
            ):
                with _target_memory_writer(self.context, "memory-target"):
                    pass
            for mutation in (
                lambda value: value["contract"]["execution"].update(
                    mode="codex-paseo-claude"
                ),
                lambda value: value.update(state="reviewing"),
                lambda value: value["contract"]["plan"].update(
                    owned_paths=["docs/agent-memory/"]
                ),
            ):
                invalid = json.loads(json.dumps(run))
                mutation(invalid)
                with patch(
                    "harness.memory._load_run",
                    return_value=(task_dir / "run.json", invalid),
                ):
                    with self.assertRaisesRegex(MemoryProjectionError, "memory-only"):
                        with _target_memory_writer(self.context, "memory-target"):
                            pass

    def test_secret_shaped_source_task_identity_is_rejected(self) -> None:
        envelope = self.envelope()
        envelope["source"]["task_id"] = "github_pat_abcdefghijklmnopqrstuvwxyz123456"

        with self.assertRaisesRegex(MemoryProjectionError, "task identity"):
            self.project(envelope)

        self.assertFalse((self.repo / "docs/agent-memory/typed-memory.json").exists())

    def test_tampered_secret_store_fails_closed_without_projection(self) -> None:
        store_path = self.repo / "docs/agent-memory/typed-memory.json"
        store_path.parent.mkdir(parents=True)
        store_path.write_text(
            json.dumps(
                {
                    "schema": "harness.typed-memory-store/v1",
                    "records": [
                        {
                            "record_id": f"mem-{'a' * 64}",
                            "type": "fact",
                            "subject": "tampered.value",
                            "value": "github_pat_abcdefghijklmnopqrstuvwxyz123456",
                            "source": "accepted-task",
                            "provenance": [],
                            "validation": "accepted",
                            "sensitivity": "public",
                            "validity": {
                                "from": "2026-08-12T11:00:00Z",
                                "to": None,
                            },
                            "supersedes": None,
                            "superseded_by": None,
                            "evidence_digest": "a" * 64,
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        with self.assertRaises(MemoryProjectionError):
            self.project()

        self.assertFalse((self.repo / "docs/agent-memory/current-memory.json").exists())

    def test_tampered_secret_startup_projection_fails_closed(self) -> None:
        projection_path = self.repo / "docs/agent-memory/current-memory.json"
        projection_path.parent.mkdir(parents=True)
        projection_path.write_text(
            json.dumps(
                {
                    "schema": "harness.current-memory/v1",
                    "limit": 64,
                    "records": [
                        {
                            "value": "Cookie: SESSDATA=synthetic",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        with self.assertRaises(MemoryProjectionError):
            startup_memory(self.context)

    def test_startup_rejects_a_projection_not_bound_to_the_typed_store(self) -> None:
        self.project()
        (self.repo / "docs/agent-memory/typed-memory.json").unlink()

        with self.assertRaisesRegex(MemoryProjectionError, "projection"):
            startup_memory(self.context)

    def test_startup_rejects_a_self_consistent_unaccepted_projection(self) -> None:
        self.project()

        with (
            patch("harness.memory._git_bytes", return_value=b"?? current-memory.json"),
            self.assertRaisesRegex(MemoryProjectionError, "accepted in HEAD"),
        ):
            startup_memory(self.context)

    def test_startup_rejects_memory_bytes_hidden_by_a_clean_filter(self) -> None:
        self.project()
        # setUp makes Harness status report clean, as a clean filter can.
        git(
            self.repo,
            "add",
            "docs/agent-memory/typed-memory.json",
            "docs/agent-memory/current-memory.json",
        )
        git(self.repo, "commit", "-m", "trusted memory baseline")
        store_path = self.repo / "docs/agent-memory/typed-memory.json"
        projection_path = self.repo / "docs/agent-memory/current-memory.json"
        store = json.loads(store_path.read_text(encoding="utf-8"))
        store["records"][0]["value"] = 99
        store["records"][0]["record_id"] = memory_module._record_id(
            store["records"][0]
        )
        store_bytes = memory_module._pretty_bytes(store, memory_module.MAX_STORE_BYTES)
        store_digest = hashlib.sha256(store_bytes).hexdigest()
        projection_bytes = memory_module._pretty_bytes(
            memory_module._projection(store["records"], store_digest),
            memory_module.MAX_PROJECTION_BYTES,
        )
        store_path.write_bytes(store_bytes)
        projection_path.write_bytes(projection_bytes)

        with self.assertRaisesRegex(MemoryProjectionError, "accepted in HEAD"):
            startup_memory(self.context)

    def test_startup_accepts_fresh_autocrlf_checkout_of_head_memory(self) -> None:
        self.project()
        attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")
        (self.repo / ".gitattributes").write_text(attributes, encoding="utf-8")
        git(self.repo, "config", "core.autocrlf", "true")
        git(self.repo, "add", ".gitattributes", "docs/agent-memory")
        git(self.repo, "commit", "-m", "trusted memory baseline")
        store_path = self.repo / "docs/agent-memory/typed-memory.json"
        projection_path = self.repo / "docs/agent-memory/current-memory.json"
        store_path.unlink()
        projection_path.unlink()
        git(self.repo, "checkout", "--", str(store_path), str(projection_path))

        self.assertNotIn(b"\r\n", store_path.read_bytes())
        self.assertNotIn(b"\r\n", projection_path.read_bytes())
        startup_memory(self.context)

    def test_startup_rejects_an_untracked_or_ignored_memory_pair(self) -> None:
        self.project()

        with (
            patch("harness.memory._git_bytes", return_value=b""),
            self.assertRaisesRegex(MemoryProjectionError, "tracked in HEAD"),
        ):
            startup_memory(self.context)

    def test_startup_rejects_uncommitted_deletion_of_both_memory_files(self) -> None:
        self.project()
        (self.repo / "docs/agent-memory/typed-memory.json").unlink()
        (self.repo / "docs/agent-memory/current-memory.json").unlink()

        with (
            patch("harness.memory._git_bytes", return_value=b" D typed-memory.json"),
            self.assertRaisesRegex(MemoryProjectionError, "accepted in HEAD"),
        ):
            startup_memory(self.context)

    def test_startup_rejects_conflicting_current_facts(self) -> None:
        self.project()
        self.project(
            self.envelope(value=11, valid_from="2026-08-12T13:00:00Z")
        )
        records = json.loads(
            (self.repo / "docs/agent-memory/typed-memory.json").read_text(encoding="utf-8")
        )["records"]
        old, new = sorted(records, key=lambda item: item["validity"]["from"])
        old["validity"]["to"] = None
        old["superseded_by"] = None
        new["supersedes"] = None
        projection = {
            "schema": "harness.current-memory/v1",
            "limit": 64,
            "records": [new, old],
        }
        (self.repo / "docs/agent-memory/current-memory.json").write_text(
            json.dumps(projection), encoding="utf-8"
        )

        with self.assertRaisesRegex(MemoryProjectionError, "projection"):
            startup_memory(self.context)

    def test_candidate_must_cite_passing_current_accepted_evidence(self) -> None:
        envelope = self.envelope()
        unrelated = hashlib.sha256(b"unrelated").hexdigest()
        with self.assertRaisesRegex(MemoryProjectionError, "passing accepted evidence"):
            self.project(envelope, self.accepted_status(unrelated))

    def test_candidate_content_is_bound_to_the_accepted_evidence_digest(self) -> None:
        envelope = self.envelope()
        accepted_digest = envelope["candidates"][0]["evidence_digest"]
        envelope["candidates"][0]["value"] = 11

        with self.assertRaisesRegex(MemoryProjectionError, "envelope content"):
            self.project(envelope, self.accepted_status(accepted_digest))

        self.assertFalse((self.repo / "docs/agent-memory/typed-memory.json").exists())

    def test_all_six_memory_types_remain_distinct(self) -> None:
        mappings = (
            ("fact", "reproducible-fact"),
            ("decision", "accepted-decision"),
            ("lesson", "user-correction"),
            ("failure-fingerprint", "reproducible-failure"),
            ("capability-gap", "verified-capability-gap"),
            ("execution-result", "accepted-execution-result"),
        )
        envelope = self.envelope()
        envelope["candidates"] = [
            {
                **envelope["candidates"][0],
                "type": record_type,
                "subject": f"typed.{index}",
                "value": index,
                "evidence_kind": evidence_kind,
            }
            for index, (record_type, evidence_kind) in enumerate(mappings)
        ]
        digest = memory_envelope_digest(envelope)
        for item in envelope["candidates"]:
            item["evidence_digest"] = digest

        self.project(envelope)

        records = self.startup()["records"]
        self.assertEqual({item["type"] for item in records}, {item[0] for item in mappings})
        self.assertTrue(all(item["validation"] == "accepted" for item in records))

    def test_current_projection_keeps_newest_records_within_its_byte_bound(self) -> None:
        envelope = self.envelope()
        envelope["candidates"] = [
            {
                **envelope["candidates"][0],
                "subject": f"bounded.record-{index:02d}",
                "value": f"{index:02d}:" + "x" * 3000,
                "valid_from": f"2026-08-12T12:00:{index:02d}Z",
            }
            for index in range(60)
        ]
        digest = memory_envelope_digest(envelope)
        for item in envelope["candidates"]:
            item["evidence_digest"] = digest

        self.project(envelope)

        projection_path = self.repo / "docs/agent-memory/current-memory.json"
        projection = json.loads(projection_path.read_text(encoding="utf-8"))
        self.assertLessEqual(len(projection_path.read_bytes()), MAX_PROJECTION_BYTES)
        self.assertLess(len(projection["records"]), 60)
        self.assertEqual(projection["records"][0]["subject"], "bounded.record-59")
        self.assertEqual(self.startup()["records"], projection["records"])

    def test_generated_projection_is_loadable_at_its_node_bound(self) -> None:
        envelope = self.envelope()
        envelope["candidates"] = [
            {
                **envelope["candidates"][0],
                "subject": f"bounded.node-{index:02d}",
                "value": [0] * 64,
            }
            for index in range(60)
        ]
        digest = memory_envelope_digest(envelope)
        for item in envelope["candidates"]:
            item["evidence_digest"] = digest

        self.project(envelope)

        self.assertEqual(len(self.startup()["records"]), 60)

    def test_codex_and_claude_packages_compile_from_one_versioned_source(self) -> None:
        packages = {
            host: compile_memory_capability(host) for host in ("codex", "claude")
        }

        self.assertEqual(set(packages["codex"]), set(packages["claude"]))
        self.assertEqual(
            set(packages["codex"]),
            {"SKILL.md", "interface.json", "manifest.json", "evaluation.json"},
        )
        root = Path(__file__).resolve().parents[1] / "capability-packages/bilibili-mcp-memory"
        for host, package in packages.items():
            for relative, content in package.items():
                self.assertEqual(
                    (root / host / relative).read_text(encoding="utf-8"), content
                )
            manifest = json.loads(package["manifest.json"])
            interface = json.loads(package["interface.json"])
            evaluation = json.loads(package["evaluation.json"])
            self.assertEqual(manifest["host"], host)
            self.assertEqual(manifest["version"], interface["version"])
            self.assertEqual(evaluation["interface_version"], interface["version"])
            self.assertRegex(manifest["source_digest"], r"^[0-9a-f]{64}$")
        self.assertEqual(
            packages["codex"]["interface.json"], packages["claude"]["interface.json"]
        )
        self.assertEqual(
            packages["codex"]["evaluation.json"], packages["claude"]["evaluation.json"]
        )


class MemoryPilotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        git(self.repo, "init", "-b", "main")
        git(self.repo, "config", "user.name", "Harness Pilot")
        git(self.repo, "config", "user.email", "pilot@example.invalid")
        (self.repo / ".gitignore").write_text(".harness/\n", encoding="utf-8")
        (self.repo / "README.md").write_text("seed\n", encoding="utf-8")
        git(self.repo, "add", ".gitignore", "README.md")
        git(self.repo, "commit", "-m", "seed")

    def test_pilot_environment_removes_credential_variables(self) -> None:
        with patch.dict(
            os.environ,
            {
                "FIRECRAWL_API_KEY": "synthetic",
                "SERVICE_ACCESS_KEY": "synthetic",
                "CUSTOM_AUTH_HEADER": "synthetic",
                "BILI_JCT": "synthetic",
            },
            clear=False,
        ):
            environment = isolated_environment()

        for key in (
            "FIRECRAWL_API_KEY",
            "SERVICE_ACCESS_KEY",
            "CUSTOM_AUTH_HEADER",
            "BILI_JCT",
        ):
            self.assertNotIn(key, environment)

    def harness(self, *args: str) -> subprocess.CompletedProcess[str]:
        environment = isolated_environment()
        environment["PYTHONPATH"] = str(ROOT)
        return subprocess.run(
            [sys.executable, "-m", "harness", *args],
            cwd=self.repo,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    def write_contract(
        self,
        *,
        task_id: str,
        owned_paths: list[str],
        criterion: str,
        check: str,
    ) -> Path:
        path = self.root / f"{task_id}.json"
        path.write_text(
            json.dumps(
                {
                    "schema": "harness.task-contract/v1",
                    "task": {
                        "id": task_id,
                        "source": f"https://example.invalid/issues/{task_id}",
                    },
                    "execution": {
                        "mode": "codex-direct",
                        "canonical_worktree": str(self.repo.resolve()),
                        "base_sha": git(self.repo, "rev-parse", "HEAD"),
                        "branch": "main",
                        "adapter_switch_policy": "stop-and-report",
                    },
                    "plan": {
                        "objective": "Exercise one disposable Codex Direct task.",
                        "owned_paths": owned_paths,
                        "acceptance_criteria": [
                            {"id": criterion, "description": "The bounded task passes."}
                        ],
                        "verification_plan": [
                            {
                                "id": check,
                                "command": "inspect bounded output",
                                "required": True,
                            },
                            {
                                "id": f"{check}-review",
                                "command": "review the current diff",
                                "required": True,
                            },
                        ],
                        "repair_policy": {"max_attempts": 2},
                        "stop_conditions": [
                            "adapter-failure",
                            "new-authority",
                            "scope-expansion",
                        ],
                    },
                    "writer_lease": {"holder": "codex", "state": "inactive"},
                    "acceptance_owner": "codex",
                    "authority": {
                        "local_read_write_test": "allowed",
                        "local_commit": "after-acceptance",
                        "push_pr_tag_release_publish": "user-approval-required",
                        "credentials_ssh_broad_delete_history_rewrite": "blocked",
                    },
                    "state": "ready",
                    "terminal_states": [
                        "accepted",
                        "blocked",
                        "cancelled",
                        "recovery-required",
                    ],
                    "required_manual_skills": [],
                }
            ),
            encoding="utf-8",
        )
        return path

    def start(self, contract: Path) -> None:
        result = self.harness(
            "codex-direct", "start", "--cwd", str(self.repo), str(contract)
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def accept(
        self, *, task_id: str, criterion: str, check: str, evidence_digest: str
    ) -> str:
        review_digest = hashlib.sha256(f"{task_id}-review".encode()).hexdigest()
        self.assertEqual(
            self.harness(
                "codex-direct",
                "advance",
                "--cwd",
                str(self.repo),
                "--task",
                task_id,
                "--to",
                "verifying",
            ).returncode,
            0,
        )
        for check_id, source, digest in (
            (check, "command", evidence_digest),
            (f"{check}-review", "review", review_digest),
        ):
            command = [
                "codex-direct",
                "record-check",
                "--cwd",
                str(self.repo),
                "--task",
                task_id,
                "--check",
                check_id,
                "--status",
                "pass",
                "--source",
                source,
                "--sensitivity",
                "metadata",
                "--digest",
                digest,
            ]
            if source == "command":
                command.extend(["--exit-code", "0"])
            result = self.harness(*command)
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertEqual(
            self.harness(
                "codex-direct",
                "advance",
                "--cwd",
                str(self.repo),
                "--task",
                task_id,
                "--to",
                "reviewing",
            ).returncode,
            0,
        )
        self.assertEqual(
            self.harness(
                "codex-direct",
                "judge",
                "--cwd",
                str(self.repo),
                "--task",
                task_id,
                "--criterion",
                criterion,
                "--status",
                "pass",
                "--evidence-digest",
                evidence_digest,
            ).returncode,
            0,
        )
        accepted = self.harness(
            "codex-direct",
            "accept",
            "--cwd",
            str(self.repo),
            "--task",
            task_id,
            "--message",
            f"test(harness): accept {task_id}",
        )
        self.assertEqual(accepted.returncode, 0, accepted.stderr or accepted.stdout)
        payload = json.loads(accepted.stdout)
        self.assertEqual(payload["commit_status"], "created")
        return payload["commit_sha"]

    def test_real_zero_remote_codex_direct_memory_only_pilot(self) -> None:
        source_envelope = {
            "schema": "harness.memory-evidence/v1",
            "source": {
                "task_id": "source-pilot",
                "commit_sha": "0" * 40,
            },
            "candidates": [
                {
                    "type": "fact",
                    "subject": "pilot.accepted",
                    "value": True,
                    "evidence_kind": "reproducible-fact",
                    "evidence_digest": "0" * 64,
                    "sensitivity": "metadata",
                    "valid_from": "2026-08-12T12:00:00Z",
                }
            ],
        }
        source_draft = self.root / "source-envelope-draft.json"
        source_draft.write_text(json.dumps(source_envelope), encoding="utf-8")
        digested = self.harness(
            "memory", "digest", str(source_draft), "--cwd", str(self.repo)
        )
        self.assertEqual(digested.returncode, 0, digested.stderr or digested.stdout)
        digest_payload = json.loads(digested.stdout)
        self.assertEqual(digest_payload["schema"], "harness.memory-evidence-digest/v1")
        source_evidence = digest_payload["evidence_digest"]
        self.assertEqual(source_evidence, memory_envelope_digest(source_envelope))
        source_envelope["candidates"][0]["evidence_digest"] = source_evidence
        source_contract = self.write_contract(
            task_id="source-pilot",
            owned_paths=["accepted-memory.json"],
            criterion="source-created",
            check="source-check",
        )
        self.start(source_contract)
        (self.repo / "accepted-memory.json").write_text(
            json.dumps(source_envelope, sort_keys=True) + "\n", encoding="utf-8"
        )
        source_commit = self.accept(
            task_id="source-pilot",
            criterion="source-created",
            check="source-check",
            evidence_digest=source_evidence,
        )
        source_envelope["source"]["commit_sha"] = source_commit

        memory_contract = self.write_contract(
            task_id="memory-pilot",
            owned_paths=[
                "docs/agent-memory/typed-memory.json",
                "docs/agent-memory/current-memory.json",
            ],
            criterion="memory-projected",
            check="memory-check",
        )
        self.start(memory_contract)
        envelope_path = self.root / "accepted-memory.json"
        envelope_path.write_text(
            json.dumps(source_envelope),
            encoding="utf-8",
        )
        projected = self.harness(
            "memory",
            "project",
            str(envelope_path),
            "--cwd",
            str(self.repo),
            "--task",
            "memory-pilot",
        )
        self.assertEqual(projected.returncode, 0, projected.stderr or projected.stdout)
        self.assertTrue(json.loads(projected.stdout)["changed"])
        replayed = self.harness(
            "memory",
            "project",
            str(envelope_path),
            "--cwd",
            str(self.repo),
            "--task",
            "memory-pilot",
        )
        self.assertEqual(replayed.returncode, 0, replayed.stderr or replayed.stdout)
        self.assertFalse(json.loads(replayed.stdout)["changed"])
        memory_evidence = hashlib.sha256(b"memory-pilot-evidence").hexdigest()
        memory_commit = self.accept(
            task_id="memory-pilot",
            criterion="memory-projected",
            check="memory-check",
            evidence_digest=memory_evidence,
        )

        startup = self.harness("memory", "startup", "--cwd", str(self.repo))
        self.assertEqual(startup.returncode, 0, startup.stderr or startup.stdout)
        startup_payload = json.loads(startup.stdout)
        self.assertEqual(len(startup_payload["records"]), 1)
        self.assertEqual(
            startup_payload["projection_digest"],
            json.loads(projected.stdout)["projection_digest"],
        )

        self.assertNotEqual(memory_commit, source_commit)
        git(self.repo, "restore", "accepted-memory.json")
        self.assertEqual(git(self.repo, "rev-list", "--count", f"{source_commit}..HEAD"), "1")
        self.assertEqual(
            git(self.repo, "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD").splitlines(),
            [
                "docs/agent-memory/current-memory.json",
                "docs/agent-memory/typed-memory.json",
            ],
        )
        self.assertEqual(git(self.repo, "remote"), "")
        self.assertEqual(git(self.repo, "status", "--short"), "")
        self.assertRegex(
            git(self.repo, "show", "-s", "--format=%B", "HEAD"),
            r"Harness-Task: [0-9a-f]{24}",
        )


if __name__ == "__main__":
    unittest.main()

