from __future__ import annotations

import json
import hashlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from harness.context import discover_worktree


ROOT = Path(__file__).resolve().parents[2]
GIT = shutil.which("git") or "git"


def child_env(**extra: str) -> dict[str, str]:
    env = {
        key: os.environ[key]
        for key in ("COMSPEC", "PATH", "PATHEXT", "SYSTEMDRIVE", "SYSTEMROOT", "TEMP", "TMP", "WINDIR")
        if key in os.environ
    }
    env.update(
        {
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0",
            "GCM_INTERACTIVE": "never",
            "PYTHONIOENCODING": "utf-8",
            "PYTHONUTF8": "1",
            **extra,
        }
    )
    return env


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        [GIT, "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=child_env(),
    )
    return result.stdout.strip()


class ClaudeDirectProcessTests(unittest.TestCase):
    def test_child_environment_excludes_credentials(self) -> None:
        credential_keys = {
            "BILIBILI_SESSDATA",
            "BILIBILI_BILI_JCT",
            "BILIBILI_DEDEUSERID",
            "GITHUB_TOKEN",
            "NPM_TOKEN",
        }
        with patch.dict(os.environ, dict.fromkeys(credential_keys, "synthetic-secret")):
            self.assertTrue(credential_keys.isdisjoint(child_env()))

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
        self.contract_path.write_text(
            json.dumps(
                {
                    "schema": "harness.task-contract/v1",
                    "task": {
                        "id": "pilot-31",
                        "source": "https://github.com/example/repo/issues/31",
                    },
                    "execution": {
                        "mode": "claude-direct",
                        "canonical_worktree": str(self.repo.resolve()),
                        "base_sha": git(self.repo, "rev-parse", "HEAD"),
                        "branch": "main",
                        "adapter_switch_policy": "stop-and-report",
                    },
                    "plan": {
                        "objective": "Exercise one bounded Claude Direct ticket.",
                        "owned_paths": ["harness-only.txt"],
                        "acceptance_criteria": [
                            {
                                "id": "writes-owned-file",
                                "description": "The owned file is created.",
                            }
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
                        ],
                        "repair_policy": {"max_attempts": 2},
                        "stop_conditions": [
                            "adapter-failure",
                            "new-authority",
                            "scope-expansion",
                        ],
                    },
                    "writer_lease": {"holder": "claude", "state": "inactive"},
                    "acceptance_owner": "claude",
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
                    "required_manual_skills": [
                        {
                            "name": "implement",
                            "host": "claude",
                            "status": "invoked",
                            "invocation": "/implement",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

    def harness(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "harness", *args],
            cwd=self.repo,
            env=child_env(PYTHONPATH=str(ROOT)),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    def contract(self) -> dict[str, object]:
        return json.loads(self.contract_path.read_text(encoding="utf-8"))

    def write_contract(self, contract: dict[str, object]) -> None:
        self.contract_path.write_text(json.dumps(contract), encoding="utf-8")

    def run_json(self, *args: str, expected: int = 0) -> dict[str, object]:
        result = self.harness(*args)
        self.assertEqual(result.returncode, expected, result.stderr or result.stdout)
        return json.loads(result.stdout)

    def prepare_reviewed_diff(self) -> tuple[str, str]:
        base_sha = git(self.repo, "rev-parse", "HEAD")
        self.run_json(
            "claude-direct", "start", "--cwd", str(self.repo), str(self.contract_path)
        )
        (self.repo / "harness-only.txt").write_text("accepted\n", encoding="utf-8")
        self.run_json(
            "claude-direct", "advance", "--cwd", str(self.repo), "--task", "pilot-31",
            "--to", "verifying",
        )
        check_digest = hashlib.sha256(b"claude-direct-check").hexdigest()
        review_digest = hashlib.sha256(b"claude-direct-review").hexdigest()
        for check_id, source, digest in (
            ("owned-file-check", "command", check_digest),
            ("review-check", "review", review_digest),
        ):
            args = [
                "claude-direct", "record-check", "--cwd", str(self.repo), "--task",
                "pilot-31", "--check", check_id, "--status", "pass", "--source",
                source, "--sensitivity", "metadata", "--digest", digest,
            ]
            if source == "command":
                args.extend(["--exit-code", "0"])
            self.run_json(*args)
        self.run_json(
            "claude-direct", "advance", "--cwd", str(self.repo), "--task", "pilot-31",
            "--to", "reviewing",
        )
        self.run_json(
            "claude-direct", "judge", "--cwd", str(self.repo), "--task", "pilot-31",
            "--criterion", "writes-owned-file", "--status", "pass",
            "--evidence-digest", check_digest,
        )
        return base_sha, check_digest

    def test_start_freezes_clean_baseline_and_acquires_claude_lease(self) -> None:
        result = self.harness(
            "claude-direct",
            "start",
            "--cwd",
            str(self.repo),
            str(self.contract_path),
        )

        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["schema"], "harness.claude-direct-control/v1")
        self.assertEqual(payload["task_id"], "pilot-31")
        self.assertEqual(payload["state"], "executing")
        self.assertEqual(payload["mode"], "claude-direct")
        self.assertEqual(
            payload["writer_lease"], {"holder": "claude", "state": "active"}
        )
        self.assertEqual(git(self.repo, "status", "--short"), "")

    def test_codex_command_cannot_control_a_claude_direct_run(self) -> None:
        started = self.harness(
            "claude-direct", "start", "--cwd", str(self.repo), str(self.contract_path)
        )
        self.assertEqual(started.returncode, 0, started.stderr or started.stdout)

        rejected = self.harness(
            "codex-direct", "status", "--cwd", str(self.repo), "--task", "pilot-31"
        )

        self.assertEqual(rejected.returncode, 2, rejected.stderr or rejected.stdout)
        self.assertIn("mode", json.loads(rejected.stdout)["error"].lower())
        mutation = self.harness(
            "codex-direct", "advance", "--cwd", str(self.repo), "--task", "pilot-31",
            "--to", "verifying",
        )
        self.assertEqual(mutation.returncode, 2, mutation.stderr or mutation.stdout)
        status = self.run_json(
            "claude-direct", "status", "--cwd", str(self.repo), "--task", "pilot-31"
        )
        self.assertEqual(status["state"], "executing")

    def test_start_rejects_claude_mode_owner_and_manual_host_tampering(self) -> None:
        original = self.contract()
        cases = []
        wrong_mode = json.loads(json.dumps(original))
        wrong_mode["execution"]["mode"] = "codex-direct"
        cases.append(wrong_mode)
        wrong_owner = json.loads(json.dumps(original))
        wrong_owner["acceptance_owner"] = "codex"
        cases.append(wrong_owner)
        wrong_host = json.loads(json.dumps(original))
        wrong_host["required_manual_skills"][0].update(
            {"host": "codex", "invocation": "$implement"}
        )
        cases.append(wrong_host)

        for contract in cases:
            with self.subTest(contract=contract):
                self.write_contract(contract)
                rejected = self.harness(
                    "claude-direct", "start", "--cwd", str(self.repo),
                    str(self.contract_path),
                )
                self.assertEqual(rejected.returncode, 2, rejected.stderr or rejected.stdout)

        self.assertEqual(git(self.repo, "status", "--short"), "")
        self.assertEqual(
            list((discover_worktree(self.repo).runtime_root / "tasks").glob("*/run.json")),
            [],
        )

    def test_missing_manual_skill_reminds_once_without_starting_or_writing(self) -> None:
        contract = self.contract()
        contract["required_manual_skills"] = [
            {"name": "implement", "host": "claude", "status": "required"}
        ]
        self.write_contract(contract)

        first = self.harness(
            "claude-direct", "start", "--cwd", str(self.repo), str(self.contract_path)
        )
        second = self.harness(
            "claude-direct", "start", "--cwd", str(self.repo), str(self.contract_path)
        )

        self.assertEqual(first.returncode, 3, first.stderr or first.stdout)
        self.assertEqual(second.returncode, 3, second.stderr or second.stdout)
        first_payload = json.loads(first.stdout)
        second_payload = json.loads(second.stdout)
        self.assertEqual(first_payload["manual_skill"]["status"], "reminder-emitted")
        self.assertEqual(second_payload["manual_skill"]["status"], "already-reminded")
        self.assertEqual(first_payload["manual_skill"]["native_invocation"], "/implement")
        self.assertEqual(second_payload["manual_skill"]["native_invocation"], "/implement")
        self.assertEqual(first_payload["writer_lease"], {"holder": "claude", "state": "inactive"})
        context = discover_worktree(self.repo)
        self.assertEqual(list((context.runtime_root / "tasks").glob("*/run.json")), [])
        self.assertFalse((self.repo / "harness-only.txt").exists())
        self.assertEqual(git(self.repo, "status", "--short"), "")

    def test_unstable_lock_rolls_back_the_source_scoped_skill_reminder(self) -> None:
        import harness.codex_direct as controller

        contract = self.contract()
        contract["required_manual_skills"] = [
            {"name": "implement", "host": "claude", "status": "required"}
        ]
        context = discover_worktree(self.repo)
        lock = context.common_git_dir / "config"
        identity = controller._repository_lock_identity(lock)
        changed = (*identity[:-1], identity[-1] + 1)

        with patch.object(
            controller,
            "_repository_lock_identity",
            side_effect=[identity, identity, changed],
        ):
            with self.assertRaisesRegex(controller.CodexDirectError, "changed during"):
                controller.start_claude_direct(context, contract)

        self.assertEqual(
            list((context.runtime_root / "manual-skill-reminders").glob("*.json")), []
        )
        control, exit_code = controller.start_claude_direct(context, contract)
        self.assertEqual(exit_code, 3)
        self.assertEqual(control["manual_skill"]["status"], "reminder-emitted")

    def test_guard_matches_the_shared_direct_authority_matrix(self) -> None:
        started = self.harness(
            "claude-direct", "start", "--cwd", str(self.repo), str(self.contract_path)
        )
        self.assertEqual(started.returncode, 0, started.stderr or started.stdout)

        for action, path in (
            ("read", None),
            ("edit", "harness-only.txt"),
            ("build", None),
            ("test", None),
        ):
            args = [
                "claude-direct", "guard", "--cwd", str(self.repo), "--task",
                "pilot-31", "--action", action,
            ]
            if path is not None:
                args.extend(["--path", path])
            result = self.harness(*args)
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            self.assertEqual(json.loads(result.stdout)["decision"], "allowed")

        unowned = self.harness(
            "claude-direct", "guard", "--cwd", str(self.repo), "--task", "pilot-31",
            "--action", "edit", "--path", "README.md",
        )
        self.assertEqual(unowned.returncode, 5)
        self.assertEqual(json.loads(unowned.stdout)["reason_code"], "path-not-owned")

        for action in ("broad-delete", "history-rewrite", "credential", "ssh"):
            result = self.harness(
                "claude-direct", "guard", "--cwd", str(self.repo), "--task",
                "pilot-31", "--action", action,
            )
            self.assertEqual(result.returncode, 5, action)
            self.assertEqual(json.loads(result.stdout)["decision"], "blocked")

        for action in ("push", "pull-request", "tag", "release", "publish"):
            result = self.harness(
                "claude-direct", "guard", "--cwd", str(self.repo), "--task",
                "pilot-31", "--action", action,
            )
            self.assertEqual(result.returncode, 4, action)
            self.assertEqual(
                json.loads(result.stdout)["decision"], "user-authorization-required"
            )

        early_commit = self.harness(
            "claude-direct", "guard", "--cwd", str(self.repo), "--task", "pilot-31",
            "--action", "local-commit",
        )
        self.assertEqual(early_commit.returncode, 5)
        self.assertEqual(json.loads(early_commit.stdout)["reason_code"], "acceptance-required")

    def test_full_path_creates_exactly_one_scoped_local_commit_without_remote_effects(self) -> None:
        bare = self.root / "origin.git"
        subprocess.run(
            [GIT, "clone", "--bare", str(self.repo), str(bare)],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=child_env(),
        )
        git(self.repo, "remote", "add", "origin", str(bare))
        remote_before = git(bare, "rev-parse", "refs/heads/main")
        base_sha, _ = self.prepare_reviewed_diff()

        accepted = self.run_json(
            "claude-direct", "accept", "--cwd", str(self.repo), "--task", "pilot-31",
            "--message", "feat(harness): complete Claude Direct pilot",
        )
        commit_sha = str(accepted["commit_sha"])

        self.assertEqual(accepted["schema"], "harness.claude-direct-control/v1")
        self.assertEqual(accepted["mode"], "claude-direct")
        self.assertEqual(accepted["state"], "accepted")
        self.assertEqual(accepted["commit_status"], "created")
        self.assertEqual(accepted["writer_lease"], {"holder": "claude", "state": "released"})
        self.assertEqual(git(self.repo, "rev-list", "--count", f"{base_sha}..HEAD"), "1")
        self.assertEqual(git(self.repo, "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"), "harness-only.txt")
        self.assertRegex(
            git(self.repo, "show", "-s", "--format=%B", "HEAD"),
            r"Harness-Task: [0-9a-f]{20}",
        )
        self.assertEqual(git(self.repo, "status", "--short"), "")
        self.assertEqual(git(bare, "rev-parse", "refs/heads/main"), remote_before)
        self.assertNotEqual(commit_sha, remote_before)

        repeated = self.run_json(
            "claude-direct", "commit", "--cwd", str(self.repo), "--task", "pilot-31",
            "--message", "feat(harness): complete Claude Direct pilot",
        )
        self.assertEqual(repeated["commit_status"], "already-committed")
        self.assertEqual(repeated["commit_sha"], commit_sha)
        self.assertEqual(git(self.repo, "rev-list", "--count", f"{base_sha}..HEAD"), "1")
        self.assertEqual(git(bare, "rev-parse", "refs/heads/main"), remote_before)

    def test_codex_and_claude_cannot_hold_writers_for_the_same_source(self) -> None:
        linked = self.root / "linked"
        git(self.repo, "worktree", "add", "-b", "linked", str(linked))
        codex_contract = self.contract()
        codex_contract["task"] = {
            "id": "pilot-30-alias",
            "source": codex_contract["task"]["source"],
        }
        codex_contract["execution"] = {
            **codex_contract["execution"],
            "mode": "codex-direct",
            "canonical_worktree": str(linked.resolve()),
            "base_sha": git(linked, "rev-parse", "HEAD"),
            "branch": "linked",
        }
        codex_contract["writer_lease"] = {"holder": "codex", "state": "inactive"}
        codex_contract["acceptance_owner"] = "codex"
        codex_contract["required_manual_skills"] = [
            {
                "name": "implement",
                "host": "codex",
                "status": "invoked",
                "invocation": "$implement",
            }
        ]
        codex_path = self.root / "codex-contract.json"
        codex_path.write_text(json.dumps(codex_contract), encoding="utf-8")

        first = self.harness(
            "claude-direct", "start", "--cwd", str(self.repo), str(self.contract_path)
        )
        second = self.harness(
            "codex-direct", "start", "--cwd", str(linked), str(codex_path)
        )

        self.assertEqual(first.returncode, 0, first.stderr or first.stdout)
        self.assertEqual(second.returncode, 2, second.stderr or second.stdout)
        self.assertIn("writer lease", json.loads(second.stdout)["error"].lower())
        active_runs = sum(
            len(list((discover_worktree(root).runtime_root / "tasks").glob("*/run.json")))
            for root in (self.repo, linked)
        )
        self.assertEqual(active_runs, 1)

    def test_repeated_failure_without_progress_emits_a_complete_recovery_bundle(self) -> None:
        self.run_json(
            "claude-direct", "start", "--cwd", str(self.repo), str(self.contract_path)
        )
        (self.repo / "harness-only.txt").write_text("broken\n", encoding="utf-8")
        self.run_json(
            "claude-direct", "advance", "--cwd", str(self.repo), "--task", "pilot-31",
            "--to", "verifying",
        )
        self.run_json(
            "claude-direct", "record-check", "--cwd", str(self.repo), "--task",
            "pilot-31", "--check", "owned-file-check", "--status", "fail",
            "--source", "command", "--exit-code", "1", "--sensitivity", "metadata",
            "--digest", hashlib.sha256(b"same-evidence").hexdigest(),
        )
        fingerprint = hashlib.sha256(b"same-failure").hexdigest()
        first = self.run_json(
            "claude-direct", "repair", "--cwd", str(self.repo), "--task", "pilot-31",
            "--fingerprint", fingerprint,
        )
        self.assertEqual(first["repair_attempt"], 1)
        self.run_json(
            "claude-direct", "advance", "--cwd", str(self.repo), "--task", "pilot-31",
            "--to", "verifying",
        )
        stopped = self.run_json(
            "claude-direct", "repair", "--cwd", str(self.repo), "--task", "pilot-31",
            "--fingerprint", fingerprint, expected=6,
        )

        bundle = stopped["recovery_bundle"]
        self.assertEqual(stopped["state"], "recovery-required")
        self.assertEqual(bundle["schema"], "harness.recovery-bundle/v1")
        self.assertEqual(bundle["mode"], "claude-direct")
        self.assertEqual(bundle["failure"], {
            "category": "repeated-failure", "fingerprint": fingerprint,
        })
        self.assertEqual(bundle["writer_lease"], {"holder": "claude", "state": "active"})
        self.assertEqual(bundle["adapter_switch_policy"], "stop-and-report")
        self.assertEqual(bundle["changed_paths"], ["harness-only.txt"])
        self.assertNotIn("fallback", json.dumps(bundle).lower())

    def test_adapter_exception_auto_recovers_without_switching_modes(self) -> None:
        import harness.codex_direct as controller
        from harness.cli import main

        original_save = controller._save_run
        calls = 0

        def fail_after_first_save(*args: object, **kwargs: object) -> None:
            nonlocal calls
            original_save(*args, **kwargs)
            calls += 1
            if calls == 1:
                raise controller.CodexDirectAdapterError("claude durability fixture")

        output = io.StringIO()
        with patch.object(controller, "_save_run", side_effect=fail_after_first_save):
            with redirect_stdout(output):
                exit_code = main(
                    [
                        "claude-direct", "start", "--cwd", str(self.repo),
                        str(self.contract_path),
                    ]
                )

        payload = json.loads(output.getvalue())
        self.assertEqual(exit_code, 6)
        self.assertEqual(payload["schema"], "harness.claude-direct-control/v1")
        self.assertEqual(payload["mode"], "claude-direct")
        self.assertEqual(payload["state"], "recovery-required")
        self.assertEqual(payload["recovery_bundle"]["mode"], "claude-direct")
        self.assertEqual(payload["recovery_bundle"]["adapter_switch_policy"], "stop-and-report")
        self.assertNotIn("fallback", json.dumps(payload).lower())

    def test_shared_fixture_drives_both_public_direct_lifecycles(self) -> None:
        fixture_path = ROOT / "harness" / "fixtures" / "direct-adapter-conformance.json"
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))

        for adapter in fixture["adapters"]:
            with self.subTest(mode=adapter["mode"]):
                repo = self.root / f"conformance-{adapter['writer']}"
                repo.mkdir()
                git(repo, "init", "-b", "main")
                git(repo, "config", "user.name", "Harness Test")
                git(repo, "config", "user.email", "harness@example.invalid")
                (repo / ".gitignore").write_text(".harness/\n", encoding="utf-8")
                (repo / "README.md").write_text("seed\n", encoding="utf-8")
                git(repo, "add", ".gitignore", "README.md")
                git(repo, "commit", "-m", "seed")
                base_sha = git(repo, "rev-parse", "HEAD")

                contract = self.contract()
                contract["task"] = {
                    "id": f"conformance-{adapter['writer']}",
                    "source": f"https://example.invalid/{adapter['mode']}",
                }
                contract["execution"] = {
                    **contract["execution"],
                    "mode": adapter["mode"],
                    "canonical_worktree": str(repo.resolve()),
                    "base_sha": base_sha,
                }
                contract["writer_lease"] = {
                    "holder": adapter["writer"], "state": "inactive",
                }
                contract["acceptance_owner"] = adapter["acceptance_owner"]
                contract["required_manual_skills"] = [
                    {
                        "name": "implement",
                        "host": adapter["skill_host"],
                        "status": "invoked",
                        "invocation": adapter["skill_invocation"],
                    }
                ]
                contract_path = self.root / f"{adapter['mode']}.json"
                contract_path.write_text(json.dumps(contract), encoding="utf-8")
                task_id = contract["task"]["id"]
                command = adapter["command"]

                def run(action: str, *args: str, expected: int = 0) -> dict[str, object]:
                    result = self.harness(
                        command, action, "--cwd", str(repo), *args
                    )
                    self.assertEqual(
                        result.returncode, expected, result.stderr or result.stdout
                    )
                    return json.loads(result.stdout)

                started = run("start", str(contract_path))
                self.assertEqual(started["schema"], adapter["control_schema"])
                self.assertEqual(started["writer_lease"], {
                    "holder": adapter["writer"], "state": "active",
                })
                self.assertEqual(
                    run("guard", "--task", task_id, "--action", "edit", "--path", "harness-only.txt")["decision"],
                    "allowed",
                )
                self.assertEqual(
                    run("guard", "--task", task_id, "--action", "ssh", expected=5)["decision"],
                    "blocked",
                )
                (repo / "harness-only.txt").write_text("accepted\n", encoding="utf-8")
                run("advance", "--task", task_id, "--to", "verifying")
                check_digest = hashlib.sha256(
                    f"{adapter['mode']}:check".encode()
                ).hexdigest()
                review_digest = hashlib.sha256(
                    f"{adapter['mode']}:review".encode()
                ).hexdigest()
                run(
                    "record-check", "--task", task_id, "--check", "owned-file-check",
                    "--status", "pass", "--source", "command", "--exit-code", "0",
                    "--sensitivity", "metadata", "--digest", check_digest,
                )
                run(
                    "record-check", "--task", task_id, "--check", "review-check",
                    "--status", "pass", "--source", "review", "--sensitivity",
                    "metadata", "--digest", review_digest,
                )
                run("advance", "--task", task_id, "--to", "reviewing")
                run(
                    "judge", "--task", task_id, "--criterion", "writes-owned-file",
                    "--status", "pass", "--evidence-digest", check_digest,
                )
                accepted = run(
                    "accept", "--task", task_id, "--message",
                    f"test: accept {adapter['mode']} conformance",
                )
                self.assertEqual(accepted["state"], "accepted")
                self.assertEqual(accepted["commit_status"], "created")
                self.assertEqual(accepted["writer_lease"], {
                    "holder": adapter["writer"], "state": "released",
                })
                self.assertEqual(git(repo, "rev-list", "--count", f"{base_sha}..HEAD"), "1")
                self.assertEqual(
                    git(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"),
                    "harness-only.txt",
                )
                self.assertEqual(git(repo, "status", "--short"), "")
                self.assertEqual(git(repo, "remote"), "")


if __name__ == "__main__":
    unittest.main()
