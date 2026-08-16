from __future__ import annotations

import io
import json
import os
import hashlib
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from harness.context import discover_worktree


ROOT = Path(__file__).resolve().parents[2]


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


class CodexDirectProcessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        git(self.repo, "init", "-b", "main")
        git(self.repo, "config", "user.name", "Harness Test")
        git(self.repo, "config", "user.email", "harness@example.invalid")
        (self.repo / ".gitignore").write_text(".harness/\n", encoding="utf-8")
        (self.repo / "README.md").write_text("seed\n", encoding="utf-8")
        git(self.repo, "add", ".gitignore", "README.md")
        git(self.repo, "commit", "-m", "seed")
        self.contract_path = self.root / "contract.json"
        self.write_contract()

    def write_contract(self, **overrides: object) -> None:
        contract: dict[str, object] = {
            "schema": "harness.task-contract/v1",
            "task": {
                "id": "pilot-30",
                "source": "https://github.com/example/repo/issues/30",
            },
            "execution": {
                "mode": "codex-direct",
                "canonical_worktree": str(self.repo.resolve()),
                "base_sha": git(self.repo, "rev-parse", "HEAD"),
                "branch": "main",
                "adapter_switch_policy": "stop-and-report",
            },
            "plan": {
                "objective": "Exercise one bounded Harness-only ticket.",
                "owned_paths": ["harness-only.txt"],
                "acceptance_criteria": [
                    {"id": "writes-owned-file", "description": "The owned file is created."}
                ],
                "verification_plan": [
                    {
                        "id": "owned-file-check",
                        "command": "test -f harness-only.txt",
                        "required": True,
                    },
                    {
                        "id": "review-check",
                        "command": "inspect the final diff",
                        "required": True,
                    },
                    {
                        "id": "optional-smoke",
                        "command": "run an optional host smoke",
                        "required": False,
                    },
                ],
                "repair_policy": {"max_attempts": 2},
                "stop_conditions": ["adapter-failure", "new-authority", "scope-expansion"],
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
            "terminal_states": ["accepted", "blocked", "cancelled", "recovery-required"],
            "required_manual_skills": [
                {
                    "name": "implement",
                    "host": "codex",
                    "status": "invoked",
                    "invocation": "$implement",
                }
            ],
        }
        contract.update(overrides)
        self.contract_path.write_text(json.dumps(contract), encoding="utf-8")

    def harness(self, *args: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT)
        return subprocess.run(
            [sys.executable, "-m", "harness", *args],
            cwd=self.repo,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    def run_path(self, repo: Path | None = None) -> Path:
        context = discover_worktree(repo or self.repo)
        matches = list((context.runtime_root / "tasks").glob("*/run.json"))
        self.assertEqual(len(matches), 1)
        return matches[0]

    def prepare_reviewed_diff(self, *, content: bytes | None = None) -> None:
        started = self.harness(
            "codex-direct", "start", "--cwd", str(self.repo), str(self.contract_path)
        )
        self.assertEqual(started.returncode, 0, started.stderr or started.stdout)
        if content is None:
            (self.repo / "harness-only.txt").write_text("accepted\n", encoding="utf-8")
        else:
            (self.repo / "harness-only.txt").write_bytes(content)
        self.assertEqual(
            self.harness(
                "codex-direct",
                "advance",
                "--cwd",
                str(self.repo),
                "--task",
                "pilot-30",
                "--to",
                "verifying",
            ).returncode,
            0,
        )
        check_digest = hashlib.sha256(b"automatic-commit-check").hexdigest()
        review_digest = hashlib.sha256(b"automatic-commit-review").hexdigest()
        for check_id, source, digest in (
            ("owned-file-check", "command", check_digest),
            ("review-check", "review", review_digest),
        ):
            args = [
                "codex-direct",
                "record-check",
                "--cwd",
                str(self.repo),
                "--task",
                "pilot-30",
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
                args.extend(["--exit-code", "0"])
            result = self.harness(*args)
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertEqual(
            self.harness(
                "codex-direct",
                "advance",
                "--cwd",
                str(self.repo),
                "--task",
                "pilot-30",
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
                "pilot-30",
                "--criterion",
                "writes-owned-file",
                "--status",
                "pass",
                "--evidence-digest",
                check_digest,
            ).returncode,
            0,
        )

    def persist_accepted_fixture(self) -> None:
        import harness.codex_direct as controller

        context = discover_worktree(self.repo)
        run_path = self.run_path()
        run = json.loads(run_path.read_text(encoding="utf-8"))
        paths = controller._changed_paths(self.repo)
        snapshot = controller._path_snapshot(self.repo, paths)
        index_snapshot = controller._canonical_index_snapshot(context, paths)
        diff_digest = controller._diff_digest(self.repo)
        evidence_digest = hashlib.sha256(b"accepted-crash-fixture").hexdigest()
        evidence = {
            "status": "pass",
            "source": "command",
            "exit_code": 0,
            "sensitivity": "metadata",
            "digest": evidence_digest,
            "diff_digest": diff_digest,
            "reason_code": None,
        }
        run["checks"] = {
            "owned-file-check": evidence,
            "review-check": {**evidence, "source": "review", "exit_code": None},
        }
        run["evidence_log"] = [
            {"id": check_id, **item} for check_id, item in run["checks"].items()
        ]
        run["criteria"] = {
            "writes-owned-file": {
                "status": "pass",
                "evidence_digest": evidence_digest,
            }
        }
        run["state"] = "verifying"
        run["contract"]["state"] = "verifying"
        controller._add_history(run, "entered-verifying", "verifying")
        run["state"] = "reviewing"
        run["contract"]["state"] = "reviewing"
        controller._add_history(run, "entered-reviewing", "reviewing")
        run["state"] = "accepted"
        run["contract"]["state"] = "accepted"
        run["accepted_diff"] = {
            "diff_digest": diff_digest,
            "digest": controller._snapshot_digest(snapshot),
            "paths": paths,
            "snapshot": snapshot,
            "index_snapshot": index_snapshot,
            "index_digest": controller._snapshot_digest(index_snapshot),
        }
        controller._add_history(run, "accepted", "accepted")
        controller._write_json(context, run_path, run)

    def test_start_freezes_clean_baseline_and_acquires_codex_lease(self) -> None:
        result = self.harness(
            "codex-direct",
            "start",
            "--cwd",
            str(self.repo),
            str(self.contract_path),
        )

        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["schema"], "harness.codex-direct-control/v1")
        self.assertEqual(payload["task_id"], "pilot-30")
        self.assertEqual(payload["state"], "executing")
        self.assertEqual(payload["mode"], "codex-direct")
        self.assertEqual(payload["writer_lease"], {"holder": "codex", "state": "active"})
        self.assertEqual(git(self.repo, "status", "--short"), "")

    def test_start_without_manual_skill_reminds_once_and_does_not_start(self) -> None:
        contract = json.loads(self.contract_path.read_text(encoding="utf-8"))
        contract["required_manual_skills"][0] = {
            "name": "implement",
            "host": "codex",
            "status": "required",
        }
        self.contract_path.write_text(json.dumps(contract), encoding="utf-8")

        first = self.harness(
            "codex-direct", "start", "--cwd", str(self.repo), str(self.contract_path)
        )
        second = self.harness(
            "codex-direct", "start", "--cwd", str(self.repo), str(self.contract_path)
        )

        self.assertEqual(first.returncode, 3, first.stderr or first.stdout)
        self.assertEqual(second.returncode, 3, second.stderr or second.stdout)
        first_payload = json.loads(first.stdout)
        second_payload = json.loads(second.stdout)
        self.assertEqual(first_payload["state"], "awaiting-user")
        self.assertEqual(first_payload["manual_skill"]["status"], "reminder-emitted")
        self.assertEqual(second_payload["manual_skill"]["status"], "already-reminded")
        self.assertEqual(first_payload["writer_lease"]["state"], "inactive")
        self.assertFalse((self.repo / "harness-only.txt").exists())
        self.assertEqual(git(self.repo, "status", "--short"), "")

    def test_invalid_start_does_not_consume_the_manual_skill_reminder(self) -> None:
        contract = json.loads(self.contract_path.read_text(encoding="utf-8"))
        contract["required_manual_skills"][0] = {
            "name": "implement",
            "host": "codex",
            "status": "required",
        }
        valid_base = contract["execution"]["base_sha"]
        contract["execution"]["base_sha"] = "0" * 40
        self.contract_path.write_text(json.dumps(contract), encoding="utf-8")

        rejected = self.harness(
            "codex-direct", "start", "--cwd", str(self.repo), str(self.contract_path)
        )
        self.assertEqual(rejected.returncode, 2, rejected.stderr or rejected.stdout)
        self.assertFalse(
            (discover_worktree(self.repo).runtime_root / "manual-skill-reminders").exists()
        )

        contract["execution"]["base_sha"] = valid_base
        self.contract_path.write_text(json.dumps(contract), encoding="utf-8")
        reminded = self.harness(
            "codex-direct", "start", "--cwd", str(self.repo), str(self.contract_path)
        )
        self.assertEqual(reminded.returncode, 3, reminded.stderr or reminded.stdout)
        self.assertEqual(
            json.loads(reminded.stdout)["manual_skill"]["status"], "reminder-emitted"
        )

    def test_declared_contract_maxima_fit_loader_and_start(self) -> None:
        contract = json.loads(self.contract_path.read_text(encoding="utf-8"))
        contract["task"]["source"] = "界" * 1024
        contract["plan"]["objective"] = "界" * 2048
        contract["plan"]["owned_paths"] = [
            f"p{index:02}/{'界' * 124}" for index in range(32)
        ]
        contract["plan"]["acceptance_criteria"] = [
            {"id": f"criterion-{index}", "description": "界" * 256}
            for index in range(32)
        ]
        contract["plan"]["verification_plan"] = [
            {"id": f"check-{index}", "command": "界" * 512, "required": True}
            for index in range(32)
        ]
        contract["plan"]["stop_conditions"] = [
            f"{index:02}{'界' * 94}" for index in range(16)
        ]
        self.contract_path.write_text(json.dumps(contract), encoding="utf-8")
        self.assertLess(self.contract_path.stat().st_size, 256 * 1024)

        started = self.harness(
            "codex-direct", "start", "--cwd", str(self.repo), str(self.contract_path)
        )

        self.assertEqual(started.returncode, 0, started.stderr or started.stdout)

    def test_missing_skill_wrong_worktree_writes_no_reminder(self) -> None:
        linked = self.root / "linked"
        git(self.repo, "worktree", "add", "-b", "linked", str(linked))
        contract = json.loads(self.contract_path.read_text(encoding="utf-8"))
        contract["required_manual_skills"][0] = {
            "name": "implement",
            "host": "codex",
            "status": "required",
        }
        self.contract_path.write_text(json.dumps(contract), encoding="utf-8")

        result = self.harness(
            "codex-direct", "start", "--cwd", str(linked), str(self.contract_path)
        )

        self.assertEqual(result.returncode, 2, result.stderr or result.stdout)
        self.assertIn("canonical worktree", json.loads(result.stdout)["error"].lower())
        self.assertFalse(
            (discover_worktree(linked).runtime_root / "manual-skill-reminders").exists()
        )

    def test_linked_missing_skill_contracts_emit_one_reminder_total(self) -> None:
        linked = self.root / "linked"
        git(self.repo, "worktree", "add", "-b", "linked", str(linked))
        contract = json.loads(self.contract_path.read_text(encoding="utf-8"))
        contract["required_manual_skills"][0] = {
            "name": "implement",
            "host": "codex",
            "status": "required",
        }
        self.contract_path.write_text(json.dumps(contract), encoding="utf-8")
        linked_contract = self.root / "linked-contract.json"
        linked_value = json.loads(json.dumps(contract))
        linked_value["execution"].update(
            {
                "canonical_worktree": str(linked.resolve()),
                "base_sha": git(linked, "rev-parse", "HEAD"),
                "branch": "linked",
            }
        )
        linked_contract.write_text(json.dumps(linked_value), encoding="utf-8")

        calls = ((self.repo, self.contract_path), (linked, linked_contract))

        def start(call: tuple[Path, Path]) -> subprocess.CompletedProcess[str]:
            cwd, path = call
            return self.harness(
                "codex-direct", "start", "--cwd", str(cwd), str(path)
            )

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(start, calls))

        self.assertEqual([result.returncode for result in results], [3, 3])
        statuses = sorted(json.loads(result.stdout)["manual_skill"]["status"] for result in results)
        self.assertEqual(statuses, ["already-reminded", "reminder-emitted"])
        marker_dirs = [
            discover_worktree(root).runtime_root / "manual-skill-reminders"
            for root in (self.repo, linked)
        ]
        self.assertEqual(sum(path.exists() for path in marker_dirs), 1)

    def test_start_rejects_stale_or_dirty_baseline_before_writer_lease(self) -> None:
        contract = json.loads(self.contract_path.read_text(encoding="utf-8"))
        contract["execution"]["base_sha"] = "0" * 40
        self.contract_path.write_text(json.dumps(contract), encoding="utf-8")
        stale = self.harness(
            "codex-direct", "start", "--cwd", str(self.repo), str(self.contract_path)
        )
        self.assertEqual(stale.returncode, 2)
        self.assertIn("stale", json.loads(stale.stdout)["error"].lower())

        contract["execution"]["base_sha"] = git(self.repo, "rev-parse", "HEAD")
        self.contract_path.write_text(json.dumps(contract), encoding="utf-8")
        (self.repo / "README.md").write_text("pre-existing user change\n", encoding="utf-8")
        dirty = self.harness(
            "codex-direct", "start", "--cwd", str(self.repo), str(self.contract_path)
        )
        self.assertEqual(dirty.returncode, 2)
        self.assertIn("clean", json.loads(dirty.stdout)["error"].lower())

    def test_start_rejects_external_filters_without_invoking_them(self) -> None:
        (self.repo / ".gitattributes").write_text(
            "harness-only.txt filter=unsafe\n", encoding="utf-8"
        )
        git(self.repo, "add", ".gitattributes")
        git(self.repo, "commit", "-m", "declare filter")
        contract = json.loads(self.contract_path.read_text(encoding="utf-8"))
        contract["execution"]["base_sha"] = git(self.repo, "rev-parse", "HEAD")
        self.contract_path.write_text(json.dumps(contract), encoding="utf-8")
        git(
            self.repo,
            "config",
            "filter.unsafe.clean",
            "sh -c 'echo ran > filter-ran.txt; cat'",
        )
        git(self.repo, "config", "filter.unsafe.required", "true")

        result = self.harness(
            "codex-direct", "start", "--cwd", str(self.repo), str(self.contract_path)
        )

        self.assertEqual(result.returncode, 2, result.stderr or result.stdout)
        self.assertIn("external git filters", json.loads(result.stdout)["error"].lower())
        self.assertFalse((self.repo / "filter-ran.txt").exists())

    def test_diff_evidence_rejects_runtime_filter_without_invoking_it(self) -> None:
        contract = json.loads(self.contract_path.read_text(encoding="utf-8"))
        contract["plan"]["owned_paths"] = [".gitattributes", "owned/"]
        self.contract_path.write_text(json.dumps(contract), encoding="utf-8")
        marker = self.repo / "filter-ran.txt"
        git(
            self.repo,
            "config",
            "filter.unsafe.clean",
            "sh -c 'echo ran > filter-ran.txt; cat'",
        )
        git(self.repo, "config", "filter.unsafe.required", "true")
        started = self.harness(
            "codex-direct", "start", "--cwd", str(self.repo), str(self.contract_path)
        )
        self.assertEqual(started.returncode, 0, started.stderr or started.stdout)
        (self.repo / ".gitattributes").write_text(
            "owned/*.txt filter=unsafe\n", encoding="utf-8"
        )
        (self.repo / "owned").mkdir()
        (self.repo / "owned" / "x.txt").write_text("unsafe\n", encoding="utf-8")
        advanced = self.harness(
            "codex-direct",
            "advance",
            "--cwd",
            str(self.repo),
            "--task",
            "pilot-30",
            "--to",
            "verifying",
        )
        self.assertEqual(advanced.returncode, 0, advanced.stderr or advanced.stdout)

        result = self.harness(
            "codex-direct",
            "record-check",
            "--cwd",
            str(self.repo),
            "--task",
            "pilot-30",
            "--check",
            "owned-file-check",
            "--status",
            "pass",
            "--source",
            "command",
            "--exit-code",
            "0",
            "--sensitivity",
            "metadata",
            "--digest",
            hashlib.sha256(b"must-not-run-filter").hexdigest(),
        )

        self.assertEqual(result.returncode, 2, result.stderr or result.stdout)
        self.assertIn("external git filters", json.loads(result.stdout)["error"].lower())
        self.assertFalse(marker.exists())

    def test_ambiguous_filter_sentinel_is_rejected_without_invocation(self) -> None:
        (self.repo / ".gitattributes").write_text(
            "harness-only.txt filter=unset\n", encoding="utf-8"
        )
        git(self.repo, "add", ".gitattributes")
        git(self.repo, "commit", "-m", "configure ambiguous filter")
        self.write_contract()
        marker = self.repo / "filter-ran.txt"
        git(
            self.repo,
            "config",
            "filter.unset.clean",
            "sh -c 'echo ran > filter-ran.txt; cat'",
        )
        git(self.repo, "config", "filter.unset.required", "true")
        import harness.codex_direct as controller

        self.assertIn("unset", controller._configured_filter_drivers(self.repo))
        with self.assertRaises(controller.CodexDirectError):
            controller._reject_repository_filters(
                self.repo, ["harness-only.txt"]
            )

        result = self.harness(
            "codex-direct", "start", "--cwd", str(self.repo), str(self.contract_path)
        )

        self.assertEqual(result.returncode, 2, result.stderr or result.stdout)
        self.assertIn("external git filters", json.loads(result.stdout)["error"].lower())
        self.assertFalse(marker.exists())

    def test_concurrent_start_allows_only_one_codex_writer(self) -> None:
        def start(_: int) -> subprocess.CompletedProcess[str]:
            return self.harness(
                "codex-direct",
                "start",
                "--cwd",
                str(self.repo),
                str(self.contract_path),
            )

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(start, range(2)))

        self.assertEqual(sorted(result.returncode for result in results), [0, 2])
        rejection = next(result for result in results if result.returncode == 2)
        self.assertIn("writer lease", json.loads(rejection.stdout)["error"].lower())

    def test_replaced_repository_lock_rolls_back_writer_acquisition(self) -> None:
        import harness.codex_direct as controller

        context = discover_worktree(self.repo)
        contract = json.loads(self.contract_path.read_text(encoding="utf-8"))
        identity = controller._repository_lock_identity(context.common_git_dir / "config")
        changed = (*identity[:-1], identity[-1] + 1)
        with patch.object(
            controller,
            "_repository_lock_identity",
            side_effect=[identity, identity, changed],
        ):
            with self.assertRaisesRegex(controller.CodexDirectError, "changed during"):
                controller.start_codex_direct(context, contract)
        self.assertEqual(list(context.runtime_root.glob("tasks/*/run.json")), [])

    def test_frozen_canonical_worktree_rejects_second_linked_writer(self) -> None:
        linked = self.root / "linked"
        git(self.repo, "worktree", "add", "-b", "linked", str(linked))

        first = self.harness(
            "codex-direct", "start", "--cwd", str(self.repo), str(self.contract_path)
        )
        second = self.harness(
            "codex-direct", "start", "--cwd", str(linked), str(self.contract_path)
        )

        self.assertEqual(first.returncode, 0, first.stderr or first.stdout)
        self.assertEqual(second.returncode, 2, second.stderr or second.stdout)
        self.assertIn("canonical worktree", json.loads(second.stdout)["error"].lower())

    def test_concurrent_linked_contracts_allow_only_one_ticket_writer(self) -> None:
        linked = self.root / "linked"
        git(self.repo, "worktree", "add", "-b", "linked", str(linked))
        repository_metadata = discover_worktree(self.repo).common_git_dir / "config"
        metadata_before = repository_metadata.read_bytes()
        linked_contract = self.root / "linked-contract.json"
        contract = json.loads(self.contract_path.read_text(encoding="utf-8"))
        contract["execution"].update(
            {
                "canonical_worktree": str(linked.resolve()),
                "base_sha": git(linked, "rev-parse", "HEAD"),
                "branch": "linked",
            }
        )
        linked_contract.write_text(json.dumps(contract), encoding="utf-8")

        calls = (
            (self.repo, self.contract_path),
            (linked, linked_contract),
        )

        def start(call: tuple[Path, Path]) -> subprocess.CompletedProcess[str]:
            cwd, path = call
            return self.harness(
                "codex-direct", "start", "--cwd", str(cwd), str(path)
            )

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(start, calls))

        self.assertEqual(sorted(result.returncode for result in results), [0, 2])
        rejection = next(result for result in results if result.returncode == 2)
        self.assertIn("writer lease", json.loads(rejection.stdout)["error"].lower())
        active_runs = 0
        for root in (self.repo, linked):
            context = discover_worktree(root)
            active_runs += len(list((context.runtime_root / "tasks").glob("*/run.json")))
        self.assertEqual(active_runs, 1)
        self.assertEqual(repository_metadata.read_bytes(), metadata_before)

    def test_same_issue_source_with_different_task_ids_allows_only_one_writer(self) -> None:
        linked = self.root / "linked-alias"
        git(self.repo, "worktree", "add", "-b", "linked-alias", str(linked))
        linked_contract = self.root / "linked-alias-contract.json"
        contract = json.loads(self.contract_path.read_text(encoding="utf-8"))
        contract["task"]["id"] = "pilot-30-alias"
        contract["execution"].update(
            {
                "canonical_worktree": str(linked.resolve()),
                "base_sha": git(linked, "rev-parse", "HEAD"),
                "branch": "linked-alias",
            }
        )
        linked_contract.write_text(json.dumps(contract), encoding="utf-8")

        first = self.harness(
            "codex-direct", "start", "--cwd", str(self.repo), str(self.contract_path)
        )
        second = self.harness(
            "codex-direct", "start", "--cwd", str(linked), str(linked_contract)
        )

        self.assertEqual(first.returncode, 0, first.stderr or first.stdout)
        self.assertEqual(second.returncode, 2, second.stderr or second.stdout)
        self.assertIn("writer lease", json.loads(second.stdout)["error"].lower())

    def test_same_issue_source_with_whitespace_allows_only_one_writer(self) -> None:
        linked = self.root / "linked-source-whitespace"
        git(
            self.repo,
            "worktree",
            "add",
            "-b",
            "linked-source-whitespace",
            str(linked),
        )
        linked_contract = self.root / "linked-source-whitespace-contract.json"
        contract = json.loads(self.contract_path.read_text(encoding="utf-8"))
        contract["task"].update(
            {
                "id": "pilot-30-source-whitespace",
                "source": contract["task"]["source"] + " ",
            }
        )
        contract["execution"].update(
            {
                "canonical_worktree": str(linked.resolve()),
                "base_sha": git(linked, "rev-parse", "HEAD"),
                "branch": "linked-source-whitespace",
            }
        )
        linked_contract.write_text(json.dumps(contract), encoding="utf-8")

        first = self.harness(
            "codex-direct", "start", "--cwd", str(self.repo), str(self.contract_path)
        )
        second = self.harness(
            "codex-direct", "start", "--cwd", str(linked), str(linked_contract)
        )

        self.assertEqual(first.returncode, 0, first.stderr or first.stdout)
        self.assertEqual(second.returncode, 2, second.stderr or second.stdout)
        self.assertIn("writer lease", json.loads(second.stdout)["error"].lower())

    def test_malformed_sibling_task_state_fails_closed_before_second_writer(self) -> None:
        linked = self.root / "linked-malformed"
        git(self.repo, "worktree", "add", "-b", "linked-malformed", str(linked))
        linked_contract = self.root / "linked-malformed-contract.json"
        contract = json.loads(self.contract_path.read_text(encoding="utf-8"))
        contract["execution"].update(
            {
                "canonical_worktree": str(linked.resolve()),
                "base_sha": git(linked, "rev-parse", "HEAD"),
                "branch": "linked-malformed",
            }
        )
        linked_contract.write_text(json.dumps(contract), encoding="utf-8")
        first = self.harness(
            "codex-direct", "start", "--cwd", str(self.repo), str(self.contract_path)
        )
        self.assertEqual(first.returncode, 0, first.stderr or first.stdout)
        run_path = self.run_path()
        run = json.loads(run_path.read_text(encoding="utf-8"))
        run["contract"]["task"] = {}
        run_path.write_text(json.dumps(run), encoding="utf-8")

        second = self.harness(
            "codex-direct", "start", "--cwd", str(linked), str(linked_contract)
        )

        self.assertEqual(second.returncode, 2, second.stderr or second.stdout)
        self.assertIn("invalid task state", json.loads(second.stdout)["error"].lower())

    def test_runtime_state_is_metadata_only_and_rejects_existing_invalid_state(self) -> None:
        started = self.harness(
            "codex-direct", "start", "--cwd", str(self.repo), str(self.contract_path)
        )
        self.assertEqual(started.returncode, 0, started.stderr or started.stdout)
        persisted = self.run_path().read_text(encoding="utf-8")
        self.assertNotIn(str(self.repo.resolve()), persisted)
        self.assertNotIn("test -f harness-only.txt", persisted)
        self.assertNotIn("inspect the final diff", persisted)

        other = self.root / "other"
        other.mkdir()
        git(other, "init", "-b", "main")
        git(other, "config", "user.name", "Harness Test")
        git(other, "config", "user.email", "harness@example.invalid")
        (other / ".gitignore").write_text(".harness/\n", encoding="utf-8")
        git(other, "add", ".gitignore")
        git(other, "commit", "-m", "seed")
        contract = json.loads(self.contract_path.read_text(encoding="utf-8"))
        contract["task"]["id"] = "invalid-state-30"
        contract["execution"].update(
            {
                "canonical_worktree": str(other.resolve()),
                "base_sha": git(other, "rev-parse", "HEAD"),
            }
        )
        invalid_contract = self.root / "invalid-state-contract.json"
        invalid_contract.write_text(json.dumps(contract), encoding="utf-8")
        context = discover_worktree(other)
        task_dir = context.runtime_root / "tasks"
        task_dir.mkdir(parents=True)
        # The opaque task directory is deterministic but intentionally not exposed by the CLI.
        import harness.codex_direct as controller

        run_path = controller._task_dir(context, "invalid-state-30") / "run.json"
        run_path.parent.mkdir(parents=True)
        run_path.write_text("not-json", encoding="utf-8")

        rejected = self.harness(
            "codex-direct", "start", "--cwd", str(other), str(invalid_contract)
        )
        self.assertEqual(rejected.returncode, 2, rejected.stderr or rejected.stdout)
        self.assertIn("state", json.loads(rejected.stdout)["error"].lower())
        run_path.unlink()
        sentinel = self.root / "sentinel.json"
        sentinel.write_text('{"preserved":true}', encoding="utf-8")
        try:
            run_path.symlink_to(sentinel)
        except OSError:
            return
        linked = self.harness(
            "codex-direct", "start", "--cwd", str(other), str(invalid_contract)
        )
        self.assertEqual(linked.returncode, 2, linked.stderr or linked.stdout)
        self.assertEqual(sentinel.read_text(encoding="utf-8"), '{"preserved":true}')

    def test_state_limit_accepts_declared_maxima_and_rejects_before_overwrite(self) -> None:
        import harness.codex_direct as controller

        contract = json.loads(self.contract_path.read_text(encoding="utf-8"))
        contract["plan"]["verification_plan"] = [
            {"id": f"check-{index}", "command": "true", "required": True}
            for index in range(32)
        ]
        contract["plan"]["acceptance_criteria"] = [
            {"id": f"criterion-{index}", "description": "bounded criterion"}
            for index in range(32)
        ]
        self.contract_path.write_text(json.dumps(contract), encoding="utf-8")
        started = self.harness(
            "codex-direct", "start", "--cwd", str(self.repo), str(self.contract_path)
        )
        self.assertEqual(started.returncode, 0, started.stderr or started.stdout)
        context = discover_worktree(self.repo)
        run_path = self.run_path()
        run = json.loads(run_path.read_text(encoding="utf-8"))
        evidence = {
            "status": "pass",
            "source": "inspection",
            "exit_code": None,
            "sensitivity": "metadata",
            "digest": "a" * 64,
            "diff_digest": "b" * 64,
            "reason_code": None,
        }
        run["checks"] = {f"check-{index}": evidence for index in range(32)}
        run["evidence_log"] = [
            {"id": f"check-{index % 32}", **evidence} for index in range(384)
        ]
        run["criteria"] = {
            f"criterion-{index}": {"status": "pass", "evidence_digest": "a" * 64}
            for index in range(32)
        }
        run["history"] = [
            {"sequence": index, "event": "verification-recorded", "state": "reviewing"}
            for index in range(128)
        ]
        run["sequence"] = 127
        run["state"] = "reviewing"
        run["contract"]["state"] = "reviewing"
        risk = {"severity": "low", "status": "accepted", "digest": "c" * 64}
        run["risks"] = {f"risk-{index}": risk for index in range(128)}
        controller._write_json(context, run_path, run)
        _, loaded = controller._load_run(context, "pilot-30")
        self.assertEqual(len(loaded["checks"]), 32)
        self.assertEqual(len(loaded["criteria"]), 32)
        last_good = run_path.read_bytes()
        run["overflow"] = list(range(controller.MAX_STATE_NODES + 1))
        with self.assertRaises(controller.CodexDirectError):
            controller._write_json(context, run_path, run)
        self.assertEqual(run_path.read_bytes(), last_good)

    def test_runtime_validator_rejects_scope_history_and_bundle_tampering(self) -> None:
        started = self.harness(
            "codex-direct", "start", "--cwd", str(self.repo), str(self.contract_path)
        )
        self.assertEqual(started.returncode, 0, started.stderr or started.stdout)
        run_path = self.run_path()
        original = json.loads(run_path.read_text(encoding="utf-8"))

        tampered_scope = json.loads(json.dumps(original))
        tampered_scope["contract"]["plan"]["owned_paths"] = [".git/"]
        run_path.write_text(json.dumps(tampered_scope), encoding="utf-8")
        rejected = self.harness(
            "codex-direct", "status", "--cwd", str(self.repo), "--task", "pilot-30"
        )
        self.assertEqual(rejected.returncode, 2, rejected.stderr or rejected.stdout)

        tampered_history = json.loads(json.dumps(original))
        tampered_history["sequence"] = True
        tampered_history["history"][-1]["sequence"] = True
        run_path.write_text(json.dumps(tampered_history), encoding="utf-8")
        rejected = self.harness(
            "codex-direct", "status", "--cwd", str(self.repo), "--task", "pilot-30"
        )
        self.assertEqual(rejected.returncode, 2, rejected.stderr or rejected.stdout)

        run_path.write_text(json.dumps(original), encoding="utf-8")
        recovered = self.harness(
            "codex-direct", "recover", "--cwd", str(self.repo), "--task", "pilot-30",
            "--category", "adapter-failure", "--fingerprint", hashlib.sha256(b"tamper").hexdigest(),
        )
        self.assertEqual(recovered.returncode, 6, recovered.stderr or recovered.stdout)
        run = json.loads(run_path.read_text(encoding="utf-8"))
        bundle_path = run_path.parent / "recovery-bundle.json"
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        bundle["raw_command"] = "must-not-survive"
        encoded = json.dumps(
            bundle, ensure_ascii=True, sort_keys=True, separators=(",", ":")
        )
        bundle_path.write_text(encoded, encoding="utf-8")
        run["recovery_bundle"]["digest"] = hashlib.sha256(encoded.encode()).hexdigest()
        run_path.write_text(json.dumps(run), encoding="utf-8")

        rejected = self.harness(
            "codex-direct", "status", "--cwd", str(self.repo), "--task", "pilot-30"
        )
        self.assertEqual(rejected.returncode, 2, rejected.stderr or rejected.stdout)
        self.assertIn("recovery bundle", json.loads(rejected.stdout)["error"].lower())

    def test_risk_limit_preserves_recovery_bundle_capacity(self) -> None:
        import harness.codex_direct as controller

        started = self.harness(
            "codex-direct", "start", "--cwd", str(self.repo), str(self.contract_path)
        )
        self.assertEqual(started.returncode, 0, started.stderr or started.stdout)
        context = discover_worktree(self.repo)
        run_path = self.run_path()
        run = json.loads(run_path.read_text(encoding="utf-8"))
        run["state"] = "reviewing"
        run["contract"]["state"] = "reviewing"
        controller._add_history(run, "entered-verifying", "verifying")
        controller._add_history(run, "entered-reviewing", "reviewing")
        run["risks"] = {
            f"risk-{index}": {
                "severity": "low",
                "status": "accepted",
                "digest": hashlib.sha256(f"risk-{index}".encode()).hexdigest(),
            }
            for index in range(128)
        }
        controller._write_json(context, run_path, run)

        with self.assertRaisesRegex(controller.CodexDirectError, "risk limit"):
            controller.record_risk(
                context,
                task_id="pilot-30",
                risk_id="overflow-risk",
                severity="low",
                status="accepted",
                digest=hashlib.sha256(b"overflow-risk").hexdigest(),
            )
        result, exit_code = controller.enter_recovery(
            context,
            task_id="pilot-30",
            category="adapter-failure",
            fingerprint=hashlib.sha256(b"bounded-risk-recovery").hexdigest(),
        )
        self.assertEqual(exit_code, 6)
        self.assertEqual(len(result["recovery_bundle"]["risks"]), 128)

    def test_concurrent_review_updates_do_not_lose_risks(self) -> None:
        started = self.harness(
            "codex-direct", "start", "--cwd", str(self.repo), str(self.contract_path)
        )
        self.assertEqual(started.returncode, 0, started.stderr or started.stdout)
        (self.repo / "harness-only.txt").write_text("review\n", encoding="utf-8")
        for target in ("verifying", "reviewing"):
            advanced = self.harness(
                "codex-direct",
                "advance",
                "--cwd",
                str(self.repo),
                "--task",
                "pilot-30",
                "--to",
                target,
            )
            self.assertEqual(advanced.returncode, 0, advanced.stderr or advanced.stdout)

        def record(index: int) -> subprocess.CompletedProcess[str]:
            return self.harness(
                "codex-direct",
                "risk",
                "--cwd",
                str(self.repo),
                "--task",
                "pilot-30",
                "--risk",
                f"risk-{index}",
                "--severity",
                "low",
                "--status",
                "resolved",
                "--digest",
                hashlib.sha256(f"risk-{index}".encode()).hexdigest(),
            )

        with ThreadPoolExecutor(max_workers=12) as executor:
            results = list(executor.map(record, range(24)))
        self.assertTrue(all(result.returncode == 0 for result in results))
        status = self.harness(
            "codex-direct", "status", "--cwd", str(self.repo), "--task", "pilot-30"
        )
        self.assertEqual(status.returncode, 0, status.stderr or status.stdout)
        self.assertEqual(len(json.loads(status.stdout)["risks"]), 24)

    def test_guard_allows_ordinary_work_and_stops_protected_effects(self) -> None:
        started = self.harness(
            "codex-direct", "start", "--cwd", str(self.repo), str(self.contract_path)
        )
        self.assertEqual(started.returncode, 0, started.stderr or started.stdout)

        ordinary = (
            ("read", None),
            ("edit", "harness-only.txt"),
            ("build", None),
            ("test", None),
        )
        for action, path in ordinary:
            args = [
                "codex-direct",
                "guard",
                "--cwd",
                str(self.repo),
                "--task",
                "pilot-30",
                "--action",
                action,
            ]
            if path:
                args.extend(["--path", path])
            result = self.harness(*args)
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["decision"], "allowed")
            self.assertFalse(payload["requires_user"])

        unowned = self.harness(
            "codex-direct",
            "guard",
            "--cwd",
            str(self.repo),
            "--task",
            "pilot-30",
            "--action",
            "edit",
            "--path",
            "README.md",
        )
        self.assertEqual(unowned.returncode, 5)
        self.assertEqual(json.loads(unowned.stdout)["decision"], "blocked")

        for action in ("broad-delete", "history-rewrite", "credential", "ssh"):
            result = self.harness(
                "codex-direct",
                "guard",
                "--cwd",
                str(self.repo),
                "--task",
                "pilot-30",
                "--action",
                action,
            )
            self.assertEqual(result.returncode, 5, action)
            self.assertEqual(json.loads(result.stdout)["decision"], "blocked")

        for action in ("push", "pull-request", "tag", "release", "publish"):
            result = self.harness(
                "codex-direct",
                "guard",
                "--cwd",
                str(self.repo),
                "--task",
                "pilot-30",
                "--action",
                action,
            )
            self.assertEqual(result.returncode, 4, action)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["decision"], "user-authorization-required")
            self.assertTrue(payload["requires_user"])

        commit = self.harness(
            "codex-direct",
            "guard",
            "--cwd",
            str(self.repo),
            "--task",
            "pilot-30",
            "--action",
            "local-commit",
        )
        self.assertEqual(commit.returncode, 5)
        self.assertEqual(json.loads(commit.stdout)["decision"], "blocked")

    def test_edit_guard_rejects_owned_path_through_repository_link(self) -> None:
        contract = json.loads(self.contract_path.read_text(encoding="utf-8"))
        contract["plan"]["owned_paths"] = ["owned/"]
        self.contract_path.write_text(json.dumps(contract), encoding="utf-8")
        started = self.harness(
            "codex-direct", "start", "--cwd", str(self.repo), str(self.contract_path)
        )
        self.assertEqual(started.returncode, 0, started.stderr or started.stdout)
        outside = self.root / "outside"
        outside.mkdir()
        try:
            os.symlink(outside, self.repo / "owned", target_is_directory=True)
        except OSError as exc:
            self.skipTest(f"directory symlinks unavailable: {exc}")

        guarded = self.harness(
            "codex-direct", "guard", "--cwd", str(self.repo), "--task", "pilot-30",
            "--action", "edit", "--path", "owned/outside.txt",
        )

        self.assertEqual(guarded.returncode, 5, guarded.stderr or guarded.stdout)
        self.assertEqual(json.loads(guarded.stdout)["reason_code"], "unsafe-path-boundary")

    def test_edit_guard_rejects_owned_hard_link_to_external_file(self) -> None:
        started = self.harness(
            "codex-direct", "start", "--cwd", str(self.repo), str(self.contract_path)
        )
        self.assertEqual(started.returncode, 0, started.stderr or started.stdout)
        outside = self.root / "outside.txt"
        outside.write_text("outside\n", encoding="utf-8")
        os.link(outside, self.repo / "harness-only.txt")

        guarded = self.harness(
            "codex-direct", "guard", "--cwd", str(self.repo), "--task", "pilot-30",
            "--action", "edit", "--path", "harness-only.txt",
        )

        self.assertEqual(guarded.returncode, 5, guarded.stderr or guarded.stdout)
        self.assertEqual(json.loads(guarded.stdout)["reason_code"], "unsafe-path-boundary")

    def test_acceptance_requires_typed_checks_review_criteria_and_risks(self) -> None:
        start = self.harness(
            "codex-direct", "start", "--cwd", str(self.repo), str(self.contract_path)
        )
        self.assertEqual(start.returncode, 0, start.stderr or start.stdout)
        (self.repo / "harness-only.txt").write_text("bounded pilot\n", encoding="utf-8")

        verifying = self.harness(
            "codex-direct",
            "advance",
            "--cwd",
            str(self.repo),
            "--task",
            "pilot-30",
            "--to",
            "verifying",
        )
        self.assertEqual(verifying.returncode, 0, verifying.stderr or verifying.stdout)

        check_digest = hashlib.sha256(b"owned-file-check:pass").hexdigest()
        inconsistent = self.harness(
            "codex-direct",
            "record-check",
            "--cwd",
            str(self.repo),
            "--task",
            "pilot-30",
            "--check",
            "owned-file-check",
            "--status",
            "pass",
            "--source",
            "command",
            "--exit-code",
            "9",
            "--sensitivity",
            "metadata",
            "--digest",
            check_digest,
        )
        self.assertEqual(inconsistent.returncode, 2)
        check = self.harness(
            "codex-direct",
            "record-check",
            "--cwd",
            str(self.repo),
            "--task",
            "pilot-30",
            "--check",
            "owned-file-check",
            "--status",
            "pass",
            "--source",
            "command",
            "--exit-code",
            "0",
            "--sensitivity",
            "metadata",
            "--digest",
            check_digest,
        )
        self.assertEqual(check.returncode, 0, check.stderr or check.stdout)
        self.assertEqual(json.loads(check.stdout)["evidence"]["exit_code"], 0)
        skipped = self.harness(
            "codex-direct",
            "record-check",
            "--cwd",
            str(self.repo),
            "--task",
            "pilot-30",
            "--check",
            "optional-smoke",
            "--status",
            "skipped",
            "--source",
            "inspection",
            "--sensitivity",
            "metadata",
            "--digest",
            hashlib.sha256(b"optional-smoke:skipped").hexdigest(),
            "--reason-code",
            "not-required-for-pilot",
        )
        self.assertEqual(skipped.returncode, 0, skipped.stderr or skipped.stdout)

        reviewing = self.harness(
            "codex-direct",
            "advance",
            "--cwd",
            str(self.repo),
            "--task",
            "pilot-30",
            "--to",
            "reviewing",
        )
        self.assertEqual(reviewing.returncode, 0, reviewing.stderr or reviewing.stdout)
        premature = self.harness(
            "codex-direct", "accept", "--cwd", str(self.repo), "--task", "pilot-30"
        )
        self.assertEqual(premature.returncode, 2)

        review_digest = hashlib.sha256(b"review-check:pass").hexdigest()
        review = self.harness(
            "codex-direct",
            "record-check",
            "--cwd",
            str(self.repo),
            "--task",
            "pilot-30",
            "--check",
            "review-check",
            "--status",
            "pass",
            "--source",
            "review",
            "--sensitivity",
            "metadata",
            "--digest",
            review_digest,
        )
        self.assertEqual(review.returncode, 0, review.stderr or review.stdout)
        criterion = self.harness(
            "codex-direct",
            "judge",
            "--cwd",
            str(self.repo),
            "--task",
            "pilot-30",
            "--criterion",
            "writes-owned-file",
            "--status",
            "pass",
            "--evidence-digest",
            check_digest,
        )
        self.assertEqual(criterion.returncode, 0, criterion.stderr or criterion.stdout)
        risk = self.harness(
            "codex-direct",
            "risk",
            "--cwd",
            str(self.repo),
            "--task",
            "pilot-30",
            "--risk",
            "host-smoke-skipped",
            "--severity",
            "low",
            "--status",
            "accepted",
            "--digest",
            hashlib.sha256(b"host-smoke-skipped:accepted").hexdigest(),
        )
        self.assertEqual(risk.returncode, 0, risk.stderr or risk.stdout)

        (self.repo / "harness-only.txt").write_text(
            "bounded pilot changed after checks\n", encoding="utf-8"
        )
        stale = self.harness(
            "codex-direct", "accept", "--cwd", str(self.repo), "--task", "pilot-30"
        )
        self.assertEqual(stale.returncode, 2, stale.stderr or stale.stdout)
        self.assertIn("current diff", json.loads(stale.stdout)["error"].lower())
        for check_id, source, digest in (
            ("owned-file-check", "command", check_digest),
            ("review-check", "review", review_digest),
        ):
            args = [
                "codex-direct",
                "record-check",
                "--cwd",
                str(self.repo),
                "--task",
                "pilot-30",
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
                args.extend(["--exit-code", "0"])
            refreshed = self.harness(*args)
            self.assertEqual(refreshed.returncode, 0, refreshed.stderr or refreshed.stdout)
        accepted = self.harness(
            "codex-direct", "accept", "--cwd", str(self.repo), "--task", "pilot-30"
        )
        self.assertEqual(accepted.returncode, 0, accepted.stderr or accepted.stdout)
        payload = json.loads(accepted.stdout)
        self.assertEqual(payload["state"], "accepted")
        self.assertEqual(payload["writer_lease"]["state"], "released")
        self.assertEqual(payload["checks"]["optional-smoke"]["status"], "skipped")
        self.assertEqual(payload["commit_status"], "created")
        self.assertEqual(git(self.repo, "rev-list", "--count", "HEAD^..HEAD"), "1")
        self.assertEqual(git(self.repo, "status", "--short"), "")
        commit_guard = self.harness(
            "codex-direct",
            "guard",
            "--cwd",
            str(self.repo),
            "--task",
            "pilot-30",
            "--action",
            "local-commit",
        )
        self.assertEqual(commit_guard.returncode, 0, commit_guard.stderr or commit_guard.stdout)
        terminal_recovery = self.harness(
            "codex-direct",
            "recover",
            "--cwd",
            str(self.repo),
            "--task",
            "pilot-30",
            "--category",
            "adapter-failure",
            "--fingerprint",
            hashlib.sha256(b"after-success").hexdigest(),
        )
        self.assertEqual(
            terminal_recovery.returncode,
            2,
            terminal_recovery.stderr or terminal_recovery.stdout,
        )
        status = self.harness(
            "codex-direct", "status", "--cwd", str(self.repo), "--task", "pilot-30"
        )
        self.assertEqual(json.loads(status.stdout)["state"], "accepted")

    def test_uppercase_base_is_canonicalized_through_acceptance(self) -> None:
        contract = json.loads(self.contract_path.read_text(encoding="utf-8"))
        contract["execution"]["base_sha"] = contract["execution"]["base_sha"].upper()
        self.contract_path.write_text(json.dumps(contract), encoding="utf-8")
        self.prepare_reviewed_diff()

        accepted = self.harness(
            "codex-direct", "accept", "--cwd", str(self.repo), "--task", "pilot-30"
        )

        self.assertEqual(accepted.returncode, 0, accepted.stderr or accepted.stdout)
        self.assertEqual(json.loads(accepted.stdout)["commit_status"], "created")

    def test_acceptance_rejects_diff_above_recovery_safe_path_limit(self) -> None:
        contract = json.loads(self.contract_path.read_text(encoding="utf-8"))
        contract["plan"]["owned_paths"] = ["owned/"]
        self.contract_path.write_text(json.dumps(contract), encoding="utf-8")
        started = self.harness(
            "codex-direct", "start", "--cwd", str(self.repo), str(self.contract_path)
        )
        self.assertEqual(started.returncode, 0, started.stderr or started.stdout)
        owned = self.repo / "owned"
        owned.mkdir()
        for index in range(257):
            (owned / f"file-{index:03}.txt").write_text("bounded\n", encoding="utf-8")
        self.assertEqual(
            self.harness(
                "codex-direct",
                "advance",
                "--cwd",
                str(self.repo),
                "--task",
                "pilot-30",
                "--to",
                "verifying",
            ).returncode,
            0,
        )
        check_digest = hashlib.sha256(b"many-path-check").hexdigest()
        review_digest = hashlib.sha256(b"many-path-review").hexdigest()
        for check_id, source, digest in (
            ("owned-file-check", "command", check_digest),
            ("review-check", "review", review_digest),
        ):
            args = [
                "codex-direct",
                "record-check",
                "--cwd",
                str(self.repo),
                "--task",
                "pilot-30",
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
                args.extend(["--exit-code", "0"])
            self.assertEqual(self.harness(*args).returncode, 0)
        self.assertEqual(
            self.harness(
                "codex-direct",
                "advance",
                "--cwd",
                str(self.repo),
                "--task",
                "pilot-30",
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
                "pilot-30",
                "--criterion",
                "writes-owned-file",
                "--status",
                "pass",
                "--evidence-digest",
                check_digest,
            ).returncode,
            0,
        )

        accepted = self.harness(
            "codex-direct", "accept", "--cwd", str(self.repo), "--task", "pilot-30"
        )

        self.assertEqual(accepted.returncode, 2, accepted.stderr or accepted.stdout)
        self.assertIn("recovery-safe", json.loads(accepted.stdout)["error"].lower())

    def test_acceptance_path_budget_counts_utf8_bytes(self) -> None:
        import harness.codex_direct as controller

        paths = [f"{'a' * 500}/{index:02}.txt" for index in range(33)]
        self.assertLess(len(paths), controller.MAX_ACCEPTED_PATHS)
        with self.assertRaisesRegex(controller.CodexDirectError, "recovery-safe"):
            controller._require_recovery_safe_paths(paths)

    def test_untracked_executable_mode_is_part_of_current_diff_evidence(self) -> None:
        import harness.codex_direct as controller

        common = {"path": "script.sh", "kind": "file", "digest": "a" * 64}
        with (
            patch.object(controller, "_changed_paths", return_value=["script.sh"]),
            patch.object(controller, "_git_bytes", return_value=b""),
            patch.object(controller, "_git_paths", return_value=["script.sh"]),
            patch.object(
                controller,
                "_path_snapshot",
                side_effect=[
                    [{**common, "executable": False}],
                    [{**common, "executable": True}],
                ],
            ),
        ):
            before = controller._diff_digest(self.repo)
            after = controller._diff_digest(self.repo)
        self.assertNotEqual(before, after)

    def test_invalid_commit_message_cannot_partially_accept(self) -> None:
        self.prepare_reviewed_diff()
        base_sha = git(self.repo, "rev-parse", "HEAD")

        rejected = self.harness(
            "codex-direct",
            "accept",
            "--cwd",
            str(self.repo),
            "--task",
            "pilot-30",
            "--message",
            "   ",
        )

        self.assertEqual(rejected.returncode, 2, rejected.stderr or rejected.stdout)
        status = self.harness(
            "codex-direct", "status", "--cwd", str(self.repo), "--task", "pilot-30"
        )
        self.assertEqual(json.loads(status.stdout)["state"], "reviewing")
        self.assertEqual(git(self.repo, "rev-parse", "HEAD"), base_sha)

    def test_commit_message_rejects_process_boundary_characters(self) -> None:
        import harness.codex_direct as controller

        for message in ("bad\0message", "bad\ud800message", "bad\x7fmessage"):
            with self.subTest(message=repr(message)):
                with self.assertRaisesRegex(controller.CodexDirectError, "bounded single line"):
                    controller._require_commit_message(message)

    def test_acceptance_refuses_in_progress_git_operation_before_commit(self) -> None:
        self.prepare_reviewed_diff()
        base_sha = git(self.repo, "rev-parse", "HEAD")
        marker = Path(git(self.repo, "rev-parse", "--git-path", "MERGE_HEAD"))
        if not marker.is_absolute():
            marker = self.repo / marker
        marker.write_text(base_sha + "\n", encoding="ascii")

        rejected = self.harness(
            "codex-direct", "accept", "--cwd", str(self.repo), "--task", "pilot-30"
        )

        self.assertEqual(rejected.returncode, 2, rejected.stderr or rejected.stdout)
        self.assertIn("in-progress git", json.loads(rejected.stdout)["error"].lower())
        self.assertEqual(git(self.repo, "rev-parse", "HEAD"), base_sha)

    def test_persisted_accepted_state_cannot_bypass_review_evidence(self) -> None:
        started = self.harness(
            "codex-direct", "start", "--cwd", str(self.repo), str(self.contract_path)
        )
        self.assertEqual(started.returncode, 0, started.stderr or started.stdout)
        (self.repo / "harness-only.txt").write_text("tampered\n", encoding="utf-8")
        self.persist_accepted_fixture()
        run_path = self.run_path()
        run = json.loads(run_path.read_text(encoding="utf-8"))
        del run["checks"]["review-check"]
        run_path.write_text(json.dumps(run), encoding="utf-8")

        rejected = self.harness(
            "codex-direct", "commit", "--cwd", str(self.repo), "--task", "pilot-30",
            "--message", "test: reject forged acceptance",
        )

        self.assertEqual(rejected.returncode, 2, rejected.stderr or rejected.stdout)
        self.assertEqual(git(self.repo, "rev-parse", "HEAD"), run["baseline"]["head_sha"])

    def test_new_check_evidence_invalidates_dependent_criterion_without_bricking_state(self) -> None:
        self.prepare_reviewed_diff()
        replacement = hashlib.sha256(b"replacement-check-evidence").hexdigest()

        updated = self.harness(
            "codex-direct", "record-check", "--cwd", str(self.repo), "--task", "pilot-30",
            "--check", "owned-file-check", "--status", "pass", "--source", "command",
            "--exit-code", "0", "--sensitivity", "metadata", "--digest", replacement,
        )
        self.assertEqual(updated.returncode, 0, updated.stderr or updated.stdout)
        status = self.harness(
            "codex-direct", "status", "--cwd", str(self.repo), "--task", "pilot-30"
        )
        self.assertEqual(status.returncode, 0, status.stderr or status.stdout)
        self.assertNotIn("writes-owned-file", json.loads(status.stdout)["criteria"])

        blocked = self.harness(
            "codex-direct", "accept", "--cwd", str(self.repo), "--task", "pilot-30"
        )
        self.assertEqual(blocked.returncode, 2, blocked.stderr or blocked.stdout)
        rejudged = self.harness(
            "codex-direct", "judge", "--cwd", str(self.repo), "--task", "pilot-30",
            "--criterion", "writes-owned-file", "--status", "pass",
            "--evidence-digest", replacement,
        )
        self.assertEqual(rejudged.returncode, 0, rejudged.stderr or rejudged.stdout)
        accepted = self.harness(
            "codex-direct", "accept", "--cwd", str(self.repo), "--task", "pilot-30"
        )
        self.assertEqual(accepted.returncode, 0, accepted.stderr or accepted.stdout)

    def test_repeated_failure_without_progress_stops_with_recovery_bundle(self) -> None:
        start = self.harness(
            "codex-direct", "start", "--cwd", str(self.repo), str(self.contract_path)
        )
        self.assertEqual(start.returncode, 0, start.stderr or start.stdout)
        (self.repo / "harness-only.txt").write_text("broken\n", encoding="utf-8")
        verifying = self.harness(
            "codex-direct",
            "advance",
            "--cwd",
            str(self.repo),
            "--task",
            "pilot-30",
            "--to",
            "verifying",
        )
        self.assertEqual(verifying.returncode, 0, verifying.stderr or verifying.stdout)
        failed = self.harness(
            "codex-direct",
            "record-check",
            "--cwd",
            str(self.repo),
            "--task",
            "pilot-30",
            "--check",
            "owned-file-check",
            "--status",
            "fail",
            "--source",
            "command",
            "--exit-code",
            "1",
            "--sensitivity",
            "metadata",
            "--digest",
            hashlib.sha256(b"same-failure-evidence").hexdigest(),
        )
        self.assertEqual(failed.returncode, 0, failed.stderr or failed.stdout)
        fingerprint = hashlib.sha256(b"same-failure").hexdigest()

        first = self.harness(
            "codex-direct",
            "repair",
            "--cwd",
            str(self.repo),
            "--task",
            "pilot-30",
            "--fingerprint",
            fingerprint,
        )
        self.assertEqual(first.returncode, 0, first.stderr or first.stdout)
        self.assertEqual(json.loads(first.stdout)["state"], "repairing")
        self.assertEqual(json.loads(first.stdout)["repair_attempt"], 1)
        again = self.harness(
            "codex-direct",
            "advance",
            "--cwd",
            str(self.repo),
            "--task",
            "pilot-30",
            "--to",
            "verifying",
        )
        self.assertEqual(again.returncode, 0, again.stderr or again.stdout)
        stopped = self.harness(
            "codex-direct",
            "repair",
            "--cwd",
            str(self.repo),
            "--task",
            "pilot-30",
            "--fingerprint",
            fingerprint,
        )

        self.assertEqual(stopped.returncode, 6, stopped.stderr or stopped.stdout)
        payload = json.loads(stopped.stdout)
        self.assertEqual(payload["state"], "recovery-required")
        bundle = payload["recovery_bundle"]
        self.assertEqual(bundle["schema"], "harness.recovery-bundle/v1")
        self.assertEqual(bundle["failure"]["category"], "repeated-failure")
        self.assertEqual(bundle["failure"]["fingerprint"], fingerprint)
        self.assertEqual(bundle["mode"], "codex-direct")
        self.assertEqual(bundle["adapter_switch_policy"], "stop-and-report")
        self.assertEqual(bundle["writer_lease"], {"holder": "codex", "state": "active"})
        self.assertEqual(bundle["owned_paths"], ["harness-only.txt"])
        self.assertEqual(bundle["changed_paths"], ["harness-only.txt"])
        self.assertEqual(bundle["incomplete_criteria"], ["writes-owned-file"])
        self.assertEqual(bundle["validations"][0]["status"], "fail")
        self.assertEqual(len(bundle["diff_digest"]), 64)

    def test_recovery_bundle_preserves_superseded_negative_evidence(self) -> None:
        started = self.harness(
            "codex-direct", "start", "--cwd", str(self.repo), str(self.contract_path)
        )
        self.assertEqual(started.returncode, 0, started.stderr or started.stdout)
        (self.repo / "harness-only.txt").write_text("evidence\n", encoding="utf-8")
        self.assertEqual(
            self.harness(
                "codex-direct", "advance", "--cwd", str(self.repo), "--task", "pilot-30",
                "--to", "verifying",
            ).returncode,
            0,
        )
        for status, exit_code in (("fail", "1"), ("pass", "0")):
            recorded = self.harness(
                "codex-direct", "record-check", "--cwd", str(self.repo), "--task", "pilot-30",
                "--check", "owned-file-check", "--status", status, "--source", "command",
                "--exit-code", exit_code, "--sensitivity", "metadata", "--digest",
                hashlib.sha256(status.encode()).hexdigest(),
            )
            self.assertEqual(recorded.returncode, 0, recorded.stderr or recorded.stdout)
        recovered = self.harness(
            "codex-direct", "recover", "--cwd", str(self.repo), "--task", "pilot-30",
            "--category", "adapter-failure", "--fingerprint",
            hashlib.sha256(b"evidence-recovery").hexdigest(),
        )
        self.assertEqual(recovered.returncode, 6, recovered.stderr or recovered.stdout)
        validations = json.loads(recovered.stdout)["recovery_bundle"]["validations"]
        self.assertEqual([item["status"] for item in validations], ["fail", "pass"])

    def test_unsorted_contract_owned_paths_produce_canonical_recovery_evidence(self) -> None:
        contract = json.loads(self.contract_path.read_text(encoding="utf-8"))
        contract["plan"]["owned_paths"] = ["z-last.txt", "harness-only.txt"]
        self.contract_path.write_text(json.dumps(contract), encoding="utf-8")
        started = self.harness(
            "codex-direct", "start", "--cwd", str(self.repo), str(self.contract_path)
        )
        self.assertEqual(started.returncode, 0, started.stderr or started.stdout)

        recovered = self.harness(
            "codex-direct", "recover", "--cwd", str(self.repo), "--task", "pilot-30",
            "--category", "adapter-failure", "--fingerprint",
            hashlib.sha256(b"canonical-owned-paths").hexdigest(),
        )
        self.assertEqual(recovered.returncode, 6, recovered.stderr or recovered.stdout)
        self.assertEqual(
            json.loads(recovered.stdout)["recovery_bundle"]["owned_paths"],
            ["harness-only.txt", "z-last.txt"],
        )
        status = self.harness(
            "codex-direct", "status", "--cwd", str(self.repo), "--task", "pilot-30"
        )
        self.assertEqual(status.returncode, 0, status.stderr or status.stdout)

    def test_new_evidence_prevents_false_repeated_failure_after_latest_value_returns(self) -> None:
        started = self.harness(
            "codex-direct", "start", "--cwd", str(self.repo), str(self.contract_path)
        )
        self.assertEqual(started.returncode, 0, started.stderr or started.stdout)
        (self.repo / "harness-only.txt").write_text("broken\n", encoding="utf-8")
        self.assertEqual(
            self.harness(
                "codex-direct", "advance", "--cwd", str(self.repo), "--task", "pilot-30",
                "--to", "verifying",
            ).returncode,
            0,
        )
        fingerprint = hashlib.sha256(b"stable-failure").hexdigest()

        def record(digest_seed: bytes) -> None:
            result = self.harness(
                "codex-direct", "record-check", "--cwd", str(self.repo), "--task", "pilot-30",
                "--check", "owned-file-check", "--status", "fail", "--source", "command",
                "--exit-code", "1", "--sensitivity", "metadata", "--digest",
                hashlib.sha256(digest_seed).hexdigest(),
            )
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

        record(b"evidence-a")
        first = self.harness(
            "codex-direct", "repair", "--cwd", str(self.repo), "--task", "pilot-30",
            "--fingerprint", fingerprint,
        )
        self.assertEqual(first.returncode, 0, first.stderr or first.stdout)
        self.assertEqual(
            self.harness(
                "codex-direct", "advance", "--cwd", str(self.repo), "--task", "pilot-30",
                "--to", "verifying",
            ).returncode,
            0,
        )
        record(b"evidence-b")
        record(b"evidence-a")
        second = self.harness(
            "codex-direct", "repair", "--cwd", str(self.repo), "--task", "pilot-30",
            "--fingerprint", fingerprint,
        )
        self.assertEqual(second.returncode, 0, second.stderr or second.stdout)
        self.assertEqual(json.loads(second.stdout)["repair_attempt"], 2)

    def test_adapter_failure_stops_without_switching_or_releasing_lease(self) -> None:
        start = self.harness(
            "codex-direct", "start", "--cwd", str(self.repo), str(self.contract_path)
        )
        self.assertEqual(start.returncode, 0, start.stderr or start.stdout)
        fingerprint = hashlib.sha256(b"adapter-failure").hexdigest()
        recovered = self.harness(
            "codex-direct",
            "recover",
            "--cwd",
            str(self.repo),
            "--task",
            "pilot-30",
            "--category",
            "adapter-failure",
            "--fingerprint",
            fingerprint,
        )

        self.assertEqual(recovered.returncode, 6, recovered.stderr or recovered.stdout)
        bundle = json.loads(recovered.stdout)["recovery_bundle"]
        self.assertEqual(bundle["failure"]["category"], "adapter-failure")
        self.assertEqual(bundle["mode"], "codex-direct")
        self.assertEqual(bundle["writer_lease"]["state"], "active")
        self.assertNotIn("fallback", json.dumps(bundle).lower())

    def test_large_preaccept_diff_writes_bounded_external_recovery_bundle(self) -> None:
        contract = json.loads(self.contract_path.read_text(encoding="utf-8"))
        contract["plan"]["owned_paths"] = ["owned/"]
        self.contract_path.write_text(json.dumps(contract), encoding="utf-8")
        started = self.harness(
            "codex-direct", "start", "--cwd", str(self.repo), str(self.contract_path)
        )
        self.assertEqual(started.returncode, 0, started.stderr or started.stdout)
        owned = self.repo / "owned"
        owned.mkdir()
        for index in range(257):
            (owned / f"file-{index:03}.txt").write_text("bounded\n", encoding="utf-8")

        recovered = self.harness(
            "codex-direct",
            "recover",
            "--cwd",
            str(self.repo),
            "--task",
            "pilot-30",
            "--category",
            "adapter-failure",
            "--fingerprint",
            hashlib.sha256(b"large-preaccept-diff").hexdigest(),
        )

        self.assertEqual(recovered.returncode, 6, recovered.stderr or recovered.stdout)
        bundle = json.loads(recovered.stdout)["recovery_bundle"]
        self.assertEqual(bundle["changed_path_count"], 257)
        self.assertFalse(bundle["changed_paths_embedded"])
        self.assertEqual(bundle["changed_paths"], [])
        self.assertEqual(len(bundle["changed_paths_digest"]), 64)
        run = json.loads(self.run_path().read_text(encoding="utf-8"))
        self.assertEqual(
            run["recovery_bundle"]["schema"], "harness.recovery-bundle-ref/v1"
        )
        status = self.harness(
            "codex-direct", "status", "--cwd", str(self.repo), "--task", "pilot-30"
        )
        self.assertEqual(
            json.loads(status.stdout)["recovery_bundle"]["changed_path_count"], 257
        )

    def test_recovery_records_staged_only_diff_and_index_paths(self) -> None:
        started = self.harness(
            "codex-direct", "start", "--cwd", str(self.repo), str(self.contract_path)
        )
        self.assertEqual(started.returncode, 0, started.stderr or started.stdout)
        (self.repo / "harness-only.txt").write_text("staged\n", encoding="utf-8")
        git(self.repo, "add", "--", "harness-only.txt")

        recovered = self.harness(
            "codex-direct",
            "recover",
            "--cwd",
            str(self.repo),
            "--task",
            "pilot-30",
            "--category",
            "adapter-failure",
            "--fingerprint",
            hashlib.sha256(b"staged-recovery").hexdigest(),
        )

        self.assertEqual(recovered.returncode, 6, recovered.stderr or recovered.stdout)
        bundle = json.loads(recovered.stdout)["recovery_bundle"]
        self.assertEqual(bundle["changed_paths"], ["harness-only.txt"])
        self.assertEqual(bundle["staged_paths"], ["harness-only.txt"])
        self.assertEqual(bundle["staged_path_count"], 1)
        self.assertNotEqual(bundle["diff_digest"], hashlib.sha256(b"").hexdigest())

    def test_recovery_bundle_survives_persistent_git_inspection_failure(self) -> None:
        import harness.codex_direct as controller

        started = self.harness(
            "codex-direct", "start", "--cwd", str(self.repo), str(self.contract_path)
        )
        self.assertEqual(started.returncode, 0, started.stderr or started.stdout)
        context = discover_worktree(self.repo)
        with patch.object(
            controller,
            "_changed_paths",
            side_effect=controller.CodexDirectAdapterError("git unavailable"),
        ):
            result, exit_code = controller.enter_recovery(
                context,
                task_id="pilot-30",
                category="adapter-failure",
                fingerprint=hashlib.sha256(b"persistent-git-failure").hexdigest(),
            )
        self.assertEqual(exit_code, 6)
        bundle = result["recovery_bundle"]
        self.assertEqual(bundle["repository_inspection"], "unavailable")
        self.assertIsNone(bundle["head_sha"])
        self.assertIsNone(bundle["diff_digest"])
        self.assertEqual(json.loads(self.run_path().read_text())["state"], "recovery-required")

    def test_recovery_bundle_survives_bounded_snapshot_rejection(self) -> None:
        import harness.codex_direct as controller

        started = self.harness(
            "codex-direct", "start", "--cwd", str(self.repo), str(self.contract_path)
        )
        self.assertEqual(started.returncode, 0, started.stderr or started.stdout)
        context = discover_worktree(self.repo)
        with patch.object(
            controller,
            "_changed_paths",
            side_effect=controller.CodexDirectError("snapshot exceeds bound"),
        ):
            result, exit_code = controller.enter_recovery(
                context,
                task_id="pilot-30",
                category="adapter-failure",
                fingerprint=hashlib.sha256(b"bounded-snapshot").hexdigest(),
            )
        self.assertEqual(exit_code, 6)
        self.assertEqual(result["recovery_bundle"]["repository_inspection"], "unavailable")

    def test_partial_precommit_index_is_rebuilt_before_crash_resume(self) -> None:
        import harness.codex_direct as controller

        contract = json.loads(self.contract_path.read_text(encoding="utf-8"))
        contract["plan"]["owned_paths"] = ["owned/"]
        self.contract_path.write_text(json.dumps(contract), encoding="utf-8")
        started = self.harness(
            "codex-direct", "start", "--cwd", str(self.repo), str(self.contract_path)
        )
        self.assertEqual(started.returncode, 0, started.stderr or started.stdout)
        owned = self.repo / "owned"
        owned.mkdir()
        (owned / "a.txt").write_text("a\n", encoding="utf-8")
        (owned / "b.txt").write_text("b\n", encoding="utf-8")
        self.persist_accepted_fixture()
        git(self.repo, "add", "--", "owned/a.txt")
        git(self.repo, "update-index", "--chmod=+x", "owned/a.txt")

        resumed = self.harness(
            "codex-direct",
            "commit",
            "--cwd",
            str(self.repo),
            "--task",
            "pilot-30",
            "--message",
            "test: resume accepted commit",
        )

        self.assertEqual(resumed.returncode, 0, resumed.stderr or resumed.stdout)
        self.assertEqual(json.loads(resumed.stdout)["commit_status"], "created")
        self.assertEqual(
            git(self.repo, "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD").splitlines(),
            ["owned/a.txt", "owned/b.txt"],
        )
        self.assertTrue(git(self.repo, "ls-tree", "HEAD", "owned/a.txt").startswith("100644"))

    def test_saved_exact_index_snapshot_resumes_commit_after_crash(self) -> None:
        import harness.codex_direct as controller

        started = self.harness(
            "codex-direct", "start", "--cwd", str(self.repo), str(self.contract_path)
        )
        self.assertEqual(started.returncode, 0, started.stderr or started.stdout)
        (self.repo / "harness-only.txt").write_text("resume\n", encoding="utf-8")
        self.persist_accepted_fixture()
        git(self.repo, "add", "--", "harness-only.txt")
        context = discover_worktree(self.repo)
        run_path = self.run_path()
        run = json.loads(run_path.read_text(encoding="utf-8"))
        index_snapshot = controller._index_snapshot(self.repo, ["harness-only.txt"])
        run["accepted_diff"]["index_snapshot"] = index_snapshot
        run["accepted_diff"]["index_digest"] = controller._snapshot_digest(index_snapshot)
        controller._write_json(context, run_path, run)

        resumed = self.harness(
            "codex-direct",
            "commit",
            "--cwd",
            str(self.repo),
            "--task",
            "pilot-30",
            "--message",
            "test: resume saved index commit",
        )

        self.assertEqual(resumed.returncode, 0, resumed.stderr or resumed.stdout)
        self.assertEqual(json.loads(resumed.stdout)["commit_status"], "created")

    def test_commit_recovers_when_index_install_fails_after_ref_update(self) -> None:
        import harness.codex_direct as controller

        self.assertEqual(
            self.harness(
                "codex-direct", "start", "--cwd", str(self.repo), str(self.contract_path)
            ).returncode,
            0,
        )
        (self.repo / "harness-only.txt").write_text("accepted\n", encoding="utf-8")
        self.persist_accepted_fixture()
        context = discover_worktree(self.repo)
        original_replace = controller.os.replace
        failed = False

        def fail_index_install(
            source: object, target: object, *args: object, **kwargs: object
        ) -> None:
            nonlocal failed
            if not failed and Path(source).name == "index.lock":
                failed = True
                raise OSError("simulated post-ref index install failure")
            original_replace(source, target, *args, **kwargs)

        with patch.object(controller.os, "replace", side_effect=fail_index_install):
            with self.assertRaises(controller.CodexDirectAdapterError):
                controller._commit_unlocked(
                    context,
                    task_id="pilot-30",
                    message="test: recover exact post-ref commit",
                )
        self.assertTrue(failed)

        recovered = controller._commit_unlocked(
            context,
            task_id="pilot-30",
            message="test: recover exact post-ref commit",
        )
        self.assertEqual(recovered["commit_status"], "already-committed")
        self.assertEqual(git(self.repo, "status", "--porcelain=v1"), "")
        self.assertEqual(
            git(self.repo, "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"),
            "harness-only.txt",
        )

    @unittest.skipIf(os.name == "nt", "directory-relative descriptors are POSIX-only")
    def test_index_lock_rejects_git_directory_swap_before_open(self) -> None:
        import harness.codex_direct as controller

        context = discover_worktree(self.repo)
        displaced = self.root / "git-displaced"
        external = self.root / "external-git"
        external.mkdir()
        external_index = external / "index"
        external_index.write_bytes(b"external-index")
        real_open = controller.os.open
        swapped = False

        def raced_open(
            candidate: os.PathLike[str] | str | bytes,
            flags: int,
            mode: int = 0o777,
            *,
            dir_fd: int | None = None,
        ) -> int:
            nonlocal swapped
            if (
                not swapped
                and dir_fd is not None
                and Path(candidate).name == "index.lock"
            ):
                context.git_dir.rename(displaced)
                context.git_dir.symlink_to(external, target_is_directory=True)
                swapped = True
            if dir_fd is None:
                return real_open(candidate, flags, mode)
            return real_open(candidate, flags, mode, dir_fd=dir_fd)

        try:
            with patch.object(controller.os, "open", new=raced_open):
                with self.assertRaises(controller.CodexDirectAdapterError):
                    with controller._open_index_lock(context):
                        pass
            self.assertTrue(swapped)
            self.assertEqual(external_index.read_bytes(), b"external-index")
            self.assertFalse((external / "index.lock").exists())
        finally:
            if context.git_dir.is_symlink():
                context.git_dir.unlink()
            if displaced.exists():
                displaced.rename(context.git_dir)

    def test_automatic_commit_adapter_failure_writes_recovery_bundle(self) -> None:
        self.prepare_reviewed_diff()
        index_lock = Path(git(self.repo, "rev-parse", "--git-path", "index.lock"))
        if not index_lock.is_absolute():
            index_lock = self.repo / index_lock
        index_lock.write_text("held by test", encoding="utf-8")

        failed = self.harness(
            "codex-direct", "accept", "--cwd", str(self.repo), "--task", "pilot-30"
        )

        self.assertEqual(failed.returncode, 6, failed.stderr or failed.stdout)
        payload = json.loads(failed.stdout)
        self.assertEqual(payload["state"], "recovery-required")
        bundle = payload["recovery_bundle"]
        self.assertEqual(bundle["failure"]["category"], "adapter-failure")
        self.assertEqual(bundle["writer_lease"]["state"], "active")
        self.assertEqual(bundle["changed_paths"], ["harness-only.txt"])
        self.assertNotIn("fallback", json.dumps(bundle).lower())

    def test_automatic_commit_disables_hooks_and_signing(self) -> None:
        self.prepare_reviewed_diff()
        hook_dir = Path(git(self.repo, "rev-parse", "--git-path", "hooks"))
        if not hook_dir.is_absolute():
            hook_dir = self.repo / hook_dir
        pre_commit = hook_dir / "pre-commit"
        pre_commit.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
        post_commit = hook_dir / "post-commit"
        marker = self.repo / "hook-ran.txt"
        post_commit.write_text(
            f"#!/bin/sh\nprintf ran > '{marker.as_posix()}'\n", encoding="utf-8"
        )
        os.chmod(pre_commit, 0o755)
        os.chmod(post_commit, 0o755)
        git(self.repo, "config", "commit.gpgSign", "true")
        git(self.repo, "config", "core.commentChar", "H")

        accepted = self.harness(
            "codex-direct", "accept", "--cwd", str(self.repo), "--task", "pilot-30"
        )

        self.assertEqual(accepted.returncode, 0, accepted.stderr or accepted.stdout)
        payload = json.loads(accepted.stdout)
        self.assertEqual(payload["commit_status"], "created")
        self.assertEqual(payload["writer_lease"]["state"], "released")
        self.assertFalse(marker.exists())
        self.assertTrue(
            any(
                line.startswith("Harness-Task:")
                for line in git(self.repo, "log", "-1", "--format=%B").splitlines()
            )
        )
        self.assertEqual(git(self.repo, "status", "--short"), "")

    def test_late_filter_mutation_never_executes_during_accepted_commit(self) -> None:
        (self.repo / ".gitattributes").write_text("", encoding="utf-8")
        git(self.repo, "add", ".gitattributes")
        git(self.repo, "commit", "-m", "track attributes")
        self.write_contract()
        self.prepare_reviewed_diff()
        import harness.codex_direct as controller

        marker = self.repo / "filter-ran.txt"
        original = controller._run_git_bytes
        injected = False

        def race(root: Path, args: tuple[str, ...], *pos: object, **kwargs: object) -> bytes:
            nonlocal injected
            if not injected and "add" in args:
                injected = True
                (self.repo / ".gitattributes").write_text(
                    "harness-only.txt filter=late\n", encoding="utf-8"
                )
                git(
                    self.repo, "config", "filter.late.clean",
                    "sh -c 'echo ran > filter-ran.txt; cat'",
                )
                git(self.repo, "config", "filter.late.required", "true")
            return original(root, args, *pos, **kwargs)

        with patch.object(controller, "_run_git_bytes", side_effect=race):
            with self.assertRaises(controller.CodexDirectError):
                controller.accept_codex_direct(
                    discover_worktree(self.repo), task_id="pilot-30",
                    message="test: reject late filter race",
                )
        self.assertTrue(injected)
        self.assertFalse(marker.exists())

    def test_concurrent_real_index_stage_cannot_enter_accepted_commit(self) -> None:
        self.prepare_reviewed_diff()
        import harness.codex_direct as controller

        base_sha = git(self.repo, "rev-parse", "HEAD")
        original = controller._run_git_bytes
        injected = False

        def race(root: Path, args: tuple[str, ...], *pos: object, **kwargs: object) -> bytes:
            nonlocal injected
            if not injected and any(item in {"commit", "commit-tree"} for item in args):
                injected = True
                (self.repo / "README.md").write_text("concurrent writer\n", encoding="utf-8")
                try:
                    git(self.repo, "add", "README.md")
                except subprocess.CalledProcessError:
                    pass
            return original(root, args, *pos, **kwargs)

        with patch.object(controller, "_run_git_bytes", side_effect=race):
            try:
                controller.accept_codex_direct(
                    discover_worktree(self.repo), task_id="pilot-30",
                    message="test: isolate accepted tree",
                )
            except controller.CodexDirectError:
                pass
        self.assertTrue(injected)
        head = git(self.repo, "rev-parse", "HEAD")
        if head != base_sha:
            self.assertEqual(controller._commit_paths(self.repo, head), ["harness-only.txt"])

    def test_automatic_commit_preserves_builtin_crlf_normalization(self) -> None:
        git(self.repo, "config", "core.autocrlf", "true")
        self.prepare_reviewed_diff(content=b"accepted\r\n")
        accepted = self.harness(
            "codex-direct", "accept", "--cwd", str(self.repo), "--task", "pilot-30",
            "--message", "test: preserve repository eol semantics",
        )

        self.assertEqual(accepted.returncode, 0, accepted.stderr or accepted.stdout)
        blob = subprocess.run(
            ["git", "-C", str(self.repo), "cat-file", "blob", "HEAD:harness-only.txt"],
            check=True,
            capture_output=True,
        ).stdout
        self.assertEqual(blob, b"accepted\n")
        self.assertEqual((self.repo / "harness-only.txt").read_bytes(), b"accepted\r\n")
        self.assertEqual(git(self.repo, "status", "--porcelain=v1"), "")

    def test_canonical_probe_does_not_write_git_objects_or_temp_payloads(self) -> None:
        import harness.codex_direct as controller

        (self.repo / "harness-only.txt").write_text("probe\n", encoding="utf-8")
        before = git(self.repo, "count-objects", "-v")
        snapshot = controller._canonical_index_snapshot(
            discover_worktree(self.repo), ["harness-only.txt"]
        )
        after = git(self.repo, "count-objects", "-v")

        self.assertEqual(len(snapshot), 1)
        self.assertEqual(before, after)

    def test_core_symlinks_false_preserves_tracked_symlink_mode(self) -> None:
        git(self.repo, "config", "core.symlinks", "false")
        git(self.repo, "config", "core.autocrlf", "true")
        owned = self.repo / "harness-only.txt"
        owned.write_text("old-target", encoding="utf-8")
        object_id = git(self.repo, "hash-object", "-w", "--", "harness-only.txt")
        git(
            self.repo,
            "update-index",
            "--add",
            "--cacheinfo",
            f"120000,{object_id},harness-only.txt",
        )
        git(self.repo, "commit", "-m", "track symlink with emulated checkout")
        self.write_contract()
        self.prepare_reviewed_diff(content=b"accepted\r\n")

        accepted = self.harness(
            "codex-direct", "accept", "--cwd", str(self.repo), "--task", "pilot-30"
        )

        self.assertEqual(accepted.returncode, 0, accepted.stderr or accepted.stdout)
        self.assertTrue(git(self.repo, "ls-tree", "HEAD", "harness-only.txt").startswith("120000"))
        self.assertFalse(owned.is_symlink())

    def test_exact_commit_verification_forces_utf8_log_output(self) -> None:
        git(self.repo, "config", "i18n.logOutputEncoding", "ISO-8859-1")
        self.prepare_reviewed_diff()
        accepted = self.harness(
            "codex-direct", "accept", "--cwd", str(self.repo), "--task", "pilot-30",
            "--message", "test: 验证 UTF-8 提交",
        )
        self.assertEqual(accepted.returncode, 0, accepted.stderr or accepted.stdout)
        repeated = self.harness(
            "codex-direct", "commit", "--cwd", str(self.repo), "--task", "pilot-30",
            "--message", "test: 验证 UTF-8 提交",
        )
        self.assertEqual(repeated.returncode, 0, repeated.stderr or repeated.stdout)
        self.assertEqual(json.loads(repeated.stdout)["commit_status"], "already-committed")

    def test_start_adapter_failure_uses_contract_identity_for_recovery(self) -> None:
        import harness.codex_direct as controller
        from harness.cli import main

        original_save = controller._save_run
        calls = 0

        def fail_after_first_save(*args: object, **kwargs: object) -> None:
            nonlocal calls
            original_save(*args, **kwargs)
            calls += 1
            if calls == 1:
                raise controller.CodexDirectAdapterError("durability fixture")

        output = io.StringIO()
        with patch.object(controller, "_save_run", side_effect=fail_after_first_save):
            with redirect_stdout(output):
                exit_code = main(
                    [
                        "codex-direct", "start", "--cwd", str(self.repo),
                        str(self.contract_path),
                    ]
                )

        self.assertEqual(exit_code, 6)
        self.assertEqual(json.loads(output.getvalue())["state"], "recovery-required")

    def test_controller_ignores_git_repository_redirection_environment(self) -> None:
        alternate_index = self.root / "outside.index"
        with patch.dict(os.environ, {"GIT_INDEX_FILE": str(alternate_index)}):
            self.prepare_reviewed_diff()
            accepted = self.harness(
                "codex-direct", "accept", "--cwd", str(self.repo), "--task", "pilot-30"
            )

        self.assertEqual(accepted.returncode, 0, accepted.stderr or accepted.stdout)
        self.assertEqual(json.loads(accepted.stdout)["commit_status"], "created")
        self.assertFalse(alternate_index.exists())
        self.assertEqual(git(self.repo, "status", "--short"), "")

    def test_repair_limit_is_finite_even_when_diff_and_evidence_change(self) -> None:
        contract = json.loads(self.contract_path.read_text(encoding="utf-8"))
        contract["plan"]["repair_policy"]["max_attempts"] = 1
        self.contract_path.write_text(json.dumps(contract), encoding="utf-8")
        self.assertEqual(
            self.harness(
                "codex-direct", "start", "--cwd", str(self.repo), str(self.contract_path)
            ).returncode,
            0,
        )
        (self.repo / "harness-only.txt").write_text("attempt one\n", encoding="utf-8")
        self.assertEqual(
            self.harness(
                "codex-direct",
                "advance",
                "--cwd",
                str(self.repo),
                "--task",
                "pilot-30",
                "--to",
                "verifying",
            ).returncode,
            0,
        )
        self.assertEqual(
            self.harness(
                "codex-direct",
                "record-check",
                "--cwd",
                str(self.repo),
                "--task",
                "pilot-30",
                "--check",
                "owned-file-check",
                "--status",
                "fail",
                "--source",
                "command",
                "--exit-code",
                "1",
                "--sensitivity",
                "metadata",
                "--digest",
                hashlib.sha256(b"attempt-one").hexdigest(),
            ).returncode,
            0,
        )
        self.assertEqual(
            self.harness(
                "codex-direct",
                "repair",
                "--cwd",
                str(self.repo),
                "--task",
                "pilot-30",
                "--fingerprint",
                hashlib.sha256(b"failure-one").hexdigest(),
            ).returncode,
            0,
        )
        (self.repo / "harness-only.txt").write_text("attempt two\n", encoding="utf-8")
        self.assertEqual(
            self.harness(
                "codex-direct",
                "advance",
                "--cwd",
                str(self.repo),
                "--task",
                "pilot-30",
                "--to",
                "verifying",
            ).returncode,
            0,
        )
        self.assertEqual(
            self.harness(
                "codex-direct",
                "record-check",
                "--cwd",
                str(self.repo),
                "--task",
                "pilot-30",
                "--check",
                "owned-file-check",
                "--status",
                "fail",
                "--source",
                "command",
                "--exit-code",
                "1",
                "--sensitivity",
                "metadata",
                "--digest",
                hashlib.sha256(b"attempt-two").hexdigest(),
            ).returncode,
            0,
        )
        stopped = self.harness(
            "codex-direct",
            "repair",
            "--cwd",
            str(self.repo),
            "--task",
            "pilot-30",
            "--fingerprint",
            hashlib.sha256(b"failure-two").hexdigest(),
        )
        self.assertEqual(stopped.returncode, 6, stopped.stderr or stopped.stdout)
        self.assertEqual(
            json.loads(stopped.stdout)["recovery_bundle"]["failure"]["category"],
            "repair-limit",
        )

    def test_repair_invalidates_prior_criteria_and_risk_review(self) -> None:
        self.prepare_reviewed_diff()
        recorded = self.harness(
            "codex-direct", "risk", "--cwd", str(self.repo), "--task", "pilot-30",
            "--risk", "reviewed-risk", "--severity", "low", "--status", "resolved",
            "--digest", hashlib.sha256(b"reviewed-risk").hexdigest(),
        )
        self.assertEqual(recorded.returncode, 0, recorded.stderr or recorded.stdout)
        repair = self.harness(
            "codex-direct", "repair", "--cwd", str(self.repo), "--task", "pilot-30",
            "--fingerprint", hashlib.sha256(b"new-diff-required").hexdigest(),
        )
        self.assertEqual(repair.returncode, 0, repair.stderr or repair.stdout)
        status = self.harness(
            "codex-direct", "status", "--cwd", str(self.repo), "--task", "pilot-30"
        )
        payload = json.loads(status.stdout)
        self.assertEqual(payload["criteria"], {})
        self.assertEqual(payload["risks"], {})

    def test_commit_is_post_acceptance_owned_exactly_once_and_never_pushes(self) -> None:
        contract = json.loads(self.contract_path.read_text(encoding="utf-8"))
        contract["plan"]["verification_plan"] = [
            {
                "id": "owned-file-check",
                "command": "test -f harness-only.txt",
                "required": True,
            },
            {
                "id": "review-check",
                "command": "inspect final diff",
                "required": True,
            },
        ]
        self.contract_path.write_text(json.dumps(contract), encoding="utf-8")
        base_sha = git(self.repo, "rev-parse", "HEAD")
        bare = self.root / "origin.git"
        subprocess.run(
            ["git", "clone", "--bare", str(self.repo), str(bare)],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        git(self.repo, "remote", "add", "origin", str(bare))

        start = self.harness(
            "codex-direct", "start", "--cwd", str(self.repo), str(self.contract_path)
        )
        self.assertEqual(start.returncode, 0, start.stderr or start.stdout)
        early = self.harness(
            "codex-direct",
            "commit",
            "--cwd",
            str(self.repo),
            "--task",
            "pilot-30",
            "--message",
            "feat: complete pilot",
        )
        self.assertEqual(early.returncode, 2)

        (self.repo / "harness-only.txt").write_text("accepted\n", encoding="utf-8")
        self.assertEqual(
            self.harness(
                "codex-direct",
                "advance",
                "--cwd",
                str(self.repo),
                "--task",
                "pilot-30",
                "--to",
                "verifying",
            ).returncode,
            0,
        )
        evidence_digest = hashlib.sha256(b"commit-pilot-check").hexdigest()
        self.assertEqual(
            self.harness(
                "codex-direct",
                "record-check",
                "--cwd",
                str(self.repo),
                "--task",
                "pilot-30",
                "--check",
                "owned-file-check",
                "--status",
                "pass",
                "--source",
                "command",
                "--exit-code",
                "0",
                "--sensitivity",
                "metadata",
                "--digest",
                evidence_digest,
            ).returncode,
            0,
        )
        review_digest = hashlib.sha256(b"commit-pilot-review").hexdigest()
        asserted_review = self.harness(
            "codex-direct",
            "record-check",
            "--cwd",
            str(self.repo),
            "--task",
            "pilot-30",
            "--check",
            "review-check",
            "--status",
            "pass",
            "--source",
            "command",
            "--exit-code",
            "0",
            "--sensitivity",
            "metadata",
            "--digest",
            review_digest,
        )
        self.assertEqual(
            asserted_review.returncode, 0, asserted_review.stderr or asserted_review.stdout
        )
        self.assertEqual(
            self.harness(
                "codex-direct",
                "advance",
                "--cwd",
                str(self.repo),
                "--task",
                "pilot-30",
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
                "pilot-30",
                "--criterion",
                "writes-owned-file",
                "--status",
                "pass",
                "--evidence-digest",
                evidence_digest,
            ).returncode,
            0,
        )
        without_review = self.harness(
            "codex-direct", "accept", "--cwd", str(self.repo), "--task", "pilot-30"
        )
        self.assertEqual(without_review.returncode, 2)
        self.assertIn("review", json.loads(without_review.stdout)["error"].lower())
        reviewed = self.harness(
            "codex-direct",
            "record-check",
            "--cwd",
            str(self.repo),
            "--task",
            "pilot-30",
            "--check",
            "review-check",
            "--status",
            "pass",
            "--source",
            "review",
            "--sensitivity",
            "metadata",
            "--digest",
            review_digest,
        )
        self.assertEqual(reviewed.returncode, 0, reviewed.stderr or reviewed.stdout)
        (self.repo / "README.md").write_text("unrelated\n", encoding="utf-8")
        mixed = self.harness(
            "codex-direct", "accept", "--cwd", str(self.repo), "--task", "pilot-30"
        )
        self.assertEqual(mixed.returncode, 2)
        self.assertIn("current diff", json.loads(mixed.stdout)["error"].lower())
        (self.repo / "README.md").write_text("seed\n", encoding="utf-8")
        accepted = self.harness(
            "codex-direct", "accept", "--cwd", str(self.repo), "--task", "pilot-30"
        )
        self.assertEqual(accepted.returncode, 0, accepted.stderr or accepted.stdout)
        payload = json.loads(accepted.stdout)
        self.assertEqual(payload["commit_status"], "created")
        commit_sha = payload["commit_sha"]
        self.assertNotEqual(commit_sha, base_sha)
        self.assertEqual(git(self.repo, "rev-list", "--count", f"{base_sha}..HEAD"), "1")
        self.assertEqual(
            git(self.repo, "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"),
            "harness-only.txt",
        )
        self.assertEqual(git(bare, "rev-parse", "refs/heads/main"), base_sha)

        git(self.repo, "switch", "-c", "moved")
        wrong_branch = self.harness(
            "codex-direct",
            "commit",
            "--cwd",
            str(self.repo),
            "--task",
            "pilot-30",
            "--message",
            "feat: complete pilot",
        )
        self.assertEqual(
            wrong_branch.returncode, 2, wrong_branch.stderr or wrong_branch.stdout
        )
        git(self.repo, "switch", "main")

        repeated = self.harness(
            "codex-direct",
            "commit",
            "--cwd",
            str(self.repo),
            "--task",
            "pilot-30",
            "--message",
            "feat: complete pilot",
        )
        self.assertEqual(repeated.returncode, 0, repeated.stderr or repeated.stdout)
        self.assertEqual(json.loads(repeated.stdout)["commit_status"], "already-committed")
        self.assertEqual(json.loads(repeated.stdout)["commit_sha"], commit_sha)
        self.assertEqual(git(self.repo, "rev-list", "--count", f"{base_sha}..HEAD"), "1")
        status = self.harness(
            "codex-direct", "status", "--cwd", str(self.repo), "--task", "pilot-30"
        )
        self.assertEqual(status.returncode, 0, status.stderr or status.stdout)
        summary = json.loads(status.stdout)
        self.assertEqual(summary["state"], "accepted")
        self.assertEqual(summary["commit_sha"], commit_sha)
        self.assertEqual(summary["criteria"]["writes-owned-file"]["status"], "pass")
        self.assertEqual(summary["accepted_diff"]["paths"], ["harness-only.txt"])

    def test_persisted_commit_sha_still_requires_exact_ticket_commit(self) -> None:
        self.prepare_reviewed_diff()
        accepted = self.harness(
            "codex-direct", "accept", "--cwd", str(self.repo), "--task", "pilot-30"
        )
        self.assertEqual(accepted.returncode, 0, accepted.stderr or accepted.stdout)
        git(self.repo, "commit", "--allow-empty", "-m", "unrelated clean commit")
        unrelated = git(self.repo, "rev-parse", "HEAD")
        run_path = self.run_path()
        run = json.loads(run_path.read_text(encoding="utf-8"))
        run["commit_sha"] = unrelated
        run_path.write_text(json.dumps(run), encoding="utf-8")

        rejected = self.harness(
            "codex-direct", "commit", "--cwd", str(self.repo), "--task", "pilot-30",
            "--message", "test: exact persisted commit",
        )

        self.assertEqual(rejected.returncode, 2, rejected.stderr or rejected.stdout)
        self.assertIn("head moved", json.loads(rejected.stdout)["error"].lower())

    def test_commit_recovery_rejects_a_different_owned_diff(self) -> None:
        import harness.codex_direct as controller

        self.assertEqual(
            self.harness(
                "codex-direct", "start", "--cwd", str(self.repo), str(self.contract_path)
            ).returncode,
            0,
        )
        (self.repo / "harness-only.txt").write_text("accepted\n", encoding="utf-8")
        self.assertEqual(
            self.harness(
                "codex-direct",
                "advance",
                "--cwd",
                str(self.repo),
                "--task",
                "pilot-30",
                "--to",
                "verifying",
            ).returncode,
            0,
        )
        check_digest = hashlib.sha256(b"recovery-check").hexdigest()
        review_digest = hashlib.sha256(b"recovery-review").hexdigest()
        for check_id, source, digest in (
            ("owned-file-check", "command", check_digest),
            ("review-check", "review", review_digest),
        ):
            args = [
                "codex-direct",
                "record-check",
                "--cwd",
                str(self.repo),
                "--task",
                "pilot-30",
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
                args.extend(["--exit-code", "0"])
            self.assertEqual(self.harness(*args).returncode, 0)
        self.assertEqual(
            self.harness(
                "codex-direct",
                "advance",
                "--cwd",
                str(self.repo),
                "--task",
                "pilot-30",
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
                "pilot-30",
                "--criterion",
                "writes-owned-file",
                "--status",
                "pass",
                "--evidence-digest",
                check_digest,
            ).returncode,
            0,
        )
        context = discover_worktree(self.repo)
        with patch.object(
            controller,
            "_commit_unlocked",
            side_effect=controller.CodexDirectAdapterError("simulated commit interruption"),
        ):
            with self.assertRaises(controller.CodexDirectAdapterError):
                controller.accept_codex_direct(context, task_id="pilot-30")

        (self.repo / "harness-only.txt").write_text("different\n", encoding="utf-8")
        git(self.repo, "add", "harness-only.txt")
        git(
            self.repo,
            "commit",
            "-m",
            "different",
            "-m",
            f"Harness-Task: {controller._task_key('pilot-30')}",
        )
        (self.repo / "harness-only.txt").write_text("accepted\n", encoding="utf-8")
        git(self.repo, "add", "harness-only.txt")
        recovered = self.harness(
            "codex-direct",
            "commit",
            "--cwd",
            str(self.repo),
            "--task",
            "pilot-30",
            "--message",
            "feat: complete pilot",
        )
        self.assertEqual(recovered.returncode, 2, recovered.stderr or recovered.stdout)
        self.assertIn("accepted ticket commit", json.loads(recovered.stdout)["error"])


if __name__ == "__main__":
    unittest.main()
