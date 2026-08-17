"""Tests for the Codex-Paseo-Claude collaboration seam (Issue #32).

Function tests mock ``_run_paseo_cli`` with real Paseo CLI JSON shapes.
CLI tests verify the subcommand is registered (subprocess, no mock).
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from harness.context import WorktreeContext, discover_worktree

ROOT = Path(__file__).resolve().parents[2]

GIT_EXE: str | None = shutil.which("git")
# ponytail: one portable resolution, no hard-coded drives, no process-global
# PATH mutation.  When git is absent the test class skips with a clear reason;
# run with a command-scoped PATH injection for local verification:
#   PATH="D:\Git\cmd;$PATH" python -m pytest harness/tests/test_paseo_collaboration.py -v


def _git(repo: Path, *args: str) -> str:
    # GIT_EXE is always set when tests run (skipped otherwise).
    exe = GIT_EXE or "git"
    result = subprocess.run(
        [exe, "-C", str(repo), *args],
        check=True, capture_output=True, text=True, encoding="utf-8",
    )
    return result.stdout.strip()


def _git_init(repo: Path, branch: str = "main") -> None:
    _git(repo, "init")
    _git(repo, "checkout", "-b", branch)


# ---------------------------------------------------------------------------
# Real Paseo CLI JSON shapes (used in mock returns)
# ---------------------------------------------------------------------------

def _make_daemon_status(running: bool = True) -> dict:
    return {
        "localDaemon": "running" if running else "stopped",
        "connectedDaemon": "connected" if running else "",
        "daemonVersion": "1.0.0",
        "cliVersion": "1.0.0",
    }


def _make_provider_list() -> list[dict]:
    return [
        {"provider": "codex", "status": "available", "label": "Codex", "defaultMode": "auto"},
        {"provider": "claude", "status": "available", "label": "Claude Code", "defaultMode": "auto"},
    ]


def _make_model_list() -> list[dict]:
    return [
        {"id": "deepseek-v4-flash", "model": "deepseek-v4-flash", "description": "Fast model"},
    ]


def _make_run_result(agent_id: str = "agent-test-uuid") -> dict:
    return {"id": agent_id, "status": "running"}


def _make_inspect_result(
    agent_id: str = "agent-test-uuid",
    provider: str = "claude",
    cwd: str = "",
) -> dict:
    return {"Id": agent_id, "Provider": provider, "Model": "deepseek-v4-flash",
            "Cwd": cwd, "Status": "idle", "Mode": "bypassPermissions",
            "Archived": False}


def _make_send_result() -> dict:
    return {"status": "dispatched"}


# ---------------------------------------------------------------------------
# Mock helper: maps first CLI arg to the expected return value
# ---------------------------------------------------------------------------

def _paseo_cli_side_effect(repo_path: str = "") -> object:
    """Return a mock for ``_run_paseo_cli`` that uses *repo_path* for Cwd."""
    def _effect(*args: str, **kwargs) -> dict | list:  # noqa: E306
        cmd = args[0] if args else ""
        if cmd == "daemon":
            return _make_daemon_status()
        if cmd == "provider":
            sub = args[1] if len(args) > 1 else ""
            if sub == "ls":
                return _make_provider_list()
            if sub == "models":
                return _make_model_list()
        if cmd == "run":
            return _make_run_result()
        if cmd == "inspect":
            agent_id = args[1] if len(args) > 1 else "agent-test-uuid"
            return _make_inspect_result(agent_id=agent_id, cwd=repo_path)
        if cmd == "send":
            return _make_send_result()
        raise RuntimeError(f"unexpected paseo cli args: {args}")
    return _effect


# ---------------------------------------------------------------------------
# Contract builder
# ---------------------------------------------------------------------------

def _collab_contract(repo: Path, **overrides: object) -> dict:
    head = _git(repo, "rev-parse", "HEAD")
    c: dict = {
        "schema": "harness.task-contract/v1",
        "task": {
            "id": "github-32",
            "source": "https://github.com/XZXZZX-Ai/bilibili-mcp/issues/32",
        },
        "execution": {
            "mode": "codex-paseo-claude",
            "canonical_worktree": str(repo.resolve()),
            "base_sha": head,
            "branch": "main",
            "adapter_switch_policy": "stop-and-report",
        },
        "plan": {
            "objective": "Implement collaboration loop.",
            "owned_paths": ["harness/paseo_collaboration.py"],
            "acceptance_criteria": [
                {"id": "preflight-readonly", "description": "Read-only preflight."},
            ],
            "verification_plan": [
                {"id": "tests", "command": "python -m unittest", "required": True},
            ],
            "repair_policy": {"max_attempts": 2},
            "stop_conditions": ["adapter-failure", "new-authority", "scope-expansion"],
        },
        "writer_lease": {"holder": "claude", "state": "inactive"},
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
                "name": "implement", "host": "claude",
                "status": "invoked", "invocation": "/implement",
            },
        ],
    }
    c.update(overrides)
    return c


# ---------------------------------------------------------------------------
# Bridge trigger helper
# ---------------------------------------------------------------------------

def _write_bridge(
    repo: Path,
    contract: dict | None = None,
    *,
    handoff_digest: str | None = None,
) -> None:
    td = repo / ".harness" / "coordination" / "github-32"
    td.mkdir(parents=True, exist_ok=True)
    if contract is not None:
        cd = hashlib.sha256(
            json.dumps(contract, sort_keys=True, ensure_ascii=True).encode("utf-8")
        ).hexdigest()
    else:
        cd = "aa" * 32
    hd = handoff_digest if handoff_digest is not None else "bb" * 32
    (td / "bridge-trigger.json").write_text(
        json.dumps({
            "schema": "harness.codex-bridge-trigger/v1",
            "task_id": "github-32",
            "mode": "codex-paseo-claude",
            "recorded_at": "2026-08-12T00:00:00Z",
            "triggered_by": "codex",
            "target_host": "claude",
            "manual_skill": "implement",
            "native_invocation": "/implement",
            "contract_digest": cd,
            "handoff_digest": hd,
            "canonical_worktree": str(repo.resolve()),
            "base_sha": _git(repo, "rev-parse", "HEAD"),
            "branch": "main",
            "writer_lease": {"holder": "claude", "state": "active"},
            "acceptance_owner": "codex",
            "status": "recorded-before-native-invocation",
        }),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Test base (no PATH mutation — finding #20)
# ---------------------------------------------------------------------------

class _PaseoTestBase(unittest.TestCase):
    """Shared bootstrap: temp git repo, no os.environ mutation."""

    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp.cleanup)
        prefs = patch(
            "harness.paseo_collaboration._read_orchestration_prefs",
            return_value={"providers": {"impl": "claude/deepseek-v4-flash"}},
        )
        prefs.start()
        self.addCleanup(prefs.stop)
        self.root = Path(self._temp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        _git_init(self.repo)
        _git(self.repo, "config", "user.name", "Harness Test")
        _git(self.repo, "config", "user.email", "harness@example.invalid")
        (self.repo / ".gitignore").write_text(".harness/\nhandoff.md\n", encoding="utf-8")
        _git(self.repo, "add", ".gitignore")
        _git(self.repo, "commit", "-m", "seed")

    def _ctx(self) -> WorktreeContext:
        return discover_worktree(self.repo)

    def _contract(self, **overrides: object) -> dict:
        return _collab_contract(self.repo, **overrides)


# ---------------------------------------------------------------------------
# Function tests — mock _run_paseo_cli
# ---------------------------------------------------------------------------

@unittest.skipIf(GIT_EXE is None, "git not on PATH — inject PATH at command line")
class PaseoCollaborationFunctionTests(_PaseoTestBase):
    """Tests calling paseo_* functions directly with mocked Paseo CLI."""

    def test_paseo_subprocess_receives_allowlisted_environment(self) -> None:
        from harness.paseo_collaboration import _run_paseo_cli

        captured: dict[str, object] = {}

        class FakeProcess:
            stdout = io.BytesIO(b"{}")
            stderr = io.BytesIO()

            def wait(self, timeout: int) -> int:
                return 0

            def kill(self) -> None:
                pass

        def fake_popen(*args: object, **kwargs: object) -> FakeProcess:
            captured.update(kwargs)
            return FakeProcess()

        sensitive = {
            "ANTHROPIC_API_KEY": "synthetic-secret",
            "BILIBILI_SESSDATA": "synthetic-secret",
            "GITHUB_TOKEN": "synthetic-secret",
            "NPM_TOKEN": "synthetic-secret",
            "PASEO_FAKE_EVENTS": "synthetic-secret",
            "PASEO_HUB_API_KEY": "synthetic-secret",
            "PASEO_PASSWORD": "synthetic-secret",
            "SSH_AUTH_SOCK": "synthetic-secret",
        }
        with (
            patch.dict(os.environ, {**sensitive, "PASEO_HOME": str(self.root)}),
            patch(
                "harness.paseo_collaboration._resolve_paseo_cli",
                return_value=Path("paseo"),
            ),
            patch("harness.paseo_collaboration.subprocess.Popen", new=fake_popen),
        ):
            self.assertEqual(_run_paseo_cli("daemon", "status"), {})

        child_env = captured["env"]
        self.assertIsInstance(child_env, dict)
        self.assertTrue(set(sensitive).isdisjoint(child_env))
        self.assertEqual(child_env.get("PASEO_HOME"), str(self.root))

    # ---- preflight (findings #1, #2) ----

    def test_preflight_read_only_no_daemon_restart(self) -> None:
        from harness.paseo_collaboration import paseo_preflight

        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ):
            result = paseo_preflight(self._ctx())
        self.assertEqual(result["schema"], "harness.paseo-preflight/v1")
        self.assertTrue(result["available"])
        self.assertFalse(result["restarted_daemon"])
        self.assertFalse(result["fallback_chosen"])
        self.assertEqual(result["source"], "orchestration-preferences")

    def test_preflight_fails_closed_when_paseo_unavailable(self) -> None:
        from harness.paseo_collaboration import (
            PaseoCollaborationError,
            paseo_preflight,
        )

        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=PaseoCollaborationError("paseo_cli_unavailable"),
        ):
            result = paseo_preflight(self._ctx())
        self.assertFalse(result["available"])
        self.assertIn("error", result)

    def test_preflight_respects_provider_override(self) -> None:
        from harness.paseo_collaboration import paseo_preflight

        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ):
            result = paseo_preflight(self._ctx(), provider_override="claude/deepseek-v4-flash")
        self.assertTrue(result["available"])
        self.assertEqual(result["provider"], "claude")
        self.assertEqual(result["model"], "deepseek-v4-flash")
        self.assertEqual(result["source"], "explicit-override")

    def test_preflight_malformed_provider_preferences_fail_closed(self) -> None:
        from harness.paseo_collaboration import paseo_preflight

        malformed = (
            None,
            [],
            "claude/deepseek-v4-flash",
            {"impl": None},
            {"impl": "claude/model\nLEAK"},
            {"impl": f"claude/{'m' * 65}"},
            {"impl": "claude/model/extra"},
        )
        for providers in malformed:
            with self.subTest(providers=providers), patch(
                "harness.paseo_collaboration._read_orchestration_prefs",
                return_value={"providers": providers},
            ), patch(
                "harness.paseo_collaboration._run_paseo_cli",
                side_effect=_paseo_cli_side_effect(str(self.repo)),
            ):
                result = paseo_preflight(self._ctx())
                self.assertFalse(result["available"])
                self.assertIn("provider_not_resolved", result["error"])
                self.assertNotIn("LEAK", result["error"])
                self.assertLess(len(result["error"]), 256)

    def test_preflight_daemon_not_running(self) -> None:
        from harness.paseo_collaboration import paseo_preflight

        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            return_value=_make_daemon_status(running=False),
        ):
            result = paseo_preflight(self._ctx())
        self.assertFalse(result["available"])
        self.assertIn("error", result)

    def test_preflight_provider_not_claude_rejected(self) -> None:
        from harness.paseo_collaboration import paseo_preflight

        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            return_value=_make_daemon_status(),
        ):
            # provider list returns only "codex", not "claude"
            def _side_effect(*args, **kwargs):
                cmd = args[0] if args else ""
                if cmd == "daemon":
                    return _make_daemon_status()
                if cmd == "provider":
                    return [{"provider": "codex", "status": "available"}]
                return {}
            with patch(
                "harness.paseo_collaboration._run_paseo_cli",
                side_effect=_side_effect,
            ):
                result = paseo_preflight(self._ctx())
        self.assertFalse(result["available"])

    # ---- bootstrap (findings #3-#7) ----

    def test_bootstrap_wrapper_uses_accepted_lock_protocol(self) -> None:
        """Public ``bootstrap()`` wrapper must use the accepted lock protocol.

        Follows the ``start_direct`` pattern: repository_lock identity from
        ``common_git_dir/config``, bounded_file_lock, _repository_mutex,
        recheck identity before and after the unlocked inner call.
        """
        from harness.paseo_collaboration import bootstrap

        contract = self._contract()
        _write_bridge(self.repo, contract)
        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ):
            result, exit_code = bootstrap(self._ctx(), contract)
        self.assertEqual(exit_code, 0)
        self.assertEqual(result["mode"], "codex-paseo-claude")

    def test_bootstrap_rejects_unavailable_repository_lock(self) -> None:
        """bootstrap() rejects when common_git_dir/config is missing/empty."""
        from harness.paseo_collaboration import PaseoCollaborationError, bootstrap

        contract = self._contract()
        _write_bridge(self.repo, contract)
        ctx = self._ctx()
        # Remove the git config to simulate unavailable lock
        config = ctx.common_git_dir / "config"
        config.unlink()
        with self.assertRaises(PaseoCollaborationError) as cm:
            bootstrap(ctx, contract)
        self.assertIn("repository control lock", str(cm.exception))

    def test_bootstrap_freezes_authority_with_bridge_trigger(self) -> None:
        from harness.paseo_collaboration import paseo_bootstrap

        contract = self._contract()
        _write_bridge(self.repo, contract)
        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ):
            result, exit_code = paseo_bootstrap(self._ctx(), contract)
        self.assertEqual(exit_code, 0)
        self.assertEqual(result["mode"], "codex-paseo-claude")
        self.assertEqual(
            result["writer_lease"], {"holder": "claude", "state": "active"}
        )
        self.assertEqual(result["state"], "executing")

        # Provider must not be persisted in run state
        from harness.codex_direct import _load_run
        _rp, run = _load_run(
            self._ctx(), "github-32", expected_mode="codex-paseo-claude"
        )
        self.assertEqual(run["schema"], "harness.codex-paseo-claude-run/v1")
        self.assertNotIn("provider", run)  # key-level check, not substring
        # Agent ID must be recorded
        self.assertTrue(isinstance(run.get("agent_id"), str) and run["agent_id"])

    def test_bootstrap_without_bridge_trigger_reminds_once(self) -> None:
        from harness.paseo_collaboration import paseo_bootstrap

        contract = self._contract()
        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ):
            first, ec1 = paseo_bootstrap(self._ctx(), contract)
            second, ec2 = paseo_bootstrap(self._ctx(), contract)

        self.assertEqual(ec1, 3)
        self.assertEqual(ec2, 3)
        self.assertEqual(first["state"], "awaiting-user")
        self.assertEqual(first["manual_skill"]["status"], "reminder-emitted")
        self.assertEqual(second["manual_skill"]["status"], "already-reminded")

        # No run.json written
        ctx = self._ctx()
        from harness.codex_direct import _task_dir
        td = _task_dir(ctx, "github-32")
        self.assertFalse((td / "run.json").exists())
        # Bridge reminder marker persisted via shared manual-skill-reminders seam
        reminder_markers = list(
            (ctx.runtime_root / "manual-skill-reminders").rglob("*.json")
        )
        self.assertTrue(reminder_markers, "bridge reminder marker not found")

    def test_bootstrap_rejects_invalid_contract(self) -> None:
        from harness.paseo_collaboration import paseo_bootstrap

        contract = self._contract()
        del contract["plan"]["acceptance_criteria"]
        result, ec = paseo_bootstrap(self._ctx(), contract)
        self.assertNotEqual(ec, 0)
        self.assertEqual(result["state"], "rejected")

    def test_bootstrap_rejects_wrong_mode(self) -> None:
        from harness.paseo_collaboration import paseo_bootstrap

        contract = self._contract(
            execution={
                "mode": "codex-direct",
                "canonical_worktree": str(self.repo.resolve()),
                "base_sha": _git(self.repo, "rev-parse", "HEAD"),
                "branch": "main",
                "adapter_switch_policy": "stop-and-report",
            },
        )
        result, ec = paseo_bootstrap(self._ctx(), contract)
        self.assertEqual(result["state"], "rejected")
        self.assertIn("wrong_mode", result.get("errors", []))

    def test_bootstrap_rejects_bridge_mismatch(self) -> None:
        from harness.paseo_collaboration import paseo_bootstrap

        _write_bridge(self.repo, self._contract())
        # Override contract so contract_digest doesn't match bridge
        contract = self._contract()
        contract["task"]["id"] = "github-99"  # mismatches bridge's "github-32"
        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ):
            result, ec = paseo_bootstrap(self._ctx(), contract)
        self.assertNotEqual(ec, 0)

    # ---- dispatch (finding #21 — serialized) ----

    def test_dispatch_persists_launch_evidence(self) -> None:
        from harness.paseo_collaboration import paseo_bootstrap, paseo_dispatch

        contract = self._contract()
        content = "Implement Issue #32 per the contract."
        hd = hashlib.sha256(content.encode("utf-8")).hexdigest()
        _write_bridge(self.repo, contract, handoff_digest=hd)
        ctx = self._ctx()
        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ):
            paseo_bootstrap(ctx, contract)

        handoff = self.repo / "handoff.md"
        handoff.write_text(content, encoding="utf-8")

        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ):
            launch = paseo_dispatch(ctx, "github-32", handoff)

        self.assertEqual(launch["schema"], "harness.paseo-writer-launch/v1")
        self.assertTrue(isinstance(launch["agent_id"], str) and launch["agent_id"])
        self.assertEqual(
            launch["writer_lease"], {"holder": "claude", "state": "active"}
        )

        # Launch evidence persisted
        from harness.codex_direct import _task_dir
        launch_path = _task_dir(ctx, "github-32") / "launch.json"
        self.assertTrue(launch_path.exists())
        persisted = json.loads(launch_path.read_text(encoding="utf-8"))
        self.assertEqual(persisted["agent_id"], launch["agent_id"])

    def test_dispatch_rejects_second_call(self) -> None:
        from harness.paseo_collaboration import (
            PaseoCollaborationError,
            paseo_bootstrap,
            paseo_dispatch,
        )

        content = "Task handoff."
        hd = hashlib.sha256(content.encode("utf-8")).hexdigest()
        _write_bridge(self.repo, self._contract(), handoff_digest=hd)
        ctx = self._ctx()
        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ):
            paseo_bootstrap(ctx, self._contract())

        handoff = self.repo / "handoff.md"
        handoff.write_text(content, encoding="utf-8")

        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ):
            paseo_dispatch(ctx, "github-32", handoff)

        # Second dispatch must fail
        with self.assertRaises(PaseoCollaborationError) as cm:
            paseo_dispatch(ctx, "github-32", handoff)
        self.assertIn("already_completed", str(cm.exception))

    def test_ephemeral_prompt_refuses_preexisting_hard_links(self) -> None:
        from harness.paseo_collaboration import (
            PaseoCollaborationError,
            _write_ephemeral_prompt,
        )

        outside = self.root / "outside-prompt.txt"
        outside.write_text("outside sentinel", encoding="utf-8")
        task_dir = self.repo / ".harness" / "runtime" / "prompt-test"
        task_dir.mkdir(parents=True)

        for name in ("dispatch-prompt.txt", "repair-prompt.txt"):
            prompt_path = task_dir / name
            os.link(outside, prompt_path)
            with self.assertRaises(PaseoCollaborationError):
                _write_ephemeral_prompt(self._ctx(), prompt_path, "secret prompt")
            self.assertEqual(outside.read_text(encoding="utf-8"), "outside sentinel")
            self.assertTrue(prompt_path.exists(), "untrusted link must not be removed")
            prompt_path.unlink()

    def test_ephemeral_prompt_scrubs_links_added_after_create(self) -> None:
        import harness.paseo_collaboration as collaboration

        prompt_path = self.repo / ".harness" / "runtime" / "dispatch-prompt.txt"
        if os.name != "nt":
            descriptor = collaboration._write_ephemeral_prompt(
                self._ctx(), prompt_path, "sensitive raw handoff"
            )
            self.assertFalse(prompt_path.exists())
            collaboration._unlink_ephemeral_prompt(
                self._ctx(), prompt_path, descriptor
            )
            return

        outside = self.root / "linked-after-create.txt"
        real_write = os.write

        def _link_then_write(descriptor, raw):
            if not outside.exists():
                os.link(prompt_path, outside)
            return real_write(descriptor, raw)

        with patch("harness.paseo_collaboration.os.write", new=_link_then_write):
            with self.assertRaises(collaboration.PaseoCollaborationError):
                collaboration._write_ephemeral_prompt(
                    self._ctx(), prompt_path, "sensitive raw handoff"
                )

        self.assertEqual(outside.read_bytes(), b"")
        self.assertEqual(prompt_path.read_bytes(), b"")
        prompt_path.unlink()
        outside.unlink()

        prompt_path = self.repo / ".harness" / "runtime" / "repair-prompt.txt"
        outside = self.root / "linked-before-cleanup.txt"
        descriptor = collaboration._write_ephemeral_prompt(
            self._ctx(), prompt_path, "sensitive raw review"
        )
        os.link(prompt_path, outside)
        with self.assertRaises(collaboration.PaseoCollaborationError):
            collaboration._unlink_ephemeral_prompt(
                self._ctx(), prompt_path, descriptor
            )
        self.assertEqual(outside.read_bytes(), b"")
        self.assertEqual(prompt_path.read_bytes(), b"")
        prompt_path.unlink()
        outside.unlink()

    def test_verified_prompt_send_rechecks_identity_before_accepting(self) -> None:
        import harness.paseo_collaboration as collaboration

        prompt_path = self.repo / ".harness" / "runtime" / "identity-prompt.txt"
        descriptor = collaboration._write_ephemeral_prompt(
            self._ctx(), prompt_path, "verified prompt"
        )
        try:
            with patch(
                "harness.paseo_collaboration._prompt_identity_matches",
                side_effect=(True, False),
            ) as identity, patch(
                "harness.paseo_collaboration._run_paseo_cli",
                return_value=_make_send_result(),
            ):
                with self.assertRaises(collaboration.PaseoCollaborationError) as cm:
                    collaboration._send_verified_prompt(
                        "agent-test-uuid", prompt_path, descriptor
                    )
        finally:
            collaboration._unlink_ephemeral_prompt(
                self._ctx(), prompt_path, descriptor
            )

        self.assertIn("prompt_identity_changed", str(cm.exception))
        self.assertEqual(identity.call_count, 2)

        with patch.object(collaboration.os, "name", "posix"), patch(
            "harness.paseo_collaboration.os.lseek",
        ), patch(
            "harness.paseo_collaboration._prompt_identity_matches",
            return_value=True,
        ), patch(
            "harness.paseo_collaboration._run_paseo_cli",
            return_value=_make_send_result(),
        ) as run:
            collaboration._send_verified_prompt(
                "agent-test-uuid", Path("dispatch-prompt.txt"), 123
            )

        self.assertEqual(run.call_args.args[3], "/dev/fd/123")
        self.assertEqual(run.call_args.kwargs["pass_fds"], (123,))

    def test_verified_prompt_source_cannot_be_overwritten(self) -> None:
        import harness.paseo_collaboration as collaboration

        prompt_path = self.repo / ".harness" / "runtime" / "sealed-prompt.txt"
        descriptor = collaboration._write_ephemeral_prompt(
            self._ctx(), prompt_path, "verified prompt"
        )

        def _read_delivered_prompt(*args, **_kwargs):
            if prompt_path.exists():
                try:
                    prompt_path.write_text("modified prompt", encoding="utf-8")
                except PermissionError:
                    pass
            self.assertEqual(
                Path(args[3]).read_text(encoding="utf-8"), "verified prompt"
            )
            return _make_send_result()

        try:
            with patch(
                "harness.paseo_collaboration._run_paseo_cli",
                side_effect=_read_delivered_prompt,
            ):
                collaboration._send_verified_prompt(
                    "agent-test-uuid", prompt_path, descriptor
                )
        finally:
            collaboration._unlink_ephemeral_prompt(
                self._ctx(), prompt_path, descriptor
            )

    def test_dispatch_rejects_oversized_handoff(self) -> None:
        from harness.paseo_collaboration import (
            PaseoCollaborationError,
            paseo_bootstrap,
            paseo_dispatch,
        )

        _write_bridge(self.repo, self._contract())
        ctx = self._ctx()
        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ):
            paseo_bootstrap(ctx, self._contract())

        handoff = self.repo / "handoff.md"
        handoff.write_bytes(b"x" * (128 * 1024 + 1))  # exceeds max

        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ):
            with self.assertRaises(PaseoCollaborationError) as cm:
                paseo_dispatch(ctx, "github-32", handoff)
        self.assertIn("oversized", str(cm.exception))

    # ---- report (findings #9, #16) ----

    def test_report_validates_and_persists(self) -> None:
        from harness.paseo_collaboration import (
            paseo_bootstrap,
            paseo_dispatch,
            paseo_report,
        )

        hd = hashlib.sha256(b"Task.").hexdigest()
        _write_bridge(self.repo, self._contract(), handoff_digest=hd)
        ctx = self._ctx()
        side_effect = _paseo_cli_side_effect(str(self.repo))
        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=side_effect,
        ):
            paseo_bootstrap(ctx, self._contract())

            handoff = self.repo / "handoff.md"
            handoff.write_text("Task.", encoding="utf-8")
            paseo_dispatch(ctx, "github-32", handoff)

            # Write and stage an owned file so diff is non-empty
            (self.repo / "harness").mkdir(parents=True, exist_ok=True)
            (self.repo / "harness" / "paseo_collaboration.py").write_text("# seam\n", encoding="utf-8")
            _git(self.repo, "add", "harness/paseo_collaboration.py")
            handoff.unlink()  # remove untracked file so _changed_paths is clean

            from harness.codex_direct import _diff_digest
            diff_digest = _diff_digest(ctx.root)

            report_data = {
                "schema": "harness.paseo-writer-report/v1",
                "task_id": "github-32",
                "mode": "codex-paseo-claude",
                "agent_id": "agent-test-uuid",
                "summary": "Implemented collaboration seam.",
                "files_changed": ["harness/paseo_collaboration.py"],
                "diff_digest": diff_digest,
                "commands": [{"id": "tests", "digest": "aa" * 32, "status": "pass", "exit_code": 0}],
                "skipped_checks": [],
                "risks": [],
                "criterion_evidence": [
                    {
                        "id": "preflight-readonly",
                        "status": "pass",
                        "digest": "cc" * 32,
                    }
                ],
            }
            validated = paseo_report(ctx, "github-32", report_data)
        self.assertEqual(validated["schema"], "harness.paseo-writer-report/v1")
        self.assertEqual(validated["status"], "valid")

    def test_report_rejects_wrong_agent_id(self) -> None:
        from harness.paseo_collaboration import (
            PaseoCollaborationError,
            paseo_bootstrap,
            paseo_dispatch,
            paseo_report,
        )

        hd = hashlib.sha256(b"Task.").hexdigest()
        _write_bridge(self.repo, self._contract(), handoff_digest=hd)
        ctx = self._ctx()
        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ):
            paseo_bootstrap(ctx, self._contract())

        handoff = self.repo / "handoff.md"
        handoff.write_text("Task.", encoding="utf-8")

        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ):
            paseo_dispatch(ctx, "github-32", handoff)


        (self.repo / "harness").mkdir(parents=True, exist_ok=True)
        (self.repo / "harness" / "paseo_collaboration.py").write_text("# x\n", encoding="utf-8")

        report_data = {
            "schema": "harness.paseo-writer-report/v1",
            "task_id": "github-32",
            "mode": "codex-paseo-claude",
            "agent_id": "wrong-agent-id",
            "summary": "Wrong.",
            "files_changed": ["harness/paseo_collaboration.py"],
            "commands": [{"digest": "aa" * 32, "status": "pass", "exit_code": 0}],
            "skipped_checks": [],
            "risks": [],
            "criterion_evidence": [
                {"id": "preflight-readonly", "status": "pass", "digest": "cc" * 32},
            ],
        }
        with self.assertRaises(PaseoCollaborationError) as cm:
            paseo_report(ctx, "github-32", report_data)
        self.assertIn("agent_id_mismatch", str(cm.exception))

    def test_report_rejects_missing_keys(self) -> None:
        from harness.paseo_collaboration import (
            PaseoCollaborationError,
            paseo_report,
        )

        ctx = self._ctx()
        with self.assertRaises(PaseoCollaborationError) as cm:
            paseo_report(ctx, "github-32", {"task_id": "x"})
        self.assertIn("missing_keys", str(cm.exception))

    def test_report_rejects_outside_owned_paths(self) -> None:
        from harness.paseo_collaboration import (
            PaseoCollaborationError,
            paseo_bootstrap,
            paseo_dispatch,
            paseo_report,
        )

        hd = hashlib.sha256(b"Task.").hexdigest()
        _write_bridge(self.repo, self._contract(), handoff_digest=hd)
        ctx = self._ctx()
        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ):
            paseo_bootstrap(ctx, self._contract())

        handoff = self.repo / "handoff.md"
        handoff.write_text("Task.", encoding="utf-8")

        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ):
            paseo_dispatch(ctx, "github-32", handoff)


        (self.repo / "harness").mkdir(parents=True, exist_ok=True)
        (self.repo / "harness" / "paseo_collaboration.py").write_text("# x\n", encoding="utf-8")
        (self.repo / "src" / "index.ts").parent.mkdir(parents=True, exist_ok=True)
        (self.repo / "src" / "index.ts").write_text("// not owned\n", encoding="utf-8")

        report_data = {
            "schema": "harness.paseo-writer-report/v1",
            "task_id": "github-32",
            "mode": "codex-paseo-claude",
            "agent_id": "agent-test-uuid",
            "summary": "Outside owned paths.",
            "files_changed": [
                "harness/paseo_collaboration.py",
                "src/index.ts",  # NOT in owned_paths
            ],
            "commands": [{"digest": "aa" * 32, "status": "pass", "exit_code": 0}],
            "skipped_checks": [],
            "risks": [],
            "criterion_evidence": [
                {"id": "preflight-readonly", "status": "pass", "digest": "cc" * 32},
            ],
        }
        with self.assertRaises(PaseoCollaborationError) as cm:
            paseo_report(ctx, "github-32", report_data)
        self.assertIn("unowned_path", str(cm.exception))

    def test_report_requires_exact_criterion_coverage(self) -> None:
        from harness.paseo_collaboration import (
            PaseoCollaborationError,
            paseo_bootstrap,
            paseo_dispatch,
            paseo_report,
        )

        hd = hashlib.sha256(b"Task.").hexdigest()
        _write_bridge(self.repo, self._contract(), handoff_digest=hd)
        ctx = self._ctx()
        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ):
            paseo_bootstrap(ctx, self._contract())

        handoff = self.repo / "handoff.md"
        handoff.write_text("Task.", encoding="utf-8")

        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ):
            paseo_dispatch(ctx, "github-32", handoff)


        (self.repo / "harness").mkdir(parents=True, exist_ok=True)
        (self.repo / "harness" / "paseo_collaboration.py").write_text("# x\n", encoding="utf-8")
        _git(self.repo, "add", "harness/paseo_collaboration.py")
        handoff.unlink()  # cleanup for clean _changed_paths

        from harness.codex_direct import _diff_digest
        diff_digest = _diff_digest(ctx.root)

        # Missing the criterion — only 1 required, we provide 0
        report_data = {
            "schema": "harness.paseo-writer-report/v1",
            "task_id": "github-32",
            "mode": "codex-paseo-claude",
            "agent_id": "agent-test-uuid",
            "summary": "Missing criterion.",
            "files_changed": ["harness/paseo_collaboration.py"],
            "diff_digest": diff_digest,
            "commands": [{"id": "tests", "digest": "aa" * 32, "status": "pass", "exit_code": 0}],
            "skipped_checks": [],
            "risks": [],
            "criterion_evidence": [],
        }
        with self.assertRaises(PaseoCollaborationError) as cm:
            paseo_report(ctx, "github-32", report_data)
        self.assertIn("criterion", str(cm.exception).lower())

    # ---- Slice 6: strict secret-free report ---------------------------------

    def test_slice6_report_rejects_forbidden_command_keys(self) -> None:
        """Red: commands with forbidden keys (raw, stdout, env, tokens, etc.)
        should be rejected, but the current validator only checks digest/exit_code."""
        from harness.paseo_collaboration import (
            PaseoCollaborationError,
            paseo_bootstrap,
            paseo_dispatch,
            paseo_report,
        )

        hd = hashlib.sha256(b"Slice 6.").hexdigest()
        _write_bridge(self.repo, self._contract(), handoff_digest=hd)
        ctx = self._ctx()
        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ):
            paseo_bootstrap(ctx, self._contract())

        handoff = self.repo / "handoff.md"
        handoff.write_text("Slice 6.", encoding="utf-8")
        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ):
            paseo_dispatch(ctx, "github-32", handoff)

        (self.repo / "harness").mkdir(parents=True, exist_ok=True)
        owned = self.repo / "harness" / "paseo_collaboration.py"
        owned.write_text("# slice6\n", encoding="utf-8")
        _git(self.repo, "add", str(owned.relative_to(self.repo)))

        from harness.codex_direct import _diff_digest
        diff_digest = _diff_digest(ctx.root)

        # 1. Command with forbidden key ``raw`` (a raw command string)
        report_bad_cmd = {
            "schema": "harness.paseo-writer-report/v1",
            "task_id": "github-32", "mode": "codex-paseo-claude",
            "agent_id": "agent-test-uuid",
            "summary": "Slice 6 forbidden command keys.",
            "files_changed": ["harness/paseo_collaboration.py"],
            "diff_digest": diff_digest,
            "commands": [{
                "digest": "aa" * 32, "exit_code": 0,
                "raw": "npm test",  # FORBIDDEN: raw command string
            }],
            "skipped_checks": [], "risks": [],
            "criterion_evidence": [
                {"id": "preflight-readonly", "status": "pass",
                 "digest": "cc" * 32},
            ],
        }
        # RED: should raise, currently accepts
        with self.assertRaises(PaseoCollaborationError):
            paseo_report(ctx, "github-32", report_bad_cmd)

        # 2. Duplicate criterion evidence IDs
        _git(self.repo, "checkout", "--", "harness/paseo_collaboration.py")
        owned.write_text("# slice6b\n", encoding="utf-8")
        diff_digest = _diff_digest(ctx.root)
        report_dup = {
            "schema": "harness.paseo-writer-report/v1",
            "task_id": "github-32", "mode": "codex-paseo-claude",
            "agent_id": "agent-test-uuid",
            "summary": "Slice 6 duplicate evidence IDs.",
            "files_changed": ["harness/paseo_collaboration.py"],
            "diff_digest": diff_digest,
            "commands": [{"digest": "aa" * 32, "status": "pass", "exit_code": 0}], "skipped_checks": [], "risks": [],
            "criterion_evidence": [
                {"id": "preflight-readonly", "status": "pass",
                 "digest": "dd" * 32},
                {"id": "preflight-readonly", "status": "pass",
                 "digest": "ee" * 32},  # duplicate id
            ],
        }
        # RED: should raise on duplicate IDs, currently dedupes silently
        with self.assertRaises(PaseoCollaborationError):
            paseo_report(ctx, "github-32", report_dup)

    # ---- Slice 7: positive lifecycle (accept → commit → idempotent) ---------

    def test_shared_fixture_drives_public_paseo_lifecycle(self) -> None:
        """Full lifecycle: bootstrap → dispatch → report → accept → commit
        → second commit idempotent.  Validates the happy path that the
        existing negative-only test does not cover."""
        from harness.paseo_collaboration import (
            collaboration_accept,
            collaboration_advance,
            collaboration_commit,
            collaboration_record_check,
            paseo_bootstrap,
            paseo_dispatch,
        )
        from harness.codex_direct import _diff_digest

        matrix = json.loads(
            (ROOT / "harness/fixtures/three-adapter-conformance.json").read_text(
                encoding="utf-8"
            )
        )
        adapter = next(
            item for item in matrix["adapters"]
            if item["mode"] == "codex-paseo-claude"
        )

        # Track owned file BEFORE bootstrap so baseline includes it
        (self.repo / "harness").mkdir(parents=True, exist_ok=True)
        owned = self.repo / "harness" / "paseo_collaboration.py"
        owned.write_text("# base\n", encoding="utf-8")
        _git(self.repo, "add", str(owned.relative_to(self.repo)))
        _git(self.repo, "commit", "-m", "track owned file")

        # Contract with a non-required review check to satisfy accept
        contract = self._contract()
        contract["execution"]["mode"] = adapter["mode"]
        contract["writer_lease"]["holder"] = adapter["writer"]
        contract["acceptance_owner"] = adapter["acceptance_owner"]
        contract["required_manual_skills"] = [{
            "name": "implement",
            "host": adapter["skill_host"],
            "status": "invoked",
            "invocation": adapter["skill_invocation"],
        }]
        contract["plan"]["verification_plan"].append(
            {"id": "review", "command": "code-review", "required": False}
        )

        content = "Implement Issue #32."
        hd = hashlib.sha256(content.encode("utf-8")).hexdigest()
        _write_bridge(self.repo, contract, handoff_digest=hd)
        ctx = self._ctx()
        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ):
            paseo_bootstrap(ctx, contract)

        handoff = self.repo / "handoff.md"
        handoff.write_text(content, encoding="utf-8")
        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ):
            paseo_dispatch(ctx, "github-32", handoff)


        # Modify tracked file (unstaged) for diff
        owned.write_text("# lifecycle\n", encoding="utf-8")
        diff_digest = _diff_digest(ctx.root)

        # Write a valid report.json
        import json as _json
        task_dir = self.repo / ".harness" / "runtime"
        run_candidates = list(task_dir.rglob("run.json"))
        self.assertTrue(run_candidates)
        task_dir = run_candidates[0].parent
        # Bind the manual report to the launch sidecar through the shared
        # serialization seam (acceptance recomputes the same digest).
        from harness.paseo_collaboration import _launch_digest
        launch_data = json.loads(
            (task_dir / "launch.json").read_text("utf-8")
        )
        report_data = {
            "schema": "harness.paseo-writer-report/v1",
            "task_id": "github-32", "mode": "codex-paseo-claude",
            "agent_id": "agent-test-uuid",
            "summary": "Full lifecycle test report.",
            "files_changed": ["harness/paseo_collaboration.py"],
            "diff_digest": diff_digest,
            "commands": [{"digest": "aa" * 32, "status": "pass", "exit_code": 0}],
            "skipped_checks": [], "risks": [],
            "criterion_evidence": [
                {"id": "preflight-readonly", "status": "pass",
                 "digest": "cc" * 32},
            ],
            "launch_digest": _launch_digest(launch_data),
        }
        from harness.codex_direct import _write_json
        _write_json(ctx, task_dir / "report.json", report_data)

        # Advance state: executing → verifying → reviewing
        collaboration_advance(ctx, task_id="github-32", target="verifying")
        collaboration_advance(ctx, task_id="github-32", target="reviewing")

        # Record required check evidence (accept_codex_direct checks diff_digest
        # internally, so the evidence must match the current staged diff)
        collaboration_record_check(
            ctx, task_id="github-32",
            check_id="tests", status="pass",
            source="command",
            exit_code=0, sensitivity="secret-free", digest="ab" * 32,
            reason_code=None,
        )
        # Record review-sourced evidence (required by accept_codex_direct)
        collaboration_record_check(
            ctx, task_id="github-32",
            check_id="review", status="pass",
            source="review",
            exit_code=None, sensitivity="secret-free", digest="cd" * 32,
            reason_code=None,
        )

        # Judge criterion using the passing check digest
        from harness.paseo_collaboration import collaboration_judge
        collaboration_judge(
            ctx, task_id="github-32",
            criterion_id="preflight-readonly", status="pass",
            evidence_digest="ab" * 32,
        )

        # Accept — accept_codex_direct commits internally after state
        # transition, so the commit already exists by the time it returns.
        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ):
            result = collaboration_accept(ctx, task_id="github-32")
        self.assertEqual(
            result.get("schema"),
            adapter["control_schema"],
        )
        self.assertEqual(result.get("mode"), adapter["mode"])
        accept_sha = result.get("commit_sha")
        self.assertIsNotNone(accept_sha)
        self.assertEqual(result.get("commit_status"), "created")

        # Prove exactly one HEAD delta above baseline
        baseline = contract["execution"]["base_sha"]
        rev_list = _git(
            self.repo, "rev-list", "--count", f"{baseline}..HEAD",
        ).strip()
        self.assertEqual(rev_list, "1", "exactly one commit above baseline")

        # First explicit commit — idempotent seam recognizes the exact
        # accepted commit and returns already-committed.
        committed = collaboration_commit(
            ctx, task_id="github-32", message="chore(harness): accepted"
        )
        self.assertIn("commit_sha", committed)
        self.assertEqual(committed.get("commit_status"), "already-committed")
        self.assertEqual(committed["commit_sha"], accept_sha)

        # Second explicit commit — same idempotent guard, no new delta.
        committed2 = collaboration_commit(
            ctx, task_id="github-32", message="chore(harness): again"
        )
        self.assertEqual(committed2.get("commit_status"), "already-committed")
        self.assertEqual(committed2["commit_sha"], accept_sha)

        # Still exactly one HEAD delta
        rev_list2 = _git(
            self.repo, "rev-list", "--count", f"{baseline}..HEAD",
        ).strip()
        self.assertEqual(rev_list2, "1", "still exactly one commit above baseline")

        # Verify no remote was pushed — only local commits
        self.assertFalse(committed.get("pushed", False))

    # ---- repair (findings #10, #18) ----

    def test_repair_routes_to_same_agent(self) -> None:
        import harness.codex_direct as controller
        from harness.paseo_collaboration import paseo_bootstrap, paseo_dispatch, paseo_repair

        hd = hashlib.sha256(b"Task.").hexdigest()
        _write_bridge(self.repo, self._contract(), handoff_digest=hd)
        ctx = self._ctx()
        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ):
            paseo_bootstrap(ctx, self._contract())

        handoff = self.repo / "handoff.md"
        handoff.write_text("Task.", encoding="utf-8")

        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ):
            paseo_dispatch(ctx, "github-32", handoff)

        # Advance to verifying for repair eligibility
        controller.advance_codex_direct(
            ctx, task_id="github-32", target="verifying",
            expected_mode="codex-paseo-claude",
        )

        review_file = self.repo / "review.md"
        review_file.write_text("Fix: use real Paseo CLI shapes.", encoding="utf-8")

        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ):
            result, ec = paseo_repair(ctx, "github-32", review_file)
        self.assertEqual(ec, 0)
        # Repair must advance run state to repairing
        self.assertIn("repairing", result.get("state", ""))

    # ---- Slice 3+5: locked repair (prepared-intent at-most-once) -----------

    def test_slice35_repair_rejected_by_prepared_intent(self) -> None:
        """Strong regression: a leftover repair-pending-1.json (prepared intent
        for the current attempt) blocks re-repair."""
        from harness.paseo_collaboration import (
            PaseoCollaborationError,
            paseo_bootstrap,
            paseo_dispatch,
            paseo_repair,
        )

        hd = hashlib.sha256(b"Slice 3+5.").hexdigest()
        _write_bridge(self.repo, self._contract(), handoff_digest=hd)
        ctx = self._ctx()
        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ):
            paseo_bootstrap(ctx, self._contract())

        handoff = self.repo / "handoff.md"
        handoff.write_text("Slice 3+5.", encoding="utf-8")
        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ):
            paseo_dispatch(ctx, "github-32", handoff)

        import harness.codex_direct as controller
        controller.advance_codex_direct(
            ctx, task_id="github-32", target="verifying",
            expected_mode="codex-paseo-claude",
        )

        # Simulate crash after prepared intent write: place repair-pending-1.json
        from harness.codex_direct import _task_dir
        task_dir = _task_dir(ctx, "github-32")
        pending_path = task_dir / "repair-pending-1.json"
        pending_path.write_text(json.dumps({
            "schema": "harness.repair-pending/v1",
            "status": "prepared",
        }), encoding="utf-8")

        review_file = self.repo / "review.md"
        review_file.write_text("Fix something.", encoding="utf-8")

        with self.assertRaises(PaseoCollaborationError) as cm:
            paseo_repair(ctx, "github-32", review_file)
        self.assertIn("already_pending", str(cm.exception))

    # ---- Slice 8: acceptance blocks pending dispatch/repair ---------------

    def test_slice8_accept_blocked_by_pending_dispatch(self) -> None:
        """Strong regression: acceptance refuses when dispatch-pending.json
        exists without launch.json (ambiguous dispatch)."""
        from harness.paseo_collaboration import (
            PaseoCollaborationError,
            collaboration_accept,
            paseo_bootstrap,
        )

        _write_bridge(self.repo, self._contract())
        ctx = self._ctx()
        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ):
            paseo_bootstrap(ctx, self._contract())

        # Place a pending dispatch without launch (ambiguous state)
        from harness.codex_direct import _task_dir
        task_dir = _task_dir(ctx, "github-32")
        pending_path = task_dir / "dispatch-pending.json"
        pending_path.write_text(json.dumps({
            "schema": "harness.dispatch-pending/v1",
            "status": "prepared",
        }), encoding="utf-8")

        with self.assertRaises(PaseoCollaborationError) as cm:
            collaboration_accept(ctx, task_id="github-32")
        self.assertIn("pending_dispatch", str(cm.exception))

    # ---- final review (fixes 1-5) ------------------------------------------

    def test_fix1_preflight_accepts_reachable_daemon(self) -> None:
        """Paseo 0.2.5 spells a healthy connected daemon ``reachable``;
        preflight must accept it while still rejecting unreachable."""
        from harness.paseo_collaboration import paseo_preflight

        def _effect(*args: str, **kwargs) -> object:
            if args and args[0] == "daemon":
                return {
                    "localDaemon": "running",
                    "connectedDaemon": "reachable",
                    "daemonVersion": "0.2.5",
                    "cliVersion": "0.2.5",
                }
            return _paseo_cli_side_effect(str(self.repo))(*args, **kwargs)

        with patch(
            "harness.paseo_collaboration._run_paseo_cli", side_effect=_effect
        ):
            result = paseo_preflight(self._ctx())
        self.assertTrue(result["available"])

        def _bad_effect(*args: str, **kwargs) -> object:
            if args and args[0] == "daemon":
                return {
                    "localDaemon": "running",
                    "connectedDaemon": "unreachable",
                    "daemonVersion": "0.2.5",
                    "cliVersion": "0.2.5",
                }
            return _paseo_cli_side_effect(str(self.repo))(*args, **kwargs)

        with patch(
            "harness.paseo_collaboration._run_paseo_cli", side_effect=_bad_effect
        ):
            result = paseo_preflight(self._ctx())
        self.assertFalse(result["available"])
        self.assertIn("daemon_not_connected", result["error"])

    def test_fix2_report_rejects_risk_extra_keys(self) -> None:
        """Report nested objects accept only their exact key sets; an extra
        key on a risk (token) is rejected, never persisted."""
        from harness.paseo_collaboration import (
            PaseoCollaborationError,
            paseo_bootstrap,
            paseo_dispatch,
            paseo_report,
        )

        hd = hashlib.sha256(b"Task.").hexdigest()
        _write_bridge(self.repo, self._contract(), handoff_digest=hd)
        ctx = self._ctx()
        side_effect = _paseo_cli_side_effect(str(self.repo))
        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=side_effect,
        ):
            paseo_bootstrap(ctx, self._contract())

            handoff = self.repo / "handoff.md"
            handoff.write_text("Task.", encoding="utf-8")
            paseo_dispatch(ctx, "github-32", handoff)

            (self.repo / "harness").mkdir(parents=True, exist_ok=True)
            (self.repo / "harness" / "paseo_collaboration.py").write_text(
                "# seam\n", encoding="utf-8")
            _git(self.repo, "add", "harness/paseo_collaboration.py")
            handoff.unlink()

            from harness.codex_direct import _diff_digest
            diff_digest = _diff_digest(ctx.root)

            report_data = {
                "schema": "harness.paseo-writer-report/v1",
                "task_id": "github-32",
                "mode": "codex-paseo-claude",
                "agent_id": "agent-test-uuid",
                "summary": "Implemented collaboration seam.",
                "files_changed": ["harness/paseo_collaboration.py"],
                "diff_digest": diff_digest,
                "commands": [{"id": "tests", "digest": "aa" * 32, "status": "pass", "exit_code": 0}],
                "skipped_checks": [],
                "risks": [
                    {"id": "r1", "detail": "leftover", "token": "secret-value"},
                ],
                "criterion_evidence": [
                    {
                        "id": "preflight-readonly",
                        "status": "pass",
                        "digest": "cc" * 32,
                    }
                ],
            }
            with self.assertRaises(PaseoCollaborationError) as cm:
                paseo_report(ctx, "github-32", report_data)
            self.assertIn("report_risk_0_extra_keys", str(cm.exception))

    def test_fix3_two_sequential_repairs_attempt_keyed(self) -> None:
        """Completed repair dispatch evidence must not block the next
        authorized attempt; a prepared intent for the current attempt blocks
        replay.  Evidence is attempt-keyed, not a singleton."""
        import harness.codex_direct as controller
        from harness.paseo_collaboration import (
            PaseoCollaborationError,
            collaboration_accept,
            paseo_bootstrap,
            paseo_dispatch,
            paseo_repair,
        )

        hd = hashlib.sha256(b"Fix3.").hexdigest()
        _write_bridge(self.repo, self._contract(), handoff_digest=hd)
        ctx = self._ctx()
        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ):
            paseo_bootstrap(ctx, self._contract())

        handoff = self.repo / "handoff.md"
        handoff.write_text("Fix3.", encoding="utf-8")
        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ):
            paseo_dispatch(ctx, "github-32", handoff)

        from harness.codex_direct import _task_dir
        task_dir = _task_dir(ctx, "github-32")

        def _advance() -> None:
            controller.advance_codex_direct(
                ctx, task_id="github-32", target="verifying",
                expected_mode="codex-paseo-claude",
            )

        def _repair(text: str) -> int:
            review_file = self.repo / "review.md"
            review_file.write_text(text, encoding="utf-8")
            with patch(
                "harness.paseo_collaboration._run_paseo_cli",
                side_effect=_paseo_cli_side_effect(str(self.repo)),
            ):
                _result, ec = paseo_repair(ctx, "github-32", review_file)
            return ec

        # Attempt 1 completes: dispatch evidence present, pending removed.
        _advance()
        self.assertEqual(_repair("Fix A."), 0)
        self.assertTrue((task_dir / "repair-dispatch-1.json").exists())
        self.assertFalse((task_dir / "repair-pending-1.json").exists())

        # A prepared intent for the CURRENT attempt (2) blocks replay...
        _advance()
        (task_dir / "repair-pending-2.json").write_text(json.dumps({
            "schema": "harness.repair-pending/v1",
            "status": "prepared",
            "attempt": 2,
        }), encoding="utf-8")
        with self.assertRaises(PaseoCollaborationError) as cm:
            _repair("Fix B.")
        self.assertIn("already_pending", str(cm.exception))

        # ...but a COMPLETED prior attempt never blocks: after clearing the
        # prepared intent, attempt 2 proceeds (state is still verifying).
        (task_dir / "repair-pending-2.json").unlink()
        self.assertEqual(_repair("Fix B."), 0)
        self.assertTrue((task_dir / "repair-dispatch-2.json").exists())
        self.assertFalse((task_dir / "repair-pending-2.json").exists())

        # Acceptance blocks only a pending-N lacking dispatch-N.
        (task_dir / "repair-pending-3.json").write_text(json.dumps({
            "schema": "harness.repair-pending/v1",
            "status": "prepared",
            "attempt": 3,
        }), encoding="utf-8")
        with self.assertRaises(PaseoCollaborationError) as cm:
            collaboration_accept(ctx, task_id="github-32")
        self.assertIn("pending_repair", str(cm.exception))
        (task_dir / "repair-pending-3.json").unlink()

    def test_fix4_accept_rejects_tampered_launch_agent_id(self) -> None:
        """Acceptance binds identity to the frozen run record: a tampered
        launch.json agent ID is rejected before any unlocked acceptance."""
        from harness.paseo_collaboration import (
            PaseoCollaborationError,
            collaboration_accept,
            paseo_bootstrap,
            paseo_dispatch,
        )

        hd = hashlib.sha256(b"Fix4.").hexdigest()
        _write_bridge(self.repo, self._contract(), handoff_digest=hd)
        ctx = self._ctx()
        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ):
            paseo_bootstrap(ctx, self._contract())

        handoff = self.repo / "handoff.md"
        handoff.write_text("Fix4.", encoding="utf-8")
        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ):
            paseo_dispatch(ctx, "github-32", handoff)

        from harness.codex_direct import _task_dir
        task_dir = _task_dir(ctx, "github-32")
        # Minimal report evidence: schema/task_id checks precede the
        # launch-agent binding, which must fire first.
        (task_dir / "report.json").write_text(json.dumps({
            "schema": "harness.paseo-writer-report/v1",
            "task_id": "github-32",
            "agent_id": "agent-test-uuid",
        }), encoding="utf-8")

        launch_path = task_dir / "launch.json"
        launch_data = json.loads(launch_path.read_text("utf-8"))
        launch_data["agent_id"] = "agent-tampered-uuid"
        launch_path.write_text(json.dumps(launch_data), encoding="utf-8")

        with self.assertRaises(PaseoCollaborationError) as cm:
            collaboration_accept(ctx, task_id="github-32")
        self.assertIn("agent_id_mismatch", str(cm.exception))

    def test_fix5_bootstrap_inspect_list_enters_recovery(self) -> None:
        """Post-launch malformed inspect output (list, not dict) routes to
        the shared Recovery Bundle path, preserves the candidate agent ID,
        and never surfaces an AttributeError."""
        from harness.paseo_collaboration import paseo_bootstrap

        hd = hashlib.sha256(b"Fix5.").hexdigest()
        _write_bridge(self.repo, self._contract(), handoff_digest=hd)
        ctx = self._ctx()

        def _effect(*args: str, **kwargs) -> object:
            cmd = args[0] if args else ""
            if cmd == "inspect":
                return ["not", "a", "dict"]
            return _paseo_cli_side_effect(str(self.repo))(*args, **kwargs)

        with patch(
            "harness.paseo_collaboration._run_paseo_cli", side_effect=_effect
        ):
            result, ec = paseo_bootstrap(ctx, self._contract())
        self.assertEqual(ec, 6)
        self.assertEqual(result["state"], "recovery-required")

        runtime_dir = self.repo / ".harness" / "runtime"
        candidates = list(runtime_dir.rglob("run.json"))
        self.assertTrue(candidates, "run.json not found")
        run_data = json.loads(candidates[0].read_text("utf-8"))
        self.assertEqual(run_data["agent_id"], "agent-test-uuid")
        self.assertNotIn("error", run_data)
        failure = run_data["recovery_bundle"]["failure"]
        self.assertEqual(failure["category"], "adapter-failure")
        self.assertRegex(failure["fingerprint"], r"^[0-9a-f]{64}$")

    def test_fix6_dispatch_rejects_tampered_handoff_digest(self) -> None:
        """After bootstrap freezes the handoff digest into run.json, dispatch
        must raise before any send when (a) the mutable bridge trigger is
        swapped to another valid digest or (b) the handoff bytes change."""
        from harness.codex_direct import _task_dir
        from harness.paseo_collaboration import (
            PaseoCollaborationError,
            paseo_bootstrap,
            paseo_dispatch,
        )

        hd = hashlib.sha256(b"Fix6.").hexdigest()
        _write_bridge(self.repo, self._contract(), handoff_digest=hd)
        ctx = self._ctx()
        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ):
            paseo_bootstrap(ctx, self._contract())

        handoff = self.repo / "handoff.md"
        handoff.write_text("Fix6.", encoding="utf-8")

        bridge_path = (
            self.repo / ".harness" / "coordination" / "github-32"
            / "bridge-trigger.json"
        )
        launch_path = _task_dir(ctx, "github-32") / "launch.json"

        def _dispatch_and_record() -> list[str]:
            calls: list[str] = []

            def _effect(*args: str, **kwargs) -> object:
                calls.append(args[0] if args else "")
                return _paseo_cli_side_effect(str(self.repo))(*args, **kwargs)

            with patch(
                "harness.paseo_collaboration._run_paseo_cli",
                side_effect=_effect,
            ):
                with self.assertRaises(PaseoCollaborationError):
                    paseo_dispatch(ctx, "github-32", handoff)
            return calls

        # (a) bridge digest mutated to another valid digest
        bridge_data = json.loads(bridge_path.read_text("utf-8"))
        bridge_data["handoff_digest"] = hashlib.sha256(b"Other.").hexdigest()
        bridge_path.write_text(json.dumps(bridge_data), encoding="utf-8")
        calls = _dispatch_and_record()
        self.assertNotIn("send", calls)
        self.assertFalse(launch_path.exists(),
                         "no launch.json after bridge digest rejection")

        # (b) bridge restored, handoff bytes mutated
        bridge_data["handoff_digest"] = hd
        bridge_path.write_text(json.dumps(bridge_data), encoding="utf-8")
        handoff.write_text("Tampered.", encoding="utf-8")
        calls = _dispatch_and_record()
        self.assertNotIn("send", calls)
        self.assertFalse(launch_path.exists(),
                         "no launch.json after handoff digest rejection")

    def test_fix7_report_rejects_tampered_launch_agent_id(self) -> None:
        """Report binds the mutable launch sidecar to run.agent_id before any
        live inspect: a tampered launch agent_id is rejected and no
        report.json is persisted."""
        from harness.codex_direct import _diff_digest, _task_dir
        from harness.paseo_collaboration import (
            PaseoCollaborationError,
            paseo_bootstrap,
            paseo_dispatch,
            paseo_report,
        )

        hd = hashlib.sha256(b"Fix7.").hexdigest()
        _write_bridge(self.repo, self._contract(), handoff_digest=hd)
        ctx = self._ctx()
        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ):
            paseo_bootstrap(ctx, self._contract())

            handoff = self.repo / "handoff.md"
            handoff.write_text("Fix7.", encoding="utf-8")
            paseo_dispatch(ctx, "github-32", handoff)

            # Write and stage an owned file so diff is non-empty
            (self.repo / "harness").mkdir(parents=True, exist_ok=True)
            (self.repo / "harness" / "paseo_collaboration.py").write_text(
                "# seam\n", encoding="utf-8")
            _git(self.repo, "add", "harness/paseo_collaboration.py")
            handoff.unlink()  # remove untracked file so _changed_paths is clean

            diff_digest = _diff_digest(ctx.root)

            # Tamper the mutable launch sidecar: agent_id no longer matches
            # the frozen run.agent_id.
            task_dir = _task_dir(ctx, "github-32")
            launch_path = task_dir / "launch.json"
            launch_data = json.loads(launch_path.read_text("utf-8"))
            launch_data["agent_id"] = "agent-tampered-uuid"
            launch_path.write_text(json.dumps(launch_data), encoding="utf-8")

            report_data = {
                "schema": "harness.paseo-writer-report/v1",
                "task_id": "github-32",
                "mode": "codex-paseo-claude",
                "agent_id": "agent-test-uuid",
                "summary": "Implemented collaboration seam.",
                "files_changed": ["harness/paseo_collaboration.py"],
                "diff_digest": diff_digest,
                "commands": [{"id": "tests", "digest": "aa" * 32,
                              "status": "pass", "exit_code": 0}],
                "skipped_checks": [],
                "risks": [],
                "criterion_evidence": [
                    {"id": "preflight-readonly", "status": "pass",
                     "digest": "cc" * 32},
                ],
            }
            calls: list[str] = []

            def _effect(*args: str, **kwargs) -> object:
                calls.append(args[0] if args else "")
                return _paseo_cli_side_effect(str(self.repo))(*args, **kwargs)

            with patch(
                "harness.paseo_collaboration._run_paseo_cli",
                side_effect=_effect,
            ):
                with self.assertRaises(PaseoCollaborationError) as cm:
                    paseo_report(ctx, "github-32", report_data)
            self.assertIn("report_launch_agent_id_mismatch", str(cm.exception))
            self.assertNotIn("inspect", calls)
            self.assertFalse(
                (task_dir / "report.json").exists(),
                "tampered launch must not persist report.json",
            )

    def test_fix8_accept_rejects_diff_changed_since_report(self) -> None:
        """Acceptance compares the normalized report against the CURRENT diff:
        mutating the owned file after a valid report raises
        acceptance_diff_changed_since_report before live inspect/commit and
        leaves HEAD unchanged."""
        from harness.codex_direct import _diff_digest
        from harness.paseo_collaboration import (
            PaseoCollaborationError,
            collaboration_accept,
            paseo_bootstrap,
            paseo_dispatch,
            paseo_report,
        )

        hd = hashlib.sha256(b"Fix8.").hexdigest()
        _write_bridge(self.repo, self._contract(), handoff_digest=hd)
        ctx = self._ctx()
        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ):
            paseo_bootstrap(ctx, self._contract())

            handoff = self.repo / "handoff.md"
            handoff.write_text("Fix8.", encoding="utf-8")
            paseo_dispatch(ctx, "github-32", handoff)

            owned_file = self.repo / "harness" / "paseo_collaboration.py"
            owned_file.parent.mkdir(parents=True, exist_ok=True)
            owned_file.write_text("# seam\n", encoding="utf-8")
            _git(self.repo, "add", "harness/paseo_collaboration.py")
            handoff.unlink()  # remove untracked file so _changed_paths is clean

            diff_digest = _diff_digest(ctx.root)

            report_data = {
                "schema": "harness.paseo-writer-report/v1",
                "task_id": "github-32",
                "mode": "codex-paseo-claude",
                "agent_id": "agent-test-uuid",
                "summary": "Implemented collaboration seam.",
                "files_changed": ["harness/paseo_collaboration.py"],
                "diff_digest": diff_digest,
                "commands": [{"id": "tests", "digest": "aa" * 32,
                              "status": "pass", "exit_code": 0}],
                "skipped_checks": [],
                "risks": [],
                "criterion_evidence": [
                    {"id": "preflight-readonly", "status": "pass",
                     "digest": "cc" * 32},
                ],
            }
            paseo_report(ctx, "github-32", report_data)  # persists report.json

            # Mutate the same owned file AFTER the report: same path set,
            # different content digest.
            owned_file.write_text("# mutated\n", encoding="utf-8")

            head_before = _git(self.repo, "rev-parse", "HEAD")
            calls: list[str] = []

            def _effect(*args: str, **kwargs) -> object:
                calls.append(args[0] if args else "")
                return _paseo_cli_side_effect(str(self.repo))(*args, **kwargs)

            with patch(
                "harness.paseo_collaboration._run_paseo_cli",
                side_effect=_effect,
            ):
                with self.assertRaises(PaseoCollaborationError) as cm:
                    collaboration_accept(ctx, task_id="github-32")
            self.assertIn("acceptance_diff_changed_since_report",
                          str(cm.exception))
            self.assertNotIn("inspect", calls)
            self.assertEqual(_git(self.repo, "rev-parse", "HEAD"), head_before,
                             "HEAD must be unchanged after rejection")

    def test_fix9_undelivered_repair_blocks_repair_and_accept(self) -> None:
        """Losing repair-dispatch evidence after a completed attempt 1 (crash
        simulation) blocks a second paseo_repair and collaboration_accept;
        no second send and HEAD stays unchanged."""
        import harness.codex_direct as controller
        from harness.codex_direct import _diff_digest, _task_dir
        from harness.paseo_collaboration import (
            PaseoCollaborationError,
            collaboration_accept,
            paseo_bootstrap,
            paseo_dispatch,
            paseo_repair,
            paseo_report,
        )

        hd = hashlib.sha256(b"Fix9.").hexdigest()
        _write_bridge(self.repo, self._contract(), handoff_digest=hd)
        ctx = self._ctx()
        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ):
            paseo_bootstrap(ctx, self._contract())

            handoff = self.repo / "handoff.md"
            handoff.write_text("Fix9.", encoding="utf-8")
            paseo_dispatch(ctx, "github-32", handoff)

            owned_file = self.repo / "harness" / "paseo_collaboration.py"
            owned_file.parent.mkdir(parents=True, exist_ok=True)
            owned_file.write_text("# seam\n", encoding="utf-8")
            _git(self.repo, "add", "harness/paseo_collaboration.py")
            handoff.unlink()  # remove untracked file so _changed_paths is clean

            diff_digest = _diff_digest(ctx.root)
            report_data = {
                "schema": "harness.paseo-writer-report/v1",
                "task_id": "github-32",
                "mode": "codex-paseo-claude",
                "agent_id": "agent-test-uuid",
                "summary": "Implemented collaboration seam.",
                "files_changed": ["harness/paseo_collaboration.py"],
                "diff_digest": diff_digest,
                "commands": [{"id": "tests", "digest": "aa" * 32,
                              "status": "pass", "exit_code": 0}],
                "skipped_checks": [],
                "risks": [],
                "criterion_evidence": [
                    {"id": "preflight-readonly", "status": "pass",
                     "digest": "cc" * 32},
                ],
            }
            paseo_report(ctx, "github-32", report_data)

        task_dir = _task_dir(ctx, "github-32")

        def _advance() -> None:
            controller.advance_codex_direct(
                ctx, task_id="github-32", target="verifying",
                expected_mode="codex-paseo-claude",
            )

        def _repair(text: str) -> None:
            review_file = self.repo / "review.md"
            review_file.write_text(text, encoding="utf-8")
            with patch(
                "harness.paseo_collaboration._run_paseo_cli",
                side_effect=_paseo_cli_side_effect(str(self.repo)),
            ):
                _result, ec = paseo_repair(ctx, "github-32", review_file)
            self.assertEqual(ec, 0)

        # Attempt 1 completes: run.repairs[0] and dispatch evidence agree.
        _advance()
        _repair("Fix A.")
        run_data = json.loads((task_dir / "run.json").read_text("utf-8"))
        self.assertEqual(len(run_data["repairs"]), 1)
        self.assertEqual(run_data["repairs"][0]["attempt"], 1)
        self.assertTrue((task_dir / "repair-dispatch-1.json").exists())

        # Simulate crash: only the dispatch sidecar is lost.
        (task_dir / "repair-dispatch-1.json").unlink()

        head_before = _git(self.repo, "rev-parse", "HEAD")
        calls: list[str] = []

        def _effect(*args: str, **kwargs) -> object:
            calls.append(args[0] if args else "")
            return _paseo_cli_side_effect(str(self.repo))(*args, **kwargs)

        # Second repair is blocked by the undelivered prior attempt, before
        # any send.
        review_file = self.repo / "review.md"
        review_file.write_text("Fix B.", encoding="utf-8")
        with patch(
            "harness.paseo_collaboration._run_paseo_cli", side_effect=_effect,
        ):
            with self.assertRaises(PaseoCollaborationError) as cm:
                paseo_repair(ctx, "github-32", review_file)
        self.assertIn("repair_blocked_undelivered_prior_attempt",
                      str(cm.exception))
        self.assertNotIn("send", calls)

        # Remove the untracked review file so the diff still matches the
        # report, then acceptance must block on the undelivered repair.
        review_file.unlink()
        calls = []
        with patch(
            "harness.paseo_collaboration._run_paseo_cli", side_effect=_effect,
        ):
            with self.assertRaises(PaseoCollaborationError) as cm:
                collaboration_accept(ctx, task_id="github-32")
        self.assertIn("acceptance_blocked_by_undelivered_repair",
                      str(cm.exception))
        self.assertNotIn("send", calls)
        self.assertNotIn("inspect", calls)
        self.assertEqual(_git(self.repo, "rev-parse", "HEAD"), head_before,
                         "HEAD must be unchanged after blocked repair/accept")

    def test_fix10_report_command_trust_boundary(self) -> None:
        """Report command records are metadata-only: missing id, bad digest,
        bad status, bool/out-of-range exit codes, pass/nonzero mismatch, and
        forbidden raw fields are each rejected; persisted skips/risks keep
        only 64-hex digests of reason/detail."""
        from harness.codex_direct import _diff_digest, _task_dir
        from harness.paseo_collaboration import (
            PaseoCollaborationError,
            paseo_bootstrap,
            paseo_dispatch,
            paseo_report,
        )

        hd = hashlib.sha256(b"Fix10.").hexdigest()
        _write_bridge(self.repo, self._contract(), handoff_digest=hd)
        ctx = self._ctx()
        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ):
            paseo_bootstrap(ctx, self._contract())

            handoff = self.repo / "handoff.md"
            handoff.write_text("Fix10.", encoding="utf-8")
            paseo_dispatch(ctx, "github-32", handoff)

            (self.repo / "harness").mkdir(parents=True, exist_ok=True)
            (self.repo / "harness" / "paseo_collaboration.py").write_text(
                "# seam\n", encoding="utf-8")
            _git(self.repo, "add", "harness/paseo_collaboration.py")
            handoff.unlink()

            diff_digest = _diff_digest(ctx.root)

        def _base_report() -> dict:
            return {
                "schema": "harness.paseo-writer-report/v1",
                "task_id": "github-32",
                "mode": "codex-paseo-claude",
                "agent_id": "agent-test-uuid",
                "summary": "Implemented collaboration seam.",
                "files_changed": ["harness/paseo_collaboration.py"],
                "diff_digest": diff_digest,
                "commands": [{"id": "tests", "digest": "aa" * 32,
                              "status": "pass", "exit_code": 0}],
                "skipped_checks": [],
                "risks": [],
                "criterion_evidence": [
                    {"id": "preflight-readonly", "status": "pass",
                     "digest": "cc" * 32},
                ],
            }

        def _reject(needle: str, **mutations) -> None:
            report = _base_report()
            report.update(mutations)
            with patch(
                "harness.paseo_collaboration._run_paseo_cli",
                side_effect=_paseo_cli_side_effect(str(self.repo)),
            ):
                with self.assertRaises(PaseoCollaborationError) as cm:
                    paseo_report(ctx, "github-32", report)
            self.assertIn(needle, str(cm.exception))

        _reject("report_command_0_bad_id",
                commands=[{"digest": "aa" * 32, "status": "pass",
                           "exit_code": 0}])
        _reject("report_command_0_bad_digest",
                commands=[{"id": "tests", "digest": "zz" * 32,
                           "status": "pass", "exit_code": 0}])
        _reject("report_command_0_bad_status",
                commands=[{"id": "tests", "digest": "aa" * 32,
                           "status": "ok", "exit_code": 0}])
        _reject("report_command_0_bad_exit_code",
                commands=[{"id": "tests", "digest": "aa" * 32,
                           "status": "pass", "exit_code": True}])
        _reject("report_command_0_bad_exit_code",
                commands=[{"id": "tests", "digest": "aa" * 32,
                           "status": "pass", "exit_code": 2**31}])
        _reject("report_command_0_status_exit_mismatch",
                commands=[{"id": "tests", "digest": "aa" * 32,
                           "status": "pass", "exit_code": 1}])
        _reject("report_command_0_forbidden_keys",
                commands=[{"id": "tests", "digest": "aa" * 32,
                           "status": "pass", "exit_code": 0,
                           "raw": "secret output"}])

        # Valid report: skip reason and risk detail persist as digests only.
        report = _base_report()
        report["skipped_checks"] = [
            {"id": "e2e", "reason": "needs live credentials"},
        ]
        report["risks"] = [
            {"id": "r1", "detail": "manual review recommended"},
        ]
        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ):
            validated = paseo_report(ctx, "github-32", report)
        self.assertEqual(validated["status"], "valid")

        report_path = _task_dir(ctx, "github-32") / "report.json"
        persisted = json.loads(report_path.read_text("utf-8"))
        self.assertEqual(
            persisted["skipped_checks"],
            [{"id": "e2e",
              "reason_digest": hashlib.sha256(
                  b"needs live credentials").hexdigest()}],
        )
        self.assertEqual(
            persisted["risks"],
            [{"id": "r1",
              "detail_digest": hashlib.sha256(
                  b"manual review recommended").hexdigest()}],
        )
        self.assertRegex(persisted["skipped_checks"][0]["reason_digest"],
                         r"^[0-9a-f]{64}$")
        self.assertRegex(persisted["risks"][0]["detail_digest"],
                         r"^[0-9a-f]{64}$")
        self.assertNotIn("reason", persisted["skipped_checks"][0])
        self.assertNotIn("detail", persisted["risks"][0])
        raw_text = report_path.read_text("utf-8")
        self.assertNotIn("needs live credentials", raw_text)
        self.assertNotIn("manual review recommended", raw_text)

    def test_fix11_fail_closed_prompt_cleanup(self) -> None:
        """A failed ephemeral prompt cleanup stops dispatch/repair: the
        prepared intent stays, no success sidecar is written, and HEAD is
        unchanged."""
        import pathlib

        import harness.codex_direct as controller
        from harness.codex_direct import _task_dir
        from harness.paseo_collaboration import (
            PaseoCollaborationError,
            paseo_bootstrap,
            paseo_dispatch,
            paseo_repair,
        )

        hd = hashlib.sha256(b"Fix11.").hexdigest()
        _write_bridge(self.repo, self._contract(), handoff_digest=hd)
        ctx = self._ctx()
        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ):
            paseo_bootstrap(ctx, self._contract())

        task_dir = _task_dir(ctx, "github-32")
        launch_path = task_dir / "launch.json"
        pending_path = task_dir / "dispatch-pending.json"
        prompt_path = task_dir / "dispatch-prompt.txt"

        handoff = self.repo / "handoff.md"
        handoff.write_text("Fix11.", encoding="utf-8")

        head_before = _git(self.repo, "rev-parse", "HEAD")
        _real_unlink = pathlib.Path.unlink

        def _fail_dispatch_prompt(self, *args, **kwargs):
            if self.name == "dispatch-prompt.txt":
                raise OSError("injected cleanup failure")
            return _real_unlink(self, *args, **kwargs)

        def _cleanup_failure(fail_unlink):
            if os.name == "nt":
                return patch("pathlib.Path.unlink", new=fail_unlink)
            return patch(
                "harness.paseo_collaboration.os.ftruncate",
                side_effect=OSError("injected cleanup failure"),
            )

        # (a) dispatch: platform-native cleanup failure is fail-closed.
        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ), _cleanup_failure(_fail_dispatch_prompt):
            with self.assertRaises(PaseoCollaborationError) as cm:
                paseo_dispatch(ctx, "github-32", handoff)
        self.assertIn("prompt_cleanup_failed", str(cm.exception))
        self.assertTrue(pending_path.exists(),
                        "prepared intent must stay for recovery inspection")
        self.assertFalse(launch_path.exists(),
                         "no launch evidence after cleanup failure")

        # Controlled test-only reset: clear the prepared intent so a normal
        # retry can obtain launch evidence.
        pending_path.unlink()
        if prompt_path.exists():
            prompt_path.unlink()
        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ):
            paseo_dispatch(ctx, "github-32", handoff)
        self.assertTrue(launch_path.exists())
        self.assertFalse(pending_path.exists())

        # (b) repair: unlink failure on repair-prompt.txt is fail-closed.
        controller.advance_codex_direct(
            ctx, task_id="github-32", target="verifying",
            expected_mode="codex-paseo-claude",
        )

        def _fail_repair_prompt(self, *args, **kwargs):
            if self.name == "repair-prompt.txt":
                raise OSError("injected cleanup failure")
            return _real_unlink(self, *args, **kwargs)

        repair_pending_path = task_dir / "repair-pending-1.json"
        repair_dispatch_path = task_dir / "repair-dispatch-1.json"
        repair_prompt_path = task_dir / "repair-prompt.txt"
        review_file = self.repo / "review.md"
        review_file.write_text("Fix review.", encoding="utf-8")
        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ), _cleanup_failure(_fail_repair_prompt):
            with self.assertRaises(PaseoCollaborationError) as cm:
                paseo_repair(ctx, "github-32", review_file)
        self.assertIn("prompt_cleanup_failed", str(cm.exception))
        self.assertIn("repair-prompt.txt", str(cm.exception))
        self.assertTrue(repair_pending_path.exists(),
                        "prepared repair intent must stay")
        self.assertFalse(repair_dispatch_path.exists(),
                         "no repair success sidecar after cleanup failure")

        with self.assertRaises(PaseoCollaborationError) as cm:
            paseo_repair(ctx, "github-32", review_file)
        self.assertIn("repair_blocked_undelivered", str(cm.exception))
        self.assertFalse(repair_prompt_path.exists(),
                         "verified stale repair prompt must be scrubbed")

        # No repair success sidecar; HEAD unchanged throughout.
        self.assertFalse(repair_dispatch_path.exists())
        self.assertEqual(_git(self.repo, "rev-parse", "HEAD"), head_before,
                         "HEAD must be unchanged after fail-closed cleanup")

    def test_fix12_send_exception_removes_prompt_files(self) -> None:
        """A send exception still removes both ephemeral prompt files: the
        prepared intent stays for recovery, no success sidecar is written,
        there is no automatic resend, and HEAD is unchanged."""
        import harness.codex_direct as controller
        from harness.codex_direct import _task_dir
        from harness.paseo_collaboration import (
            PaseoCollaborationError,
            paseo_bootstrap,
            paseo_dispatch,
            paseo_repair,
        )

        hd = hashlib.sha256(b"Fix12.").hexdigest()
        _write_bridge(self.repo, self._contract(), handoff_digest=hd)
        ctx = self._ctx()
        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ):
            paseo_bootstrap(ctx, self._contract())

        task_dir = _task_dir(ctx, "github-32")
        launch_path = task_dir / "launch.json"
        pending_path = task_dir / "dispatch-pending.json"
        prompt_path = task_dir / "dispatch-prompt.txt"

        handoff = self.repo / "handoff.md"
        handoff.write_text("Fix12.", encoding="utf-8")
        head_before = _git(self.repo, "rev-parse", "HEAD")

        sends = {"n": 0}

        def _send_raises(*args, **kwargs):
            if args and args[0] == "send":
                sends["n"] += 1
                raise PaseoCollaborationError("injected send failure")
            return _paseo_cli_side_effect(str(self.repo))(*args, **kwargs)

        # (a) dispatch: send raises; raw handoff prompt must not survive.
        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_send_raises,
        ):
            with self.assertRaises(PaseoCollaborationError) as cm:
                paseo_dispatch(ctx, "github-32", handoff)
        self.assertIn("dispatch_send_failed", str(cm.exception))
        self.assertEqual(sends["n"], 1, "no automatic resend after failure")
        self.assertFalse(prompt_path.exists(),
                         "raw handoff prompt must not survive a send failure")
        self.assertTrue(pending_path.exists(),
                        "prepared intent must stay for recovery inspection")
        self.assertFalse(launch_path.exists(),
                         "no launch evidence after send failure")

        # Controlled test-only reset: clear the prepared intent so a normal
        # retry can obtain launch evidence.
        pending_path.unlink()
        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ):
            paseo_dispatch(ctx, "github-32", handoff)
        self.assertTrue(launch_path.exists())
        self.assertFalse(pending_path.exists())

        # (b) repair: send raises; raw review prompt must not survive.
        controller.advance_codex_direct(
            ctx, task_id="github-32", target="verifying",
            expected_mode="codex-paseo-claude",
        )
        repair_pending_path = task_dir / "repair-pending-1.json"
        repair_dispatch_path = task_dir / "repair-dispatch-1.json"
        repair_prompt_path = task_dir / "repair-prompt.txt"
        review_file = self.repo / "review.md"
        review_file.write_text("Fix review.", encoding="utf-8")
        sends["n"] = 0
        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_send_raises,
        ):
            with self.assertRaises(PaseoCollaborationError) as cm:
                paseo_repair(ctx, "github-32", review_file)
        self.assertIn("repair_send_failed", str(cm.exception))
        self.assertEqual(sends["n"], 1, "no automatic resend after failure")
        self.assertFalse(repair_prompt_path.exists(),
                         "raw review prompt must not survive a send failure")
        self.assertTrue(repair_pending_path.exists(),
                        "prepared repair intent must stay")
        self.assertFalse(repair_dispatch_path.exists(),
                         "no repair success sidecar after send failure")

        self.assertEqual(_git(self.repo, "rev-parse", "HEAD"), head_before,
                         "HEAD must be unchanged after send failures")

    def test_fix13_bootstrap_lock_drift_enters_recovery(self) -> None:
        """Post-launch repository-lock drift never Direct-rollbacks: the
        frozen run, agent identity, and active lease survive into
        recovery-required."""
        import json
        from unittest.mock import Mock

        from harness.codex_direct import _repository_lock_identity, _task_dir
        from harness.paseo_collaboration import bootstrap

        hd = hashlib.sha256(b"Fix13.").hexdigest()
        _write_bridge(self.repo, self._contract(), handoff_digest=hd)
        ctx = self._ctx()
        calls: list[str] = []

        def _effect(*args, **kwargs):
            calls.append(args[0] if args else "")
            return _paseo_cli_side_effect(str(self.repo))(*args, **kwargs)

        repository_lock = ctx.common_git_dir / "config"
        identity = _repository_lock_identity(repository_lock)
        seen = {"n": 0}

        def _drifting_identity(path):
            seen["n"] += 1
            if seen["n"] >= 3:  # drift only at the post-launch recheck
                return (identity[0], identity[1], identity[2], identity[3] + 1)
            return identity

        rollback = Mock()
        with patch(
            "harness.paseo_collaboration._run_paseo_cli", side_effect=_effect,
        ), patch(
            "harness.paseo_collaboration._repository_lock_identity",
            side_effect=_drifting_identity,
        ), patch(
            "harness.paseo_collaboration._rollback_unstable_start", rollback,
        ):
            result, ec = bootstrap(ctx, self._contract())

        self.assertEqual(ec, 6)
        self.assertEqual(result["state"], "recovery-required")
        self.assertEqual(
            result["writer_lease"], {"holder": "claude", "state": "active"}
        )
        rollback.assert_not_called()
        for cmd in ("stop", "kill", "archive"):
            self.assertNotIn(cmd, calls, "agent must never be stopped or restarted")

        task_dir = _task_dir(ctx, "github-32")
        run_path = task_dir / "run.json"
        self.assertTrue(run_path.exists(), "frozen run must survive lock drift")
        run = json.loads(run_path.read_text(encoding="utf-8"))
        self.assertEqual(run["agent_id"], "agent-test-uuid")
        self.assertEqual(run["agent_state"], "active")
        self.assertEqual(
            run["contract"]["writer_lease"], {"holder": "claude", "state": "active"}
        )
        self.assertEqual(run["state"], "recovery-required")
        self.assertIsNotNone(run.get("recovery_bundle"))

    def test_fix14_manual_skill_reminder_hardened_persistence(self) -> None:
        """The missing-bridge reminder uses the hardened shared marker seam:
        durable bounded marker, repository-wide dedup, and bounded rejection
        on refusal — no traceback, no run, no Paseo call."""
        import json

        from harness.codex_direct import _task_dir
        from harness.paseo_collaboration import paseo_bootstrap

        ctx = self._ctx()
        calls: list[str] = []

        def _effect(*args, **kwargs):
            calls.append(args[0] if args else "")
            return _paseo_cli_side_effect(str(self.repo))(*args, **kwargs)

        # (a) first missing-bridge call emits the durable bounded marker.
        with patch(
            "harness.paseo_collaboration._run_paseo_cli", side_effect=_effect,
        ):
            result, ec = paseo_bootstrap(ctx, self._contract())
        self.assertEqual(ec, 3)
        self.assertEqual(result["manual_skill"]["status"], "reminder-emitted")
        self.assertNotIn("run", calls, "no agent creation on the missing-bridge path")
        self.assertNotIn("send", calls, "no send on the missing-bridge path")

        marker_dir = ctx.runtime_root / "manual-skill-reminders"
        markers = list(marker_dir.glob("*.json"))
        self.assertEqual(len(markers), 1)
        marker = json.loads(markers[0].read_text(encoding="utf-8"))
        self.assertEqual(
            marker,
            {
                "schema": "harness.manual-skill-reminder/v1",
                "reminder_id": markers[0].stem,
            },
        )
        self.assertLessEqual(markers[0].stat().st_size, 1024)

        # (b) repository-wide dedup: a second call is already-reminded.
        with patch(
            "harness.paseo_collaboration._run_paseo_cli", side_effect=_effect,
        ):
            result, ec = paseo_bootstrap(ctx, self._contract())
        self.assertEqual(ec, 3)
        self.assertEqual(result["manual_skill"]["status"], "already-reminded")
        self.assertEqual(len(list(marker_dir.glob("*.json"))), 1)

        # (c) refusal: an existing invalid marker fails closed with a bounded
        #     rejection — no run, no Paseo call.
        markers[0].unlink()
        markers[0].write_text("not a valid marker", encoding="utf-8")
        with patch(
            "harness.paseo_collaboration._run_paseo_cli", side_effect=_effect,
        ):
            result, ec = paseo_bootstrap(ctx, self._contract())
        self.assertEqual(ec, 2)
        self.assertEqual(result["state"], "rejected")
        self.assertIn("manual_skill_reminder_failed", result["error"])
        self.assertNotIn("run", calls, "no agent creation after reminder refusal")
        self.assertNotIn("send", calls, "no send after reminder refusal")
        self.assertFalse(
            (_task_dir(ctx, "github-32") / "run.json").exists(),
            "no run record after reminder refusal",
        )

    def test_fix15_malformed_contracts_reject_structurally(self) -> None:
        """Public bootstrap rejects malformed contracts with bounded JSON:
        no traceback, no run record, no Paseo call."""
        from harness.codex_direct import _task_dir
        from harness.paseo_collaboration import bootstrap

        ctx = self._ctx()
        calls: list[str] = []

        def _effect(*args, **kwargs):
            calls.append(args[0] if args else "")
            return _paseo_cli_side_effect(str(self.repo))(*args, **kwargs)

        bad_contracts = [
            {},
            {"task": None},
            {"task": "not-an-object"},
            {"task": {}},
            {"task": {"id": 7, "source": "x"}},
            {"task": {"id": "", "source": "x"}},
        ]
        with patch(
            "harness.paseo_collaboration._run_paseo_cli", side_effect=_effect,
        ):
            for bad in bad_contracts:
                result, ec = bootstrap(ctx, bad)
                self.assertEqual(ec, 2, f"bounded rejection for {bad!r}")
                self.assertEqual(result["state"], "rejected")
                self.assertTrue(
                    isinstance(result.get("error"), str) and result["error"]
                )
        self.assertEqual(calls, [], "no Paseo call for malformed contracts")
        self.assertFalse(
            (_task_dir(ctx, "github-32") / "run.json").exists(),
            "no run record for malformed contracts",
        )

    def test_fix16_prompt_ephemeral_across_write_and_persist_exits(self) -> None:
        """Raw prompt bytes never survive any write/persist exit: a pending
        write failure creates no prompt, a partial prompt write is removed,
        and the prepared intent stays for recovery."""
        import harness.codex_direct as controller
        import harness.paseo_collaboration as collaboration
        from harness.codex_direct import _task_dir
        from harness.paseo_collaboration import (
            paseo_bootstrap,
            paseo_dispatch,
            paseo_repair,
        )

        hd = hashlib.sha256(b"Fix16.").hexdigest()
        _write_bridge(self.repo, self._contract(), handoff_digest=hd)
        ctx = self._ctx()
        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ):
            paseo_bootstrap(ctx, self._contract())

        task_dir = _task_dir(ctx, "github-32")
        launch_path = task_dir / "launch.json"
        pending_path = task_dir / "dispatch-pending.json"
        prompt_path = task_dir / "dispatch-prompt.txt"
        handoff = self.repo / "handoff.md"
        handoff.write_text("Fix16.", encoding="utf-8")
        head_before = _git(self.repo, "rev-parse", "HEAD")

        real_write_json = controller._write_json
        real_write_prompt = collaboration._write_ephemeral_prompt

        def _fail_pending_write(context, path, value):
            if path.name == "dispatch-pending.json":
                raise OSError("injected pending-write failure")
            return real_write_json(context, path, value)

        # (a) dispatch: pending-write failure must create no prompt bytes.
        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ), patch("harness.codex_direct._write_json", side_effect=_fail_pending_write):
            with self.assertRaises(OSError):
                paseo_dispatch(ctx, "github-32", handoff)
        self.assertFalse(prompt_path.exists(),
                         "no prompt bytes after a pending-write failure")
        self.assertFalse(pending_path.exists())
        self.assertFalse(launch_path.exists())

        def _partial_prompt_write(context, path, content):
            if path.name == "dispatch-prompt.txt":
                path.write_bytes(b"partial prompt bytes")
                raise OSError("injected partial prompt write failure")
            return real_write_prompt(context, path, content)

        # (b) dispatch: a partial prompt write is removed; the prepared
        #     intent (persisted first) stays for recovery.
        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ), patch("harness.paseo_collaboration._write_ephemeral_prompt",
                 new=_partial_prompt_write):
            with self.assertRaises(OSError):
                paseo_dispatch(ctx, "github-32", handoff)
        self.assertFalse(prompt_path.exists(),
                         "partial prompt bytes must be removed")
        self.assertTrue(pending_path.exists(),
                        "prepared intent must stay for recovery inspection")
        self.assertFalse(launch_path.exists())

        # Controlled test-only reset: clear the prepared intent so a normal
        # retry can obtain launch evidence.
        pending_path.unlink()
        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ):
            paseo_dispatch(ctx, "github-32", handoff)
        self.assertTrue(launch_path.exists())
        self.assertFalse(prompt_path.exists())

        controller.advance_codex_direct(
            ctx, task_id="github-32", target="verifying",
            expected_mode="codex-paseo-claude",
        )
        repair_pending_path = task_dir / "repair-pending-1.json"
        repair_dispatch_path = task_dir / "repair-dispatch-1.json"
        repair_prompt_path = task_dir / "repair-prompt.txt"
        review_file = self.repo / "review.md"
        review_file.write_text("Fix review.", encoding="utf-8")

        def _fail_repair_pending_write(context, path, value):
            if path.name == "repair-pending-1.json":
                raise OSError("injected repair pending-write failure")
            return real_write_json(context, path, value)

        # (c) repair: pending-write failure must create no prompt bytes.
        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ), patch("harness.codex_direct._write_json",
                 side_effect=_fail_repair_pending_write):
            with self.assertRaises(OSError):
                paseo_repair(ctx, "github-32", review_file)
        self.assertFalse(repair_prompt_path.exists(),
                         "no prompt bytes after a pending-write failure")
        self.assertFalse(repair_pending_path.exists())
        self.assertFalse(repair_dispatch_path.exists())

        # Controlled test-only reset: _begin_repair_unlocked records repair 1
        # BEFORE the pending write (at-most-once ordering), so the undelivered
        # entry blocks the next repair call. Clear the entry and return to
        # verifying through the production advance path (mirror of the
        # pending_path.unlink() reset above) so phase (d) reaches prompt
        # creation.
        run_path, run = controller._load_run(
            ctx, "github-32", expected_mode="codex-paseo-claude"
        )
        run["repairs"] = []
        controller._save_run(ctx, run_path, run)
        controller.advance_codex_direct(
            ctx, task_id="github-32", target="verifying",
            expected_mode="codex-paseo-claude",
        )

        def _partial_repair_prompt_write(context, path, content):
            if path.name == "repair-prompt.txt":
                path.write_bytes(b"partial review bytes")
                raise OSError("injected partial repair prompt write failure")
            return real_write_prompt(context, path, content)

        # (d) repair: a partial prompt write is removed; the prepared
        #     intent stays.
        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ), patch("harness.paseo_collaboration._write_ephemeral_prompt",
                 new=_partial_repair_prompt_write):
            with self.assertRaises(OSError):
                paseo_repair(ctx, "github-32", review_file)
        self.assertFalse(repair_prompt_path.exists(),
                         "partial review bytes must be removed")
        self.assertTrue(repair_pending_path.exists(),
                        "prepared repair intent must stay")
        self.assertFalse(repair_dispatch_path.exists())

        self.assertEqual(_git(self.repo, "rev-parse", "HEAD"), head_before,
                         "HEAD must be unchanged after write/persist failures")

    def test_fix17_launch_evidence_has_no_absolute_cwd(self) -> None:
        """Launch runtime metadata never retains the absolute private cwd;
        the opaque worktree ID replaces it."""
        import json

        from harness.codex_direct import _task_dir
        from harness.paseo_collaboration import paseo_bootstrap, paseo_dispatch

        hd = hashlib.sha256(b"Fix17.").hexdigest()
        _write_bridge(self.repo, self._contract(), handoff_digest=hd)
        ctx = self._ctx()
        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ):
            paseo_bootstrap(ctx, self._contract())

        handoff = self.repo / "handoff.md"
        handoff.write_text("Fix17.", encoding="utf-8")
        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ):
            paseo_dispatch(ctx, "github-32", handoff)

        launch_path = _task_dir(ctx, "github-32") / "launch.json"
        launch_text = launch_path.read_text(encoding="utf-8")
        launch = json.loads(launch_text)
        self.assertNotIn("canonical_worktree", launch)
        self.assertEqual(launch["worktree_id"], ctx.worktree_id)
        resolved = str(self.repo.resolve())
        self.assertNotIn(resolved, launch_text)
        self.assertNotIn(resolved.replace("\\", "/"), launch_text)

    def test_fix18_accept_guard_deterministic(self) -> None:
        """Accept guard is deterministic: Codex is authorized, Claude is
        denied — handled before shared delegation, never via exception
        fallback."""
        from harness.paseo_collaboration import (
            collaboration_guard,
            paseo_bootstrap,
        )

        _write_bridge(self.repo, self._contract())
        ctx = self._ctx()
        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ):
            paseo_bootstrap(ctx, self._contract())

        result, ec = collaboration_guard(
            ctx, "github-32", action="accept", actor="claude",
        )
        self.assertNotEqual(ec, 0)
        self.assertFalse(result["allowed"])
        self.assertEqual(result["reason"], "accept_is_codex_owned")

        result, ec = collaboration_guard(
            ctx, "github-32", action="accept", actor="codex",
        )
        self.assertEqual(ec, 0)
        self.assertTrue(result["allowed"])

    # ---- recovery (finding #11) ----

    def test_recovery_preserves_lease_and_mode(self) -> None:
        from harness.paseo_collaboration import (
            paseo_bootstrap,
            paseo_dispatch,
            paseo_recover,
        )

        hd = hashlib.sha256(b"Task.").hexdigest()
        _write_bridge(self.repo, self._contract(), handoff_digest=hd)
        ctx = self._ctx()
        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ):
            paseo_bootstrap(ctx, self._contract())

        handoff = self.repo / "handoff.md"
        handoff.write_text("Task.", encoding="utf-8")

        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ):
            paseo_dispatch(ctx, "github-32", handoff)

        fingerprint = hashlib.sha256(b"adapter-failure").hexdigest()
        result, ec = paseo_recover(
            ctx, "github-32", "adapter-failure", fingerprint
        )
        # Recovery returns exit code 6 (recovery-required signal)
        self.assertEqual(ec, 6)
        self.assertEqual(result["mode"], "codex-paseo-claude")
        self.assertEqual(
            result["writer_lease"], {"holder": "claude", "state": "active"}
        )
        self.assertEqual(result["state"], "recovery-required")

    def test_recovery_bundle_roundtrip_status(self) -> None:
        """Round-trip tracer: a persisted collaboration recovery bundle is
        readable and shape-validated through the public status path."""
        from harness.codex_direct import codex_direct_status
        from harness.paseo_collaboration import (
            paseo_bootstrap,
            paseo_dispatch,
            paseo_recover,
        )

        hd = hashlib.sha256(b"Task.").hexdigest()
        _write_bridge(self.repo, self._contract(), handoff_digest=hd)
        ctx = self._ctx()
        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ):
            paseo_bootstrap(ctx, self._contract())

        handoff = self.repo / "handoff.md"
        handoff.write_text("Task.", encoding="utf-8")
        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ):
            paseo_dispatch(ctx, "github-32", handoff)

        fingerprint = hashlib.sha256(b"adapter-failure").hexdigest()
        _result, ec = paseo_recover(
            ctx, "github-32", "adapter-failure", fingerprint
        )
        self.assertEqual(ec, 6)

        status = codex_direct_status(
            ctx, task_id="github-32", expected_mode="codex-paseo-claude"
        )
        bundle = status["recovery_bundle"]
        self.assertIsNotNone(bundle)
        collab = bundle["collaboration"]
        self.assertEqual(
            collab["schema"], "harness.collaboration-recovery-evidence/v1"
        )
        self.assertIsInstance(collab["agent_id"], str)
        self.assertTrue(collab["agent_id"])
        self.assertIsInstance(collab["agent_state"], str)
        self.assertRegex(collab["bridge_handoff_digest"], r"^[0-9a-f]{64}$")
        self.assertEqual(collab["bridge_handoff_digest"], hd)
        self.assertTrue(collab["lease_preserved"])
        self.assertFalse(collab["daemon_restarted"])
        self.assertFalse(collab["adapter_switched"])
        self.assertFalse(collab["provider_switched"])
        self.assertEqual(
            set(collab["sidecars"]),
            {
                "dispatch-pending.json", "launch.json",
                "repair-pending-attempts", "repair-dispatch-attempts",
                "report.json",
            },
        )
        self.assertRegex(collab["sidecars"]["launch.json"], r"^[0-9a-f]{64}$")
        self.assertEqual(
            collab["sidecars"]["report.json"], "missing-or-unreadable"
        )
        self.assertEqual(
            collab["sidecars"]["repair-pending-attempts"],
            "missing-or-unreadable",
        )
        self.assertEqual(
            collab["sidecars"]["repair-dispatch-attempts"],
            "missing-or-unreadable",
        )

    # ---- collaboration guard (finding #8) ----

    def test_guard_blocks_codex_write_of_owned_path(self) -> None:
        from harness.paseo_collaboration import (
            collaboration_guard,
            paseo_bootstrap,
        )

        _write_bridge(self.repo, self._contract())
        ctx = self._ctx()
        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ):
            paseo_bootstrap(ctx, self._contract())

        result, ec = collaboration_guard(
            ctx, "github-32", action="write", actor="codex",
            path="harness/paseo_collaboration.py",
        )
        self.assertNotEqual(ec, 0)
        self.assertFalse(result["allowed"])

    def test_guard_allows_codex_read_of_owned_path(self) -> None:
        from harness.paseo_collaboration import (
            collaboration_guard,
            paseo_bootstrap,
        )

        _write_bridge(self.repo, self._contract())
        ctx = self._ctx()
        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ):
            paseo_bootstrap(ctx, self._contract())

        result, ec = collaboration_guard(
            ctx, "github-32", action="review", actor="codex",
        )
        self.assertEqual(ec, 0)
        self.assertTrue(result["allowed"])

    def test_guard_blocks_claude_accept(self) -> None:
        from harness.paseo_collaboration import (
            collaboration_guard,
            paseo_bootstrap,
        )

        _write_bridge(self.repo, self._contract())
        ctx = self._ctx()
        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ):
            paseo_bootstrap(ctx, self._contract())

        result, ec = collaboration_guard(
            ctx, "github-32", action="accept", actor="claude",
        )
        self.assertNotEqual(ec, 0)
        self.assertFalse(result["allowed"])

    def test_guard_blocks_claude_write_outside_owned(self) -> None:
        from harness.paseo_collaboration import (
            collaboration_guard,
            paseo_bootstrap,
        )

        _write_bridge(self.repo, self._contract())
        ctx = self._ctx()
        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ):
            paseo_bootstrap(ctx, self._contract())

        result, ec = collaboration_guard(
            ctx, "github-32", action="write", actor="claude",
            path="src/index.ts",  # not in owned_paths
        )
        self.assertNotEqual(ec, 0)
        self.assertFalse(result["allowed"])

    def test_guard_blocks_claude_local_commit_when_accepted(self) -> None:
        """Accepted run: Claude ``local-commit`` is denied at the advertised
        collaboration guard boundary (Codex-owned); Codex remains allowed."""
        from harness.codex_direct import _diff_digest
        from harness.paseo_collaboration import (
            _launch_digest,
            collaboration_accept,
            collaboration_advance,
            collaboration_guard,
            collaboration_judge,
            collaboration_record_check,
            paseo_bootstrap,
            paseo_dispatch,
        )

        # Track owned file BEFORE bootstrap so the baseline includes it.
        (self.repo / "harness").mkdir(parents=True, exist_ok=True)
        owned = self.repo / "harness" / "paseo_collaboration.py"
        owned.write_text("# base\n", encoding="utf-8")
        _git(self.repo, "add", "harness/paseo_collaboration.py")
        _git(self.repo, "commit", "-m", "track owned file")

        contract = self._contract()
        contract["plan"]["verification_plan"].append(
            {"id": "review", "command": "code-review", "required": False}
        )

        content = "Implement Issue #32."
        hd = hashlib.sha256(content.encode("utf-8")).hexdigest()
        _write_bridge(self.repo, contract, handoff_digest=hd)
        ctx = self._ctx()
        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ):
            paseo_bootstrap(ctx, contract)

        handoff = self.repo / "handoff.md"
        handoff.write_text(content, encoding="utf-8")
        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ):
            paseo_dispatch(ctx, "github-32", handoff)

        # Modify tracked file (unstaged) for diff
        owned.write_text("# lifecycle\n", encoding="utf-8")
        diff_digest = _diff_digest(ctx.root)

        # Bind the manual report to the launch sidecar through the shared
        # serialization seam (acceptance recomputes the same digest).
        from harness.codex_direct import _task_dir, _write_json
        task_dir = _task_dir(ctx, "github-32")
        launch_data = json.loads((task_dir / "launch.json").read_text("utf-8"))
        report_data = {
            "schema": "harness.paseo-writer-report/v1",
            "task_id": "github-32", "mode": "codex-paseo-claude",
            "agent_id": "agent-test-uuid",
            "summary": "Accepted-state guard regression report.",
            "files_changed": ["harness/paseo_collaboration.py"],
            "diff_digest": diff_digest,
            "commands": [{"digest": "aa" * 32, "status": "pass", "exit_code": 0}],
            "skipped_checks": [], "risks": [],
            "criterion_evidence": [
                {"id": "preflight-readonly", "status": "pass",
                 "digest": "cc" * 32},
            ],
            "launch_digest": _launch_digest(launch_data),
        }
        _write_json(ctx, task_dir / "report.json", report_data)

        # Advance state: executing → verifying → reviewing
        collaboration_advance(ctx, task_id="github-32", target="verifying")
        collaboration_advance(ctx, task_id="github-32", target="reviewing")

        collaboration_record_check(
            ctx, task_id="github-32",
            check_id="tests", status="pass",
            source="command",
            exit_code=0, sensitivity="secret-free", digest="ab" * 32,
            reason_code=None,
        )
        collaboration_record_check(
            ctx, task_id="github-32",
            check_id="review", status="pass",
            source="review",
            exit_code=None, sensitivity="secret-free", digest="cd" * 32,
            reason_code=None,
        )

        collaboration_judge(
            ctx, task_id="github-32",
            criterion_id="preflight-readonly", status="pass",
            evidence_digest="ab" * 32,
        )

        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ):
            accepted = collaboration_accept(ctx, task_id="github-32")
        self.assertEqual(accepted.get("commit_status"), "created")

        # Accepted state reached — guard the local-commit boundary.
        claude_result, claude_ec = collaboration_guard(
            ctx, "github-32", action="local-commit", actor="claude"
        )
        self.assertNotEqual(claude_ec, 0)
        self.assertFalse(claude_result["allowed"])

        codex_result, codex_ec = collaboration_guard(
            ctx, "github-32", action="local-commit", actor="codex"
        )
        self.assertEqual(codex_ec, 0)
        self.assertEqual(codex_result.get("decision"), "allowed")

    # ---- acceptance + commit (criterion 9) ----

    def test_accept_and_commit_requires_report_evidence(self) -> None:
        import harness.codex_direct as controller
        from harness.paseo_collaboration import (
            PaseoCollaborationError,
            collaboration_accept,
            paseo_bootstrap,
        )

        _write_bridge(self.repo, self._contract())
        ctx = self._ctx()
        contract = self._contract()
        contract["plan"]["verification_plan"].append(
            {"id": "review", "command": "code-review", "required": False}
        )
        with patch(
            "harness.paseo_collaboration._run_paseo_cli",
            side_effect=_paseo_cli_side_effect(str(self.repo)),
        ):
            paseo_bootstrap(ctx, contract)

        # No launch.json or report.json → accept must fail
        with self.assertRaises(PaseoCollaborationError) as cm:
            collaboration_accept(ctx, task_id="github-32")
        self.assertIn("launch_evidence", str(cm.exception))


# ---------------------------------------------------------------------------
# CLI tests
# ---------------------------------------------------------------------------

@unittest.skipIf(GIT_EXE is None, "git not on PATH — inject PATH at command line")
class PaseoCollaborationCLITests(_PaseoTestBase):
    """Tests that verify the CLI subprocess subcommand shape.

    These do NOT mock the Paseo CLI — they only verify argument parsing and
    subcommand registration.  Bootstrap/dispatch flows that require a live
    Paseo daemon are tested in the function-test class above with mocks.
    """

    def _harness(self, *args: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        if "PYTHONPATH" not in env:
            env["PYTHONPATH"] = str(ROOT)
        return subprocess.run(
            [sys.executable, "-m", "harness", *args],
            cwd=self.repo,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    def test_cli_subcommand_is_registered(self) -> None:
        result = self._harness("codex-paseo-claude", "--help")
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        stdout_lower = result.stdout.lower()
        self.assertIn("preflight", stdout_lower)
        self.assertIn("bootstrap", stdout_lower)
        self.assertIn("dispatch", stdout_lower)
        self.assertIn("report", stdout_lower)
        self.assertIn("repair", stdout_lower)
        self.assertIn("recover", stdout_lower)
        # Lifecycle commands
        self.assertIn("guard", stdout_lower)
        self.assertIn("status", stdout_lower)
        self.assertIn("accept", stdout_lower)
        self.assertIn("commit", stdout_lower)

    def test_cli_contract_validation(self) -> None:
        """Contract validation is mode-agnostic — verify it works."""
        cp = self.root / "contract.json"
        cp.write_text(json.dumps(_collab_contract(self.repo)), encoding="utf-8")
        result = self._harness("contract", "validate", str(cp))
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["valid"])

    def test_cli_bootstrap_rejects_non_object_task_without_traceback(self) -> None:
        """Public CLI seam: a valid JSON object whose ``task`` is null, a
        string, or a list must return bounded rejected JSON (exit 2) — no
        traceback, no run record, no Paseo launch."""
        # Disposable fake Paseo CLI records every invocation: the events file
        # must never be created for these rejections.
        fake_dir = Path(self._temp.name) / "fake_paseo"
        fake_dir.mkdir()
        events_path = str(fake_dir / "events.jsonl")
        self._write_fake_paseo(fake_dir, events_path, str(self.repo))

        env = os.environ.copy()
        if "PYTHONPATH" not in env:
            env["PYTHONPATH"] = str(ROOT)
        env["PATH"] = str(fake_dir) + os.pathsep + env.get("PATH", "")
        env["PASEO_FAKE_EVENTS"] = events_path
        env["PASEO_FAKE_REPO"] = str(self.repo)

        cp = self.root / "contract.json"
        for bad_task in (None, "bad", []):
            cp.write_text(json.dumps({"task": bad_task}), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "-m", "harness", "codex-paseo-claude",
                 "bootstrap", str(cp)],
                cwd=self.repo,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            self.assertEqual(
                result.returncode, 2,
                f"bounded rejection for {bad_task!r}: "
                f"{result.stderr or result.stdout}",
            )
            payload = json.loads(result.stdout)
            self.assertEqual(payload["state"], "rejected")
            self.assertTrue(
                isinstance(payload.get("error"), str) and payload["error"]
            )
            self.assertNotIn("Traceback", result.stderr)
            self.assertNotIn("Traceback", result.stdout)
            self.assertNotIn("AttributeError", result.stderr)
            self.assertNotIn("AttributeError", result.stdout)

        # No run record and no Paseo launch across all three rejections.
        runtime_dir = self.repo / ".harness" / "runtime"
        run_records = (
            list(runtime_dir.rglob("run.json")) if runtime_dir.exists() else []
        )
        self.assertFalse(run_records, "no run record for rejected contracts")
        self.assertFalse(
            Path(events_path).exists(), "fake Paseo must never be launched"
        )

    # -- Slice 1: freeze run.json BEFORE paseo run (public CLI seam) ----------

    def test_slice1_run_json_frozen_before_paseo_run(self) -> None:
        """Red tracer: run.json must exist BEFORE the fake Paseo receives ``run``."""
        contract = _collab_contract(
            self.repo,
            **{
                "writer_lease": {"holder": "claude", "state": "inactive"},
                "state": "ready",
                "required_manual_skills": [
                    {"name": "implement", "host": "claude",
                     "status": "required", "invocation": None},
                ],
            },
        )
        _write_bridge(self.repo, contract)

        # Write contract to disk
        cp = self.root / "contract.json"
        cp.write_text(json.dumps(contract, ensure_ascii=True), encoding="utf-8")

        # Disposable fake Paseo CLI in a command-scoped temp directory
        fake_dir = Path(self._temp.name) / "fake_paseo"
        fake_dir.mkdir()
        events_path = str(fake_dir / "events.jsonl")
        self._write_fake_paseo(fake_dir, events_path, str(self.repo))

        env = os.environ.copy()
        if "PYTHONPATH" not in env:
            env["PYTHONPATH"] = str(ROOT)
        # Prepend fake dir to PATH only for this subprocess
        env["PATH"] = str(fake_dir) + os.pathsep + env.get("PATH", "")
        env["PASEO_FAKE_EVENTS"] = events_path
        env["PASEO_FAKE_REPO"] = str(self.repo)

        result = subprocess.run(
            [sys.executable, "-m", "harness", "codex-paseo-claude",
             "bootstrap", str(cp),
             "--provider", "claude/deepseek-v4-flash"],
            cwd=self.repo,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        # Parse events recorded by the fake Paseo
        run_event = None
        if Path(events_path).exists():
            for line in Path(events_path).read_text("utf-8").splitlines():
                if not line.strip():
                    continue
                evt = json.loads(line)
                if evt.get("cmd") and evt["cmd"][0] == "run":
                    run_event = evt
                    break

        self.assertIsNotNone(run_event, "fake Paseo never received 'run' command")

        # The contract slice-1 assertion: run.json must exist BEFORE paseo run
        self.assertTrue(
            run_event.get("run_json_exists"),
            "run.json must exist before paseo run; got run_json_exists=False. "
            "Bootstrap is persisting run state after external agent creation.",
        )

        # Verify the frozen run content: active Claude lease, pending agent,
        # frozen base/branch/worktree/owner
        run_json_path = self.repo / ".harness" / "runtime"
        candidates = list(run_json_path.rglob("run.json"))
        self.assertTrue(candidates, "run.json not found under runtime dir")
        run_data = json.loads(
            candidates[0].read_text("utf-8"), parse_float=lambda _: None,
        )
        self.assertEqual(
            run_data.get("schema"),
            "harness.codex-paseo-claude-run/v1",
        )
        self.assertEqual(run_data.get("state"), "executing")
        # After successful bootstrap, agent is bound and active
        self.assertEqual(run_data.get("agent_state"), "active")
        self.assertIsNotNone(run_data.get("agent_id"))
        self.assertTrue(run_data["agent_id"].startswith("agent-fake-"))
        self.assertEqual(
            run_data["contract"]["writer_lease"],
            {"holder": "claude", "state": "active"},
        )
        self.assertEqual(
            run_data["contract"]["acceptance_owner"], "codex",
        )
        self.assertEqual(
            run_data["contract"]["execution"]["mode"], "codex-paseo-claude",
        )

    def test_slice2_prompt_file_format(self) -> None:
        """Red tracer: prompt file first line must be exactly /implement, then
        newline, then the bounded handoff content."""
        contract = _collab_contract(
            self.repo,
            **{
                "writer_lease": {"holder": "claude", "state": "inactive"},
                "state": "ready",
                "required_manual_skills": [
                    {"name": "implement", "host": "claude",
                     "status": "required", "invocation": None},
                ],
            },
        )
        # Handoff must exist before bootstrap: its digest binds the bridge trigger.
        handoff_dir = self.repo / ".harness" / "coordination" / "github-32"
        handoff_dir.mkdir(parents=True, exist_ok=True)
        handoff_path = handoff_dir / "handoff.md"
        handoff_text = "Implement Issue #32 from the handoff."
        handoff_path.write_text(handoff_text, encoding="utf-8")
        handoff_digest = hashlib.sha256(
            handoff_text.encode("utf-8")
        ).hexdigest()
        _write_bridge(self.repo, contract, handoff_digest=handoff_digest)

        cp = self.root / "contract.json"
        cp.write_text(json.dumps(contract, ensure_ascii=True), encoding="utf-8")

        # Disposable fake Paseo CLI
        fake_dir = Path(self._temp.name) / "fake_paseo"
        fake_dir.mkdir()
        events_path = str(fake_dir / "events.jsonl")
        self._write_fake_paseo(fake_dir, events_path, str(self.repo))

        env = os.environ.copy()
        if "PYTHONPATH" not in env:
            env["PYTHONPATH"] = str(ROOT)
        env["PATH"] = str(fake_dir) + os.pathsep + env.get("PATH", "")
        env["PASEO_FAKE_EVENTS"] = events_path
        env["PASEO_FAKE_REPO"] = str(self.repo)

        # Step 1: Bootstrap through public CLI
        bs_result = subprocess.run(
            [sys.executable, "-m", "harness", "codex-paseo-claude",
             "bootstrap", str(cp),
             "--provider", "claude/deepseek-v4-flash"],
            cwd=self.repo, env=env, capture_output=True, text=True, encoding="utf-8",
        )
        self.assertEqual(bs_result.returncode, 0,
                         f"bootstrap failed: {bs_result.stderr}")

        # Step 2: Dispatch through public CLI
        disp_result = subprocess.run(
            [sys.executable, "-m", "harness", "codex-paseo-claude",
             "dispatch", "--task", "github-32",
             "--handoff", str(handoff_path),
             "--cwd", str(self.repo)],
            cwd=self.repo, env=env, capture_output=True, text=True, encoding="utf-8",
        )
        self.assertEqual(disp_result.returncode, 0,
                         f"dispatch failed: {disp_result.stderr}")

        # Step 3: The dispatch prompt file is ephemeral — removed in finally
        # after send — so the fake Paseo captured it at send time.
        runtime_dir = self.repo / ".harness" / "runtime"
        self.assertEqual(
            list(runtime_dir.rglob("dispatch-prompt.txt")), [],
            "dispatch prompt file must be removed after send",
        )

        send_events = []
        for line in Path(events_path).read_text("utf-8").splitlines():
            if not line.strip():
                continue
            evt = json.loads(line)
            if evt.get("cmd") and evt["cmd"][0] == "send":
                send_events.append(evt)
        self.assertTrue(send_events, "fake Paseo never received 'send'")
        prompt_content = send_events[0].get("prompt_file", "")

        # Slice 2 assertion: first line is exactly /implement
        first_line, _, rest = prompt_content.partition("\n")
        self.assertEqual(
            first_line, "/implement",
            f"First line must be '/implement', got: {first_line!r}",
        )
        # Slice 2 assertion: newline separator exists, handoff on second line+
        self.assertIn(
            "\n", prompt_content,
            "Prompt must have newline after '/implement' — "
            "handoff must start on a separate line",
        )
        self.assertIn(
            "Implement Issue #32 from the handoff.", rest,
            "Handoff content must appear after the /implement line",
        )

    def _configure_fake_paseo(self, fake_dir: Path, **updates: object) -> None:
        config_path = fake_dir / "_paseo_fake_config.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        config.update(updates)
        config_path.write_text(json.dumps(config), encoding="utf-8")

    def _write_fake_paseo(self, fake_dir: Path, events_path: str, repo: str,
                          *, omit_inspect_model: bool = False,
                          empty_models: bool = False,
                          inspect_model: str | None = None,
                          connected_daemon: str = "connected") -> None:
        """Write a disposable fake Paseo CLI into *fake_dir*.

        When *omit_inspect_model* is True the inspect response omits the
        ``Model`` field so fail-closed tests can verify rejection.
        When *empty_models* is True the model list is empty.
        When *inspect_model* is set the default inspect model is overridden.
        The adjacent config file supports bounded runtime test overrides.
        *connected_daemon* controls the daemon status connectedDaemon field.
        """
        if omit_inspect_model:
            default_model = ""
        elif inspect_model is not None:
            default_model = inspect_model
        else:
            default_model = "deepseek-v4-flash"
        models_json = "[]" if empty_models else '[{"id":"deepseek-v4-flash","model":"deepseek-v4-flash","description":"Fast model"}]'
        (fake_dir / "_paseo_fake_config.json").write_text(
            json.dumps({
                "events": events_path,
                "repo": repo,
                "connected_daemon": connected_daemon,
                "inspect_json": None,
                "inspect_model": default_model,
            }),
            encoding="utf-8",
        )
        (fake_dir / "_paseo_fake.py").write_text(f'''\
import sys, json, os
from pathlib import Path
config = json.loads(Path(__file__).with_name("_paseo_fake_config.json").read_text("utf-8"))
ep = config["events"]
repo = config["repo"]
def _r(a,**kw):
    if ep:
        with open(ep,"a",encoding="utf-8") as f:
            f.write(json.dumps({{"cmd":a,**kw}})+"\\n")
def _check_run_json():
    for _ in (Path(repo)/".harness"/"runtime").rglob("run.json") if repo else []:
        return True
    return False
args = sys.argv[1:]
if args and args[0] == "--json":
    args = args[1:]
if not args:
    print(json.dumps({{}})); sys.exit(0)
cmd = args[0]
if cmd == "daemon":
    _r(args)
    cd = config["connected_daemon"]
    print(json.dumps({{"localDaemon":"running","connectedDaemon":cd,"daemonVersion":"1.0.0","cliVersion":"1.0.0"}}))
elif cmd == "provider":
    sub = args[1] if len(args) > 1 else ""
    if sub == "ls":
        _r(args)
        print(json.dumps([{{"provider":"codex","status":"available","label":"Codex","defaultMode":"auto"}},{{"provider":"claude","status":"available","label":"Claude Code","defaultMode":"auto"}}]))
    elif sub == "models":
        _r(args)
        print(json.dumps({models_json}))
    else:
        _r(args); print(json.dumps({{}}))
elif cmd == "run":
    rj = _check_run_json()
    _r(args, run_json_exists=rj)
    agent_id = "agent-fake-" + os.urandom(8).hex()
    print(json.dumps({{"id":agent_id,"status":"running"}}))
elif cmd == "inspect":
    _r(args)
    agent_id = args[1] if len(args) > 1 else "agent-fake-00000000"
    override = config.get("inspect_json")
    if override:
        resp = dict(override)
        if "Id" not in resp:
            resp["Id"] = agent_id
        print(json.dumps(resp))
    else:
        m = config.get("inspect_model", "")
        resp = {{"Id":agent_id,"Provider":"claude","Cwd":repo,"Status":"idle","Mode":"bypassPermissions","Archived":False}}
        if m:
            resp["Model"] = m
        print(json.dumps(resp))
elif cmd == "send":
    pf = ""
    if "--prompt-file" in args:
        i = args.index("--prompt-file")
        p = Path(args[i+1]) if i+1 < len(args) else None
        if p is not None and p.exists():
            pf = p.read_text("utf-8")
    _r(args, prompt_file=pf)
    print(json.dumps({{"status":"dispatched"}}))
else:
    _r(args); print(json.dumps({{}}))
''', encoding="utf-8")
        if os.name == "nt":
            (fake_dir / "paseo.cmd").write_text(
                f'@"{sys.executable}" "%~dp0_paseo_fake.py" %*', encoding="ascii",
            )
        else:
            launcher = fake_dir / "paseo"
            launcher.write_text(
                "#!/bin/sh\n"
                f'exec "{sys.executable}" "$(dirname "$0")/_paseo_fake.py" "$@"\n',
                encoding="utf-8",
            )
            launcher.chmod(0o755)

    def test_slice3_inspect_fail_closed_on_missing_field(self) -> None:
        """Red tracer: bootstrap must enter recovery when inspect omits a
        required field (Model).  The current code skips provider/cwd checks
        when those fields are empty."""
        contract = _collab_contract(
            self.repo,
            **{
                "writer_lease": {"holder": "claude", "state": "inactive"},
                "state": "ready",
                "required_manual_skills": [
                    {"name": "implement", "host": "claude",
                     "status": "required", "invocation": None},
                ],
            },
        )
        _write_bridge(self.repo, contract)

        cp = self.root / "contract.json"
        cp.write_text(json.dumps(contract, ensure_ascii=True), encoding="utf-8")

        fake_dir = Path(self._temp.name) / "fake_paseo"
        fake_dir.mkdir()
        events_path = str(fake_dir / "events.jsonl")
        # omit_inspect_model=True → inspect response has no Model field
        self._write_fake_paseo(fake_dir, events_path, str(self.repo),
                                omit_inspect_model=True)

        env = os.environ.copy()
        if "PYTHONPATH" not in env:
            env["PYTHONPATH"] = str(ROOT)
        env["PATH"] = str(fake_dir) + os.pathsep + env.get("PATH", "")
        env["PASEO_FAKE_EVENTS"] = events_path
        env["PASEO_FAKE_REPO"] = str(self.repo)

        result = subprocess.run(
            [sys.executable, "-m", "harness", "codex-paseo-claude",
             "bootstrap", str(cp),
             "--provider", "claude/deepseek-v4-flash"],
            cwd=self.repo, env=env, capture_output=True, text=True, encoding="utf-8",
        )
        # Slice 3 assertion: bootstrap must fail closed (exit 6 = recovery)
        self.assertNotEqual(result.returncode, 0,
                            "bootstrap must fail when inspect omits Model")
        self.assertEqual(result.returncode, 6,
                         result.stderr or result.stdout)

        stdout = json.loads(result.stdout)
        self.assertEqual(stdout.get("state"), "recovery-required")

        # The run record must not persist raw error text; the hashed
        # failure category/fingerprint reach the Recovery Bundle reference.
        runtime_dir = self.repo / ".harness" / "runtime"
        candidates = list(runtime_dir.rglob("run.json"))
        self.assertTrue(candidates, "run.json not found")
        run_data = json.loads(candidates[0].read_text("utf-8"))
        self.assertNotIn(
            "error", run_data,
            "run record must not persist raw error text",
        )
        failure = run_data["recovery_bundle"]["failure"]
        self.assertEqual(failure["category"], "adapter-failure")
        self.assertRegex(failure["fingerprint"], r"^[0-9a-f]{64}$")

    def test_slice4_at_most_once_dispatch(self) -> None:
        """Red tracer: a leftover ``dispatch-pending.json`` (crash after
        sidecar write, before send) must block re-dispatch.  Currently only
        ``launch.json`` is checked — the pending sidecar is not written at all."""
        contract = _collab_contract(
            self.repo,
            **{
                "writer_lease": {"holder": "claude", "state": "inactive"},
                "state": "ready",
                "required_manual_skills": [
                    {"name": "implement", "host": "claude",
                     "status": "required", "invocation": None},
                ],
            },
        )
        _write_bridge(self.repo, contract)

        cp = self.root / "contract.json"
        cp.write_text(json.dumps(contract, ensure_ascii=True), encoding="utf-8")

        fake_dir = Path(self._temp.name) / "fake_paseo"
        fake_dir.mkdir()
        events_path = str(fake_dir / "events.jsonl")
        self._write_fake_paseo(fake_dir, events_path, str(self.repo))

        env = os.environ.copy()
        if "PYTHONPATH" not in env:
            env["PYTHONPATH"] = str(ROOT)
        env["PATH"] = str(fake_dir) + os.pathsep + env.get("PATH", "")
        env["PASEO_FAKE_EVENTS"] = events_path
        env["PASEO_FAKE_REPO"] = str(self.repo)

        # Bootstrap
        bs = subprocess.run(
            [sys.executable, "-m", "harness", "codex-paseo-claude",
             "bootstrap", str(cp),
             "--provider", "claude/deepseek-v4-flash"],
            cwd=self.repo, env=env, capture_output=True, text=True, encoding="utf-8",
        )
        self.assertEqual(bs.returncode, 0, f"bootstrap failed: {bs.stderr}")

        # Write and bind handoff
        handoff_dir = self.repo / ".harness" / "coordination" / "github-32"
        handoff_path = handoff_dir / "handoff.md"
        handoff_text = "Implement Issue #32."
        handoff_path.write_text(handoff_text, encoding="utf-8")
        handoff_digest = hashlib.sha256(handoff_text.encode("utf-8")).hexdigest()
        bridge_path = handoff_dir / "bridge-trigger.json"
        bridge_data = json.loads(bridge_path.read_text("utf-8"))
        bridge_data["handoff_digest"] = handoff_digest
        bridge_path.write_text(json.dumps(bridge_data), encoding="utf-8")

        # Simulate a crash after sidecar write but before send: place a
        # leftover dispatch-pending.json in the task runtime directory.
        run_json_candidates = list(
            (self.repo / ".harness" / "runtime").rglob("run.json")
        )
        self.assertTrue(run_json_candidates, "run.json missing")
        task_dir = run_json_candidates[0].parent
        pending_path = task_dir / "dispatch-pending.json"
        pending_path.write_text(json.dumps({"schema": "harness.dispatch-pending/v1",
                                             "status": "pending"}), encoding="utf-8")
        prompt_path = task_dir / "dispatch-prompt.txt"
        prompt_path.write_text("raw handoff residue", encoding="utf-8")

        # Dispatch must REJECT because the pending sidecar already exists.
        disp = subprocess.run(
            [sys.executable, "-m", "harness", "codex-paseo-claude",
             "dispatch", "--task", "github-32",
             "--handoff", str(handoff_path),
             "--cwd", str(self.repo)],
            cwd=self.repo, env=env, capture_output=True, text=True, encoding="utf-8",
        )
        self.assertNotEqual(disp.returncode, 0,
                            "dispatch must reject when dispatch-pending.json exists")
        self.assertFalse(prompt_path.exists(),
                         "verified stale prompt must be scrubbed before rejection")

    def test_slice3_crash_recovery_both_files_reject_dispatch(self) -> None:
        """CLI tracer: if BOTH dispatch-pending.json AND launch.json exist
        (crash after launch write, before pending cleanup), dispatch must
        still reject as already completed."""
        contract = _collab_contract(
            self.repo,
            **{
                "writer_lease": {"holder": "claude", "state": "inactive"},
                "state": "ready",
                "required_manual_skills": [
                    {"name": "implement", "host": "claude",
                     "status": "required", "invocation": None},
                ],
            },
        )
        _write_bridge(self.repo, contract)

        cp = self.root / "contract.json"
        cp.write_text(json.dumps(contract, ensure_ascii=True), encoding="utf-8")

        fake_dir = Path(self._temp.name) / "fake_paseo"
        fake_dir.mkdir()
        events_path = str(fake_dir / "events.jsonl")
        self._write_fake_paseo(fake_dir, events_path, str(self.repo))

        env = os.environ.copy()
        if "PYTHONPATH" not in env:
            env["PYTHONPATH"] = str(ROOT)
        env["PATH"] = str(fake_dir) + os.pathsep + env.get("PATH", "")
        env["PASEO_FAKE_EVENTS"] = events_path
        env["PASEO_FAKE_REPO"] = str(self.repo)

        # Bootstrap
        bs = subprocess.run(
            [sys.executable, "-m", "harness", "codex-paseo-claude",
             "bootstrap", str(cp),
             "--provider", "claude/deepseek-v4-flash"],
            cwd=self.repo, env=env, capture_output=True, text=True, encoding="utf-8",
        )
        self.assertEqual(bs.returncode, 0, f"bootstrap failed: {bs.stderr}")

        # Write and bind handoff
        handoff_dir = self.repo / ".harness" / "coordination" / "github-32"
        handoff_path = handoff_dir / "handoff.md"
        handoff_text = "Implement Issue #32."
        handoff_path.write_text(handoff_text, encoding="utf-8")
        handoff_digest = hashlib.sha256(handoff_text.encode("utf-8")).hexdigest()
        bridge_path = handoff_dir / "bridge-trigger.json"
        bridge_data = json.loads(bridge_path.read_text("utf-8"))
        bridge_data["handoff_digest"] = handoff_digest
        bridge_path.write_text(json.dumps(bridge_data), encoding="utf-8")

        # Simulate crash after launch write, before pending cleanup:
        # place BOTH files in the task runtime directory.
        run_json_candidates = list(
            (self.repo / ".harness" / "runtime").rglob("run.json")
        )
        self.assertTrue(run_json_candidates, "run.json missing")
        task_dir = run_json_candidates[0].parent
        pending_path = task_dir / "dispatch-pending.json"
        pending_path.write_text(json.dumps(
            {"schema": "harness.dispatch-pending/v1", "status": "pending"}
        ), encoding="utf-8")
        launch_path = task_dir / "launch.json"
        launch_path.write_text(json.dumps(
            {"schema": "harness.launch/v1", "agent_id": "already-dispatched"}
        ), encoding="utf-8")

        # Dispatch must REJECT (both files exist = already completed).
        disp = subprocess.run(
            [sys.executable, "-m", "harness", "codex-paseo-claude",
             "dispatch", "--task", "github-32",
             "--handoff", str(handoff_path),
             "--cwd", str(self.repo)],
            cwd=self.repo, env=env, capture_output=True, text=True, encoding="utf-8",
        )
        self.assertNotEqual(disp.returncode, 0,
            "dispatch must reject when both pending and launch exist")

    # ---- Slice 5: close the actor/non-overlap guard -----------------------

    def test_slice5_guard_blocks_stage_and_unknown_actor(self) -> None:
        """Red tracer: ``stage`` is not in GUARDED_ACTIONS so the shared guard
        raises, and the collaboration exception handler lets it through because
        ``stage`` is not in the hardcoded deny list.  Result: stage is allowed
        via the fallback path (exit 0) when it should be blocked.

        Also: ``actor`` is validated only in argparse, not inside
        ``collaboration_guard``."""
        contract = _collab_contract(
            self.repo,
            **{
                "writer_lease": {"holder": "claude", "state": "inactive"},
                "state": "ready",
                "required_manual_skills": [
                    {"name": "implement", "host": "claude",
                     "status": "required", "invocation": None},
                ],
            },
        )
        _write_bridge(self.repo, contract)

        cp = self.root / "contract.json"
        cp.write_text(json.dumps(contract, ensure_ascii=True), encoding="utf-8")

        fake_dir = Path(self._temp.name) / "fake_paseo"
        fake_dir.mkdir()
        events_path = str(fake_dir / "events.jsonl")
        self._write_fake_paseo(fake_dir, events_path, str(self.repo))

        env = os.environ.copy()
        if "PYTHONPATH" not in env:
            env["PYTHONPATH"] = str(ROOT)
        env["PATH"] = str(fake_dir) + os.pathsep + env.get("PATH", "")
        env["PASEO_FAKE_EVENTS"] = events_path
        env["PASEO_FAKE_REPO"] = str(self.repo)

        # Bootstrap
        bs = subprocess.run(
            [sys.executable, "-m", "harness", "codex-paseo-claude",
             "bootstrap", str(cp),
             "--provider", "claude/deepseek-v4-flash"],
            cwd=self.repo, env=env, capture_output=True, text=True, encoding="utf-8",
        )
        self.assertEqual(bs.returncode, 0, f"bootstrap failed: {bs.stderr}")

        # 1. ``stage`` should be blocked (currently allowed through)
        result = subprocess.run(
            [sys.executable, "-m", "harness", "codex-paseo-claude",
             "guard", "--task", "github-32", "--action", "stage",
             "--actor", "claude"],
            cwd=self.repo, env=env, capture_output=True, text=True, encoding="utf-8",
        )
        self.assertNotEqual(result.returncode, 0,
                            "stage action must be rejected (currently allowed)")

        # 2. ``write`` on an owned path for Claude should be allowed
        #    (currently rejected — falls through to guard_resolution_failed)
        result = subprocess.run(
            [sys.executable, "-m", "harness", "codex-paseo-claude",
             "guard", "--task", "github-32", "--action", "write",
             "--actor", "claude",
             "--path", "harness/paseo_collaboration.py"],
            cwd=self.repo, env=env, capture_output=True, text=True, encoding="utf-8",
        )
        self.assertEqual(result.returncode, 0,
                         f"write on owned path should be allowed: {result.stdout}")


    # ---- Slice 1 RED: empty model discovery must fail closed ---------------

    def test_slice1_empty_model_discovery_rejects_before_paseo_run(self) -> None:
        """RED tracer: resolved model plus empty model discovery must reject
        before ``paseo run``.  Current code at paseo_preflight:306 checks
        ``model and model_ids and model not in model_ids`` — when model_ids is
        an empty set the condition short-circuits to False, so the preflight
        silently passes.  Bootstrap must return non-zero."""
        contract = _collab_contract(
            self.repo,
            **{
                "writer_lease": {"holder": "claude", "state": "inactive"},
                "state": "ready",
                "required_manual_skills": [
                    {"name": "implement", "host": "claude",
                     "status": "required", "invocation": None},
                ],
            },
        )
        _write_bridge(self.repo, contract)

        cp = self.root / "contract.json"
        cp.write_text(json.dumps(contract, ensure_ascii=True), encoding="utf-8")

        fake_dir = Path(self._temp.name) / "fake_paseo"
        fake_dir.mkdir()
        events_path = str(fake_dir / "events.jsonl")
        self._write_fake_paseo(fake_dir, events_path, str(self.repo),
                                empty_models=True)

        env = os.environ.copy()
        if "PYTHONPATH" not in env:
            env["PYTHONPATH"] = str(ROOT)
        env["PATH"] = str(fake_dir) + os.pathsep + env.get("PATH", "")
        env["PASEO_FAKE_EVENTS"] = events_path
        env["PASEO_FAKE_REPO"] = str(self.repo)

        result = subprocess.run(
            [sys.executable, "-m", "harness", "codex-paseo-claude",
             "bootstrap", str(cp),
             "--provider", "claude/deepseek-v4-flash"],
            cwd=self.repo, env=env, capture_output=True, text=True,
            encoding="utf-8",
        )

        # RED assertion: bootstrap MUST fail (currently passes — fail-open)
        self.assertNotEqual(
            result.returncode, 0,
            f"bootstrap must reject when model discovery returns empty list; "
            f"got exit {result.returncode}. stdout: {result.stdout}",
        )
        # State must be rejected (not executing) — preflight failure before
        # agent creation returns exit 1 with "rejected", not recovery-required.
        stdout = json.loads(result.stdout)
        self.assertEqual(
            stdout.get("state"), "rejected",
            f"empty model discovery must be rejected; "
            f"got state={stdout.get('state')}. Full: {result.stdout}",
        )


    def test_slice1_empty_handoff_digest_rejects_bootstrap(self) -> None:
        """RED tracer: bridge with empty/missing handoff_digest must reject
        bootstrap.  Current _validate_bridge_trigger skips handoff_digest
        entirely, and paseo_bootstrap:534 accepts "" silently."""
        contract = _collab_contract(
            self.repo,
            **{
                "writer_lease": {"holder": "claude", "state": "inactive"},
                "state": "ready",
                "required_manual_skills": [
                    {"name": "implement", "host": "claude",
                     "status": "required", "invocation": None},
                ],
            },
        )
        # Write bridge with empty handoff_digest
        _write_bridge(self.repo, contract, handoff_digest="")

        cp = self.root / "contract.json"
        cp.write_text(json.dumps(contract, ensure_ascii=True), encoding="utf-8")

        fake_dir = Path(self._temp.name) / "fake_paseo"
        fake_dir.mkdir()
        events_path = str(fake_dir / "events.jsonl")
        self._write_fake_paseo(fake_dir, events_path, str(self.repo))

        env = os.environ.copy()
        if "PYTHONPATH" not in env:
            env["PYTHONPATH"] = str(ROOT)
        env["PATH"] = str(fake_dir) + os.pathsep + env.get("PATH", "")
        env["PASEO_FAKE_EVENTS"] = events_path
        env["PASEO_FAKE_REPO"] = str(self.repo)

        result = subprocess.run(
            [sys.executable, "-m", "harness", "codex-paseo-claude",
             "bootstrap", str(cp),
             "--provider", "claude/deepseek-v4-flash"],
            cwd=self.repo, env=env, capture_output=True, text=True,
            encoding="utf-8",
        )

        # RED: bootstrap must reject empty handoff_digest
        self.assertNotEqual(
            result.returncode, 0,
            f"empty handoff_digest must reject bootstrap; "
            f"got exit {result.returncode}. stdout: {result.stdout}",
        )


    def test_slice1_dispatch_rejects_mutated_empty_handoff_digest(self) -> None:
        """RED tracer: dispatch must independently revalidate the current bridge
        handoff_digest.  Code at paseo_dispatch:837 checks
        ``if expected_handoff_digest and ...`` — when the digest is empty after
        a bridge mutation between bootstrap and dispatch, validation is skipped
        silently."""
        contract = _collab_contract(
            self.repo,
            **{
                "writer_lease": {"holder": "claude", "state": "inactive"},
                "state": "ready",
                "required_manual_skills": [
                    {"name": "implement", "host": "claude",
                     "status": "required", "invocation": None},
                ],
            },
        )
        _write_bridge(self.repo, contract)

        cp = self.root / "contract.json"
        cp.write_text(json.dumps(contract, ensure_ascii=True), encoding="utf-8")

        fake_dir = Path(self._temp.name) / "fake_paseo"
        fake_dir.mkdir()
        events_path = str(fake_dir / "events.jsonl")
        self._write_fake_paseo(fake_dir, events_path, str(self.repo))

        env = os.environ.copy()
        if "PYTHONPATH" not in env:
            env["PYTHONPATH"] = str(ROOT)
        env["PATH"] = str(fake_dir) + os.pathsep + env.get("PATH", "")
        env["PASEO_FAKE_EVENTS"] = events_path
        env["PASEO_FAKE_REPO"] = str(self.repo)

        # Step 1: Bootstrap with a valid bridge
        bs = subprocess.run(
            [sys.executable, "-m", "harness", "codex-paseo-claude",
             "bootstrap", str(cp),
             "--provider", "claude/deepseek-v4-flash"],
            cwd=self.repo, env=env, capture_output=True, text=True,
            encoding="utf-8",
        )
        self.assertEqual(bs.returncode, 0, f"bootstrap failed: {bs.stderr}")

        # Step 2: Mutate bridge — empty handoff_digest after bootstrap
        bridge_path = (self.repo / ".harness" / "coordination"
                       / "github-32" / "bridge-trigger.json")
        bridge_data = json.loads(bridge_path.read_text("utf-8"))
        bridge_data["handoff_digest"] = ""
        bridge_path.write_text(json.dumps(bridge_data), encoding="utf-8")

        # Step 3: Write and bind handoff
        handoff_path = (self.repo / ".harness" / "coordination"
                        / "github-32" / "handoff.md")
        handoff_path.write_text("Implement Issue #32.", encoding="utf-8")

        # Step 4: Dispatch — must reject mutated empty handoff_digest
        disp = subprocess.run(
            [sys.executable, "-m", "harness", "codex-paseo-claude",
             "dispatch", "--task", "github-32",
             "--handoff", str(handoff_path),
             "--cwd", str(self.repo)],
            cwd=self.repo, env=env, capture_output=True, text=True,
            encoding="utf-8",
        )
        self.assertNotEqual(
            disp.returncode, 0,
            f"dispatch must reject empty handoff_digest in current bridge; "
            f"got exit {disp.returncode}. stdout: {disp.stdout}",
        )


    def test_slice1_duplicate_bootstrap_rejected(self) -> None:
        """RED tracer: an existing run.json for the same task must reject a
        second bootstrap BEFORE ``paseo run``.  Currently _make_fresh_run and
        _save_run are called at lines 543-550 without checking for an existing
        run — a second bootstrap overwrites the first run and creates a second
        agent."""
        contract = _collab_contract(
            self.repo,
            **{
                "writer_lease": {"holder": "claude", "state": "inactive"},
                "state": "ready",
                "required_manual_skills": [
                    {"name": "implement", "host": "claude",
                     "status": "required", "invocation": None},
                ],
            },
        )
        _write_bridge(self.repo, contract)

        cp = self.root / "contract.json"
        cp.write_text(json.dumps(contract, ensure_ascii=True), encoding="utf-8")

        fake_dir = Path(self._temp.name) / "fake_paseo"
        fake_dir.mkdir()
        events_path = str(fake_dir / "events.jsonl")
        self._write_fake_paseo(fake_dir, events_path, str(self.repo))

        env = os.environ.copy()
        if "PYTHONPATH" not in env:
            env["PYTHONPATH"] = str(ROOT)
        env["PATH"] = str(fake_dir) + os.pathsep + env.get("PATH", "")
        env["PASEO_FAKE_EVENTS"] = events_path
        env["PASEO_FAKE_REPO"] = str(self.repo)

        # Step 1: First bootstrap succeeds
        bs1 = subprocess.run(
            [sys.executable, "-m", "harness", "codex-paseo-claude",
             "bootstrap", str(cp),
             "--provider", "claude/deepseek-v4-flash"],
            cwd=self.repo, env=env, capture_output=True, text=True,
            encoding="utf-8",
        )
        self.assertEqual(bs1.returncode, 0, f"first bootstrap failed: {bs1.stderr}")

        # Count paseo "run" events from first bootstrap
        run_count_1 = 0
        if Path(events_path).exists():
            for line in Path(events_path).read_text("utf-8").splitlines():
                if not line.strip():
                    continue
                evt = json.loads(line)
                if isinstance(evt.get("cmd"), list) and evt["cmd"] and evt["cmd"][0] == "run":
                    run_count_1 += 1
        self.assertEqual(run_count_1, 1, f"first bootstrap: expected 1 run, got {run_count_1}")

        # Step 2: Second bootstrap must be rejected WITHOUT a second paseo run
        bs2 = subprocess.run(
            [sys.executable, "-m", "harness", "codex-paseo-claude",
             "bootstrap", str(cp),
             "--provider", "claude/deepseek-v4-flash"],
            cwd=self.repo, env=env, capture_output=True, text=True,
            encoding="utf-8",
        )

        # RED: second bootstrap must fail (currently overwrites and creates agent)
        self.assertNotEqual(
            bs2.returncode, 0,
            f"second bootstrap must be rejected; "
            f"got exit {bs2.returncode}. stdout: {bs2.stdout}",
        )

        # RED: no additional paseo "run" events (currently creates a second agent)
        run_count_2 = 0
        if Path(events_path).exists():
            for line in Path(events_path).read_text("utf-8").splitlines():
                if not line.strip():
                    continue
                evt = json.loads(line)
                if isinstance(evt.get("cmd"), list) and evt["cmd"] and evt["cmd"][0] == "run":
                    run_count_2 += 1
        self.assertEqual(
            run_count_2, 1,
            f"second bootstrap must not create another agent; "
            f"got {run_count_2} paseo run events",
        )


    def test_slice1_missing_bridge_no_writes_dedup(self) -> None:
        """RED tracer: missing bridge must cause no run.json and no paseo
        run event, and the second missing-bridge call must be deduplicated."""
        contract = _collab_contract(
            self.repo,
            **{
                "writer_lease": {"holder": "claude", "state": "inactive"},
                "state": "ready",
                "required_manual_skills": [
                    {"name": "implement", "host": "claude",
                     "status": "required", "invocation": None},
                ],
            },
        )
        # No _write_bridge — bridge is intentionally missing

        cp = self.root / "contract.json"
        cp.write_text(json.dumps(contract, ensure_ascii=True), encoding="utf-8")

        fake_dir = Path(self._temp.name) / "fake_paseo"
        fake_dir.mkdir()
        events_path = str(fake_dir / "events.jsonl")
        self._write_fake_paseo(fake_dir, events_path, str(self.repo))

        env = os.environ.copy()
        if "PYTHONPATH" not in env:
            env["PYTHONPATH"] = str(ROOT)
        env["PATH"] = str(fake_dir) + os.pathsep + env.get("PATH", "")
        env["PASEO_FAKE_EVENTS"] = events_path
        env["PASEO_FAKE_REPO"] = str(self.repo)

        # Call 1: missing bridge → reminder, exit 3
        r1 = subprocess.run(
            [sys.executable, "-m", "harness", "codex-paseo-claude",
             "bootstrap", str(cp),
             "--provider", "claude/deepseek-v4-flash"],
            cwd=self.repo, env=env, capture_output=True, text=True,
            encoding="utf-8",
        )
        self.assertEqual(r1.returncode, 3,
                         f"missing bridge must exit 3; got {r1.returncode}")

        # Verify NO run.json was created
        runtime_dir = self.repo / ".harness" / "runtime"
        run_candidates = list(runtime_dir.rglob("run.json"))
        self.assertFalse(
            run_candidates,
            f"missing bridge must not create run.json; found {run_candidates}",
        )

        # Verify NO paseo run event
        run_events = 0
        if Path(events_path).exists():
            for line in Path(events_path).read_text("utf-8").splitlines():
                if not line.strip():
                    continue
                evt = json.loads(line)
                if isinstance(evt.get("cmd"), list) and evt["cmd"] and evt["cmd"][0] == "run":
                    run_events += 1
        self.assertEqual(
            run_events, 0,
            f"missing bridge must not create paseo agent; got {run_events} events",
        )

        # Call 2: deduplicated reminder (already-reminded)
        r2 = subprocess.run(
            [sys.executable, "-m", "harness", "codex-paseo-claude",
             "bootstrap", str(cp),
             "--provider", "claude/deepseek-v4-flash"],
            cwd=self.repo, env=env, capture_output=True, text=True,
            encoding="utf-8",
        )
        self.assertEqual(r2.returncode, 3,
                         f"second missing bridge must still exit 3; got {r2.returncode}")
        stdout2 = json.loads(r2.stdout)
        ms = stdout2.get("manual_skill", {})
        self.assertEqual(
            ms.get("status"), "already-reminded",
            f"second missing bridge must be already-reminded; got {ms}",
        )

    def test_slice1_connected_daemon_required(self) -> None:
        """RED tracer: preflight must fail unless both localDaemon AND
        connectedDaemon are usable.  paseo_preflight:237 only checks
        localDaemon — connectedDaemon is ignored."""
        contract = _collab_contract(
            self.repo,
            **{
                "writer_lease": {"holder": "claude", "state": "inactive"},
                "state": "ready",
                "required_manual_skills": [
                    {"name": "implement", "host": "claude",
                     "status": "required", "invocation": None},
                ],
            },
        )
        _write_bridge(self.repo, contract)

        cp = self.root / "contract.json"
        cp.write_text(json.dumps(contract, ensure_ascii=True), encoding="utf-8")

        fake_dir = Path(self._temp.name) / "fake_paseo"
        fake_dir.mkdir()
        events_path = str(fake_dir / "events.jsonl")
        self._write_fake_paseo(fake_dir, events_path, str(self.repo),
                                connected_daemon="disconnected")

        env = os.environ.copy()
        if "PYTHONPATH" not in env:
            env["PYTHONPATH"] = str(ROOT)
        env["PATH"] = str(fake_dir) + os.pathsep + env.get("PATH", "")
        env["PASEO_FAKE_EVENTS"] = events_path
        env["PASEO_FAKE_REPO"] = str(self.repo)

        result = subprocess.run(
            [sys.executable, "-m", "harness", "codex-paseo-claude",
             "bootstrap", str(cp),
             "--provider", "claude/deepseek-v4-flash"],
            cwd=self.repo, env=env, capture_output=True, text=True,
            encoding="utf-8",
        )

        # RED: must reject when connectedDaemon is not running
        self.assertNotEqual(
            result.returncode, 0,
            f"connectedDaemon disconnected must reject bootstrap; "
            f"got exit {result.returncode}. stdout: {result.stdout}",
        )

    def test_slice2_dispatch_rejects_wrong_agent_model_at_dispatch(self) -> None:
        """RED tracer: dispatch must revalidate the live agent Model against
        the frozen bootstrap provider/model.  Currently paseo_dispatch:813
        only checks ``isinstance(inspect_result, dict)`` — a drifted model is
        silently accepted."""
        contract = _collab_contract(
            self.repo,
            **{
                "writer_lease": {"holder": "claude", "state": "inactive"},
                "state": "ready",
                "required_manual_skills": [
                    {"name": "implement", "host": "claude",
                     "status": "required", "invocation": None},
                ],
            },
        )
        _write_bridge(self.repo, contract)

        cp = self.root / "contract.json"
        cp.write_text(json.dumps(contract, ensure_ascii=True), encoding="utf-8")

        fake_dir = Path(self._temp.name) / "fake_paseo"
        fake_dir.mkdir()
        events_path = str(fake_dir / "events.jsonl")
        self._write_fake_paseo(fake_dir, events_path, str(self.repo))

        env = os.environ.copy()
        if "PYTHONPATH" not in env:
            env["PYTHONPATH"] = str(ROOT)
        env["PATH"] = str(fake_dir) + os.pathsep + env.get("PATH", "")
        env["PASEO_FAKE_EVENTS"] = events_path
        env["PASEO_FAKE_REPO"] = str(self.repo)

        # Bootstrap with correct model (deepseek-v4-flash via default)
        bs = subprocess.run(
            [sys.executable, "-m", "harness", "codex-paseo-claude",
             "bootstrap", str(cp),
             "--provider", "claude/deepseek-v4-flash"],
            cwd=self.repo, env=env, capture_output=True, text=True,
            encoding="utf-8",
        )
        self.assertEqual(bs.returncode, 0, f"bootstrap failed: {bs.stderr}")

        # Write and bind handoff
        handoff_dir = self.repo / ".harness" / "coordination" / "github-32"
        handoff_path = handoff_dir / "handoff.md"
        handoff_text = "Implement Issue #32."
        handoff_path.write_text(handoff_text, encoding="utf-8")
        handoff_digest = hashlib.sha256(handoff_text.encode("utf-8")).hexdigest()
        bridge_path = handoff_dir / "bridge-trigger.json"
        bridge_data = json.loads(bridge_path.read_text("utf-8"))
        bridge_data["handoff_digest"] = handoff_digest
        bridge_path.write_text(json.dumps(bridge_data), encoding="utf-8")

        # Mutate: fake inspect now returns "wrong-model" via its private config.
        self._configure_fake_paseo(fake_dir, inspect_model="wrong-model")

        # Dispatch — must reject because inspect model drifted
        disp = subprocess.run(
            [sys.executable, "-m", "harness", "codex-paseo-claude",
             "dispatch", "--task", "github-32",
             "--handoff", str(handoff_path),
             "--cwd", str(self.repo)],
            cwd=self.repo, env=env, capture_output=True, text=True,
            encoding="utf-8",
        )
        self.assertNotEqual(
            disp.returncode, 0,
            f"dispatch must reject when live agent model differs from frozen; "
            f"got exit {disp.returncode}. stdout: {disp.stdout}",
        )


    # -- Slice 2: live inspect tracers (every missing/drifted field) ---------

    def test_slice2_inspect_missing_archived_rejected(self) -> None:
        """CLI tracer: inspect response without ``Archived`` must be rejected
        at bootstrap (exit 6 = recovery-required)."""
        contract = _collab_contract(
            self.repo,
            **{
                "writer_lease": {"holder": "claude", "state": "inactive"},
                "state": "ready",
                "required_manual_skills": [
                    {"name": "implement", "host": "claude",
                     "status": "required", "invocation": None},
                ],
            },
        )
        _write_bridge(self.repo, contract)

        cp = self.root / "contract.json"
        cp.write_text(json.dumps(contract, ensure_ascii=True), encoding="utf-8")

        fake_dir = Path(self._temp.name) / "fake_paseo"
        fake_dir.mkdir()
        events_path = str(fake_dir / "events.jsonl")
        self._write_fake_paseo(fake_dir, events_path, str(self.repo))

        env = os.environ.copy()
        if "PYTHONPATH" not in env:
            env["PYTHONPATH"] = str(ROOT)
        env["PATH"] = str(fake_dir) + os.pathsep + env.get("PATH", "")
        env["PASEO_FAKE_EVENTS"] = events_path
        env["PASEO_FAKE_REPO"] = str(self.repo)
        # Override inspect to omit Archived entirely.
        self._configure_fake_paseo(fake_dir, inspect_json={
            "Provider": "claude",
            "Model": "deepseek-v4-flash", "Cwd": str(self.repo),
            "Status": "idle", "Mode": "bypassPermissions",
        })

        result = subprocess.run(
            [sys.executable, "-m", "harness", "codex-paseo-claude",
             "bootstrap", str(cp),
             "--provider", "claude/deepseek-v4-flash"],
            cwd=self.repo, env=env, capture_output=True, text=True,
            encoding="utf-8",
        )
        self.assertNotEqual(result.returncode, 0,
                           "bootstrap must reject inspect missing Archived")
        self.assertEqual(result.returncode, 6,
                        "missing Archived must enter recovery (exit 6)")
        stdout = json.loads(result.stdout)
        self.assertEqual(stdout.get("state"), "recovery-required")
        # Raw failure text never reaches CLI output; only the hashed
        # category/fingerprint enter the persisted Recovery Bundle.
        self.assertNotIn("error", stdout)

    def test_slice2_inspect_wrong_mode_rejected(self) -> None:
        """CLI tracer: inspect with Mode=auto (not bypassPermissions) must be
        rejected at bootstrap."""
        contract = _collab_contract(
            self.repo,
            **{
                "writer_lease": {"holder": "claude", "state": "inactive"},
                "state": "ready",
                "required_manual_skills": [
                    {"name": "implement", "host": "claude",
                     "status": "required", "invocation": None},
                ],
            },
        )
        _write_bridge(self.repo, contract)

        cp = self.root / "contract.json"
        cp.write_text(json.dumps(contract, ensure_ascii=True), encoding="utf-8")

        fake_dir = Path(self._temp.name) / "fake_paseo"
        fake_dir.mkdir()
        events_path = str(fake_dir / "events.jsonl")
        self._write_fake_paseo(fake_dir, events_path, str(self.repo))

        env = os.environ.copy()
        if "PYTHONPATH" not in env:
            env["PYTHONPATH"] = str(ROOT)
        env["PATH"] = str(fake_dir) + os.pathsep + env.get("PATH", "")
        env["PASEO_FAKE_EVENTS"] = events_path
        env["PASEO_FAKE_REPO"] = str(self.repo)
        self._configure_fake_paseo(fake_dir, inspect_json={
            "Provider": "claude",
            "Model": "deepseek-v4-flash", "Cwd": str(self.repo),
            "Status": "idle", "Mode": "auto", "Archived": False,
        })

        result = subprocess.run(
            [sys.executable, "-m", "harness", "codex-paseo-claude",
             "bootstrap", str(cp),
             "--provider", "claude/deepseek-v4-flash"],
            cwd=self.repo, env=env, capture_output=True, text=True,
            encoding="utf-8",
        )
        self.assertNotEqual(result.returncode, 0,
                           "bootstrap must reject inspect with wrong Mode")
        stdout = json.loads(result.stdout)
        self.assertEqual(stdout.get("state"), "recovery-required")
        # Raw failure text never reaches CLI output (hashed bundle only).
        self.assertNotIn("error", stdout)

    def test_slice2_dispatch_rejects_drifted_provider(self) -> None:
        """CLI tracer: dispatch must reject when live inspect Provider differs
        from the frozen bootstrap provider."""
        contract = _collab_contract(
            self.repo,
            **{
                "writer_lease": {"holder": "claude", "state": "inactive"},
                "state": "ready",
                "required_manual_skills": [
                    {"name": "implement", "host": "claude",
                     "status": "required", "invocation": None},
                ],
            },
        )
        _write_bridge(self.repo, contract)

        cp = self.root / "contract.json"
        cp.write_text(json.dumps(contract, ensure_ascii=True), encoding="utf-8")

        fake_dir = Path(self._temp.name) / "fake_paseo"
        fake_dir.mkdir()
        events_path = str(fake_dir / "events.jsonl")
        self._write_fake_paseo(fake_dir, events_path, str(self.repo))

        env = os.environ.copy()
        if "PYTHONPATH" not in env:
            env["PYTHONPATH"] = str(ROOT)
        env["PATH"] = str(fake_dir) + os.pathsep + env.get("PATH", "")
        env["PASEO_FAKE_EVENTS"] = events_path
        env["PASEO_FAKE_REPO"] = str(self.repo)

        # Bootstrap with claude/deepseek-v4-flash
        bs = subprocess.run(
            [sys.executable, "-m", "harness", "codex-paseo-claude",
             "bootstrap", str(cp),
             "--provider", "claude/deepseek-v4-flash"],
            cwd=self.repo, env=env, capture_output=True, text=True,
            encoding="utf-8",
        )
        self.assertEqual(bs.returncode, 0, f"bootstrap failed: {bs.stderr}")

        # Write and bind handoff
        handoff_dir = self.repo / ".harness" / "coordination" / "github-32"
        handoff_path = handoff_dir / "handoff.md"
        handoff_text = "Implement Issue #32."
        handoff_path.write_text(handoff_text, encoding="utf-8")
        handoff_digest = hashlib.sha256(handoff_text.encode("utf-8")).hexdigest()
        bridge_path = handoff_dir / "bridge-trigger.json"
        bridge_data = json.loads(bridge_path.read_text("utf-8"))
        bridge_data["handoff_digest"] = handoff_digest
        bridge_path.write_text(json.dumps(bridge_data), encoding="utf-8")

        # Mutate: inspect now returns Provider=codex instead of claude
        # Omit Id so the fake Paseo fills it from the CLI args (real agent_id)
        self._configure_fake_paseo(fake_dir, inspect_json={
            "Provider": "codex",
            "Model": "deepseek-v4-flash", "Cwd": str(self.repo),
            "Status": "idle", "Mode": "bypassPermissions", "Archived": False,
        })

        disp = subprocess.run(
            [sys.executable, "-m", "harness", "codex-paseo-claude",
             "dispatch", "--task", "github-32",
             "--handoff", str(handoff_path),
             "--cwd", str(self.repo)],
            cwd=self.repo, env=env, capture_output=True, text=True,
            encoding="utf-8",
        )
        self.assertNotEqual(disp.returncode, 0,
                           "dispatch must reject drifted inspect Provider")
        self.assertEqual(disp.returncode, 6,
                        "drifted Provider must enter recovery (exit 6)")
        stdout = json.loads(disp.stdout)
        self.assertEqual(stdout.get("state"), "recovery-required")
        # The adapter error is hashed into the recovery fingerprint; the
        # recovery bundle embeds an adapter-failure category.
        self.assertEqual(
            stdout.get("recovery_bundle", {}).get("failure", {}).get("category"),
            "adapter-failure",
        )

    def test_slice2_report_obtains_live_idle_proof(self) -> None:
        """CLI tracer: report must call live inspect and reject if agent is
        still active (not idle/stopped).  No run.json mutation needed."""
        contract = _collab_contract(
            self.repo,
            **{
                "writer_lease": {"holder": "claude", "state": "inactive"},
                "state": "ready",
                "required_manual_skills": [
                    {"name": "implement", "host": "claude",
                     "status": "required", "invocation": None},
                ],
            },
        )
        # Handoff must exist before bootstrap: its digest binds the bridge trigger.
        handoff_dir = self.repo / ".harness" / "coordination" / "github-32"
        handoff_dir.mkdir(parents=True, exist_ok=True)
        handoff_path = handoff_dir / "handoff.md"
        handoff_text = "Implement Issue #32."
        handoff_path.write_text(handoff_text, encoding="utf-8")
        handoff_digest = hashlib.sha256(handoff_text.encode("utf-8")).hexdigest()
        _write_bridge(self.repo, contract, handoff_digest=handoff_digest)

        cp = self.root / "contract.json"
        cp.write_text(json.dumps(contract, ensure_ascii=True), encoding="utf-8")

        fake_dir = Path(self._temp.name) / "fake_paseo"
        fake_dir.mkdir()
        events_path = str(fake_dir / "events.jsonl")
        self._write_fake_paseo(fake_dir, events_path, str(self.repo))

        env = os.environ.copy()
        if "PYTHONPATH" not in env:
            env["PYTHONPATH"] = str(ROOT)
        env["PATH"] = str(fake_dir) + os.pathsep + env.get("PATH", "")
        env["PASEO_FAKE_EVENTS"] = events_path
        env["PASEO_FAKE_REPO"] = str(self.repo)

        # Bootstrap + dispatch
        bs = subprocess.run(
            [sys.executable, "-m", "harness", "codex-paseo-claude",
             "bootstrap", str(cp),
             "--provider", "claude/deepseek-v4-flash"],
            cwd=self.repo, env=env, capture_output=True, text=True,
            encoding="utf-8",
        )
        self.assertEqual(bs.returncode, 0, f"bootstrap failed: {bs.stderr}")

        disp = subprocess.run(
            [sys.executable, "-m", "harness", "codex-paseo-claude",
             "dispatch", "--task", "github-32",
             "--handoff", str(handoff_path),
             "--cwd", str(self.repo)],
            cwd=self.repo, env=env, capture_output=True, text=True,
            encoding="utf-8",
        )
        self.assertEqual(disp.returncode, 0, f"dispatch failed: {disp.stderr}")

        # Make inspect return Status=active (not idle/stopped). Omit Id so
        # the fake Paseo fills it from the CLI args (real agent_id).
        self._configure_fake_paseo(fake_dir, inspect_json={
            "Provider": "claude",
            "Model": "deepseek-v4-flash", "Cwd": str(self.repo),
            "Status": "active", "Mode": "bypassPermissions", "Archived": False,
        })

        # Write owned file for diff
        (self.repo / "harness").mkdir(parents=True, exist_ok=True)
        (self.repo / "harness" / "paseo_collaboration.py").write_text(
            "# report test\n", encoding="utf-8")
        _git(self.repo, "add", "harness/paseo_collaboration.py")

        from harness.codex_direct import _diff_digest
        diff_digest = _diff_digest(Path(self.repo))

        # Read the real agent_id from launch.json (written by dispatch).
        # launch.json lives under .harness/runtime/<wt>/tasks/<key>/,
        # not under .harness/coordination/.
        runtime_dir = self.repo / ".harness" / "runtime"
        launch_paths = list(runtime_dir.rglob("launch.json"))
        self.assertEqual(len(launch_paths), 1, f"expected 1 launch.json, found {launch_paths}")
        launch_data = json.loads(launch_paths[0].read_text("utf-8"))
        real_agent_id = launch_data["agent_id"]

        # Report via CLI — must fail because agent is "active" not idle/stopped
        report_json_path = self.root / "report.json"
        report_json_path.write_text(json.dumps({
            "schema": "harness.paseo-writer-report/v1",
            "task_id": "github-32", "mode": "codex-paseo-claude",
            "agent_id": real_agent_id,
            "summary": "Report with active agent.",
            "files_changed": ["harness/paseo_collaboration.py"],
            "diff_digest": diff_digest,
            "commands": [{"id": "test", "digest": "aa" * 32,
                          "status": "pass", "exit_code": 0}],
            "skipped_checks": [], "risks": [],
            "criterion_evidence": [
                {"id": "preflight-readonly", "status": "pass",
                 "digest": "cc" * 32},
            ],
        }), encoding="utf-8")
        rep = subprocess.run(
            [sys.executable, "-m", "harness", "codex-paseo-claude",
             "report", str(report_json_path),
             "--task", "github-32",
             "--cwd", str(self.repo)],
            cwd=self.repo, env=env, capture_output=True, text=True,
            encoding="utf-8",
        )
        self.assertNotEqual(rep.returncode, 0,
                           "report must reject active agent via live inspect")
        self.assertEqual(rep.returncode, 6,
                        "active agent must enter recovery (exit 6)")
        stdout = json.loads(rep.stdout)
        self.assertEqual(stdout.get("state"), "recovery-required")
        self.assertEqual(
            stdout.get("recovery_bundle", {}).get("failure", {}).get("category"),
            "adapter-failure",
        )


    # -- Slice 1(b): cross-worktree bridge reminder dedup ------------------

    def test_slice1b_cross_worktree_reminder_dedup(self) -> None:
        """Missing bridge must be repository-wide deduplicated across linked
        worktrees via ``_manual_skill_was_reminded_elsewhere``."""
        # -- linked worktree -------------------------------------------------
        linked_wt = self.root / "linked-wt"
        _git(self.repo, "worktree", "add", str(linked_wt), "-b", "linked-1")
        self.addCleanup(lambda: _git(self.repo, "worktree", "remove", "--force",
                                     str(linked_wt)))

        # -- contract per worktree (same task_id) -----------------------------
        contract_main = _collab_contract(
            self.repo,
            **{
                "writer_lease": {"holder": "claude", "state": "inactive"},
                "state": "ready",
                "required_manual_skills": [
                    {"name": "implement", "host": "claude",
                     "status": "required", "invocation": None},
                ],
            },
        )
        contract_linked = _collab_contract(
            linked_wt,
            **{
                "writer_lease": {"holder": "claude", "state": "inactive"},
                "state": "ready",
                "required_manual_skills": [
                    {"name": "implement", "host": "claude",
                     "status": "required", "invocation": None},
                ],
            },
        )
        contract_linked["execution"]["branch"] = "linked-1"
        contract_main["execution"]["branch"] = "main"
        # NO bridge trigger — bridge is missing for both

        cp_main = self.root / "contract-main.json"
        cp_main.write_text(json.dumps(contract_main, ensure_ascii=True), encoding="utf-8")
        cp_linked = self.root / "contract-linked.json"
        cp_linked.write_text(json.dumps(contract_linked, ensure_ascii=True), encoding="utf-8")

        # -- fake Paseo -------------------------------------------------------
        fake_dir = Path(self._temp.name) / "fake_paseo"
        fake_dir.mkdir()
        events_path = str(fake_dir / "events.jsonl")
        self._write_fake_paseo(fake_dir, events_path, str(self.repo))

        env = os.environ.copy()
        if "PYTHONPATH" not in env:
            env["PYTHONPATH"] = str(ROOT)
        env["PATH"] = str(fake_dir) + os.pathsep + env.get("PATH", "")
        env["PASEO_FAKE_EVENTS"] = events_path
        env["PASEO_FAKE_REPO"] = str(self.repo)

        # -- call 1: main worktree → reminder emitted, exit 3 -----------------
        r1 = subprocess.run(
            [sys.executable, "-m", "harness", "codex-paseo-claude",
             "bootstrap", str(cp_main),
             "--provider", "claude/deepseek-v4-flash"],
            cwd=self.repo, env=env, capture_output=True, text=True,
            encoding="utf-8",
        )
        self.assertEqual(r1.returncode, 3,
                         f"missing bridge must exit 3; got {r1.returncode}. "
                         f"stderr: {r1.stderr}")
        ms1 = json.loads(r1.stdout).get("manual_skill", {})
        self.assertEqual(ms1.get("status"), "reminder-emitted",
                         f"first call must emit reminder; got {ms1}")

        # -- verify NO run.json in either worktree ----------------------------
        for wt in (self.repo, linked_wt):
            rt = wt / ".harness" / "runtime"
            runs = list(rt.rglob("run.json")) if rt.exists() else []
            self.assertFalse(runs,
                             f"missing bridge must not create run.json in {wt}; "
                             f"found {runs}")

        # -- verify NO paseo run event ----------------------------------------
        run_events = 0
        if Path(events_path).exists():
            for line in Path(events_path).read_text("utf-8").splitlines():
                if not line.strip():
                    continue
                evt = json.loads(line)
                if isinstance(evt.get("cmd"), list) and evt["cmd"] and evt["cmd"][0] == "run":
                    run_events += 1
        self.assertEqual(run_events, 0,
                         "missing bridge must not create paseo agent")

        # -- call 2: linked worktree → SHOULD be already-reminded -------------
        # Use PASEO_FAKE_EVENTS reset so old events don't confuse
        events2 = str(fake_dir / "events2.jsonl")
        env2 = dict(env)
        self._configure_fake_paseo(
            fake_dir, events=events2, repo=str(linked_wt)
        )
        r2 = subprocess.run(
            [sys.executable, "-m", "harness", "codex-paseo-claude",
             "bootstrap", str(cp_linked),
             "--provider", "claude/deepseek-v4-flash"],
            cwd=linked_wt, env=env2, capture_output=True, text=True,
            encoding="utf-8",
        )
        self.assertEqual(r2.returncode, 3,
                         f"linked worktree missing bridge must exit 3; "
                         f"got {r2.returncode}. stderr: {r2.stderr}")

        ms2 = json.loads(r2.stdout).get("manual_skill", {})
        self.assertEqual(
            ms2.get("status"), "already-reminded",
            f"linked worktree must report already-reminded via repository-wide "
            f"dedup; got {ms2}",
        )

        # -- still no run.json at the linked worktree -------------------------
        rt2 = linked_wt / ".harness" / "runtime"
        runs2 = list(rt2.rglob("run.json")) if rt2.exists() else []
        self.assertFalse(runs2, "linked worktree must not create run.json")

        # -- still no paseo run event -----------------------------------------
        run2 = 0
        if Path(events2).exists():
            for line in Path(events2).read_text("utf-8").splitlines():
                if not line.strip():
                    continue
                evt = json.loads(line)
                if isinstance(evt.get("cmd"), list) and evt["cmd"] and evt["cmd"][0] == "run":
                    run2 += 1
        self.assertEqual(run2, 0, "linked worktree must not create paseo agent")

    # -- Slice 1(c): sibling worktree active lease rejection ------------------

    def test_slice1c_sibling_worktree_rejects_active_lease(self) -> None:
        """Sibling worktree with same task source must be rejected by
        ``_reject_ticket_in_other_worktree`` before creating a second agent."""
        # -- linked worktree -------------------------------------------------
        linked_wt = self.root / "linked-wt"
        _git(self.repo, "worktree", "add", str(linked_wt), "-b", "linked-2")
        self.addCleanup(lambda: _git(self.repo, "worktree", "remove", "--force",
                                     str(linked_wt)))

        # -- contracts per worktree (same task_id, same source) --------------
        contract_main = _collab_contract(
            self.repo,
            **{
                "writer_lease": {"holder": "claude", "state": "inactive"},
                "state": "ready",
                "required_manual_skills": [
                    {"name": "implement", "host": "claude",
                     "status": "required", "invocation": None},
                ],
            },
        )
        contract_linked = _collab_contract(
            linked_wt,
            **{
                "writer_lease": {"holder": "claude", "state": "inactive"},
                "state": "ready",
                "required_manual_skills": [
                    {"name": "implement", "host": "claude",
                     "status": "required", "invocation": None},
                ],
            },
        )
        contract_linked["execution"]["branch"] = "linked-2"
        contract_main["execution"]["branch"] = "main"
        # Bridge trigger present in BOTH worktrees
        _write_bridge(self.repo, contract_main)
        _write_bridge(linked_wt, contract_linked)
        # Patch the linked bridge branch to match (it defaults to "main")
        linked_bridge_path = linked_wt / ".harness" / "coordination" / "github-32" / "bridge-trigger.json"
        lb = json.loads(linked_bridge_path.read_text("utf-8"))
        lb["branch"] = "linked-2"
        linked_bridge_path.write_text(json.dumps(lb), encoding="utf-8")

        cp_main = self.root / "contract-main.json"
        cp_main.write_text(json.dumps(contract_main, ensure_ascii=True), encoding="utf-8")
        cp_linked = self.root / "contract-linked.json"
        cp_linked.write_text(json.dumps(contract_linked, ensure_ascii=True), encoding="utf-8")

        # -- fake Paseo -------------------------------------------------------
        fake_dir = Path(self._temp.name) / "fake_paseo"
        fake_dir.mkdir()
        events_path = str(fake_dir / "events.jsonl")
        self._write_fake_paseo(fake_dir, events_path, str(self.repo))

        env = os.environ.copy()
        if "PYTHONPATH" not in env:
            env["PYTHONPATH"] = str(ROOT)
        env["PATH"] = str(fake_dir) + os.pathsep + env.get("PATH", "")
        env["PASEO_FAKE_EVENTS"] = events_path
        env["PASEO_FAKE_REPO"] = str(self.repo)

        # -- call 1: main worktree → success, creates agent -------------------
        r1 = subprocess.run(
            [sys.executable, "-m", "harness", "codex-paseo-claude",
             "bootstrap", str(cp_main),
             "--provider", "claude/deepseek-v4-flash"],
            cwd=self.repo, env=env, capture_output=True, text=True,
            encoding="utf-8",
        )
        self.assertEqual(r1.returncode, 0,
                         f"main bootstrap must succeed; got {r1.returncode}. "
                         f"stderr: {r1.stderr}")
        main_stdout = json.loads(r1.stdout)
        self.assertEqual(main_stdout.get("state"), "executing")

        # ---- count paseo run events after call 1 ----------------------------
        run_events_1 = 0
        if Path(events_path).exists():
            for line in Path(events_path).read_text("utf-8").splitlines():
                if not line.strip():
                    continue
                evt = json.loads(line)
                if isinstance(evt.get("cmd"), list) and evt["cmd"] and evt["cmd"][0] == "run":
                    run_events_1 += 1
        self.assertEqual(run_events_1, 1, "first bootstrap must create 1 agent")

        # -- call 2: linked worktree → SHOULD be rejected (same task source) --
        events2 = str(fake_dir / "events2.jsonl")
        env2 = dict(env)
        self._configure_fake_paseo(
            fake_dir, events=events2, repo=str(linked_wt)
        )
        r2 = subprocess.run(
            [sys.executable, "-m", "harness", "codex-paseo-claude",
             "bootstrap", str(cp_linked),
             "--provider", "claude/deepseek-v4-flash"],
            cwd=linked_wt, env=env2, capture_output=True, text=True,
            encoding="utf-8",
        )
        # GREEN: sibling worktree rejected by _reject_ticket_in_other_worktree
        stdout2 = json.loads(r2.stdout)
        self.assertNotEqual(
            r2.returncode, 0,
            f"sibling worktree must be rejected. "
            f"Got exit={r2.returncode} state={stdout2.get('state')} "
            f"error={stdout2.get('error')}",
        )
        self.assertEqual(
            stdout2.get("state"), "rejected",
            f"sibling worktree must be rejected; got {stdout2}",
        )

        # ---- count paseo run events after call 2: zero second agent ---------
        run2 = 0
        if Path(events2).exists():
            for line in Path(events2).read_text("utf-8").splitlines():
                if not line.strip():
                    continue
                evt = json.loads(line)
                if isinstance(evt.get("cmd"), list) and evt["cmd"] and evt["cmd"][0] == "run":
                    run2 += 1
        self.assertEqual(
            run2, 0,
            "sibling worktree must not create a second paseo agent",
        )


if __name__ == "__main__":
    unittest.main()
