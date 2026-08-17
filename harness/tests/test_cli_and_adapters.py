from __future__ import annotations

import hashlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from harness.capabilities import (
    MAX_MANUAL_SKILL_REMINDERS,
    check_manual_skill,
    doctor_report,
)
from harness.cli import _hook_control, main
from harness.codex_direct import _validate_recovery_bundle_shape, _validate_run_shape
from harness.context import WorktreeContext, discover_worktree
from harness.events import normalize_hook_event
from harness.safe_io import read_bounded_jsonl


ROOT = Path(__file__).resolve().parents[2]


class CliAndAdapterTests(unittest.TestCase):
    def test_capability_serve_retains_per_message_bound(self) -> None:
        stdin = io.TextIOWrapper(io.BytesIO(b"{" + b" " * (64 * 1024)))
        stdout = io.StringIO()

        with patch("sys.stdin", stdin), redirect_stdout(stdout):
            status = main(
                [
                    "capability",
                    "serve",
                    "--cwd",
                    str(ROOT),
                    "--name",
                    "safe-build-fixture",
                    "--adapter",
                    "codex-direct",
                ]
            )

        self.assertEqual(status, 2)
        self.assertIn("input exceeds its bound", stdout.getvalue())

    def test_capability_serve_processes_messages_until_eof(self) -> None:
        requests = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
                "params": {},
            },
            *[
                {"jsonrpc": "2.0", "id": index, "method": "tools/list", "params": {}}
                for index in range(2, 35)
            ],
        ]
        stdin = io.TextIOWrapper(
            io.BytesIO("".join(json.dumps(item) + "\n" for item in requests).encode())
        )
        stdout = io.StringIO()

        def respond(
            _context: WorktreeContext, *, name: str, adapter: str, value: object
        ) -> dict[str, object] | None:
            del name, adapter
            message = value if isinstance(value, dict) else {}
            if message.get("method") == "notifications/initialized":
                return None
            return {"jsonrpc": "2.0", "id": message["id"], "result": {}}

        with patch("sys.stdin", stdin), patch(
            "harness.cli.mcp_surface_message", side_effect=respond
        ), redirect_stdout(stdout):
            status = main(
                [
                    "capability",
                    "serve",
                    "--cwd",
                    str(ROOT),
                    "--name",
                    "safe-build-fixture",
                    "--adapter",
                    "codex-direct",
                ]
            )

        self.assertEqual(status, 0, stdout.getvalue())
        responses = [json.loads(line) for line in stdout.getvalue().splitlines()]
        self.assertEqual([item["id"] for item in responses], [1, *range(2, 35)])

    def test_capability_serve_rejects_initialize_as_a_notification(self) -> None:
        stdin = io.TextIOWrapper(
            io.BytesIO(b'{"jsonrpc":"2.0","method":"initialize","params":{}}\n')
        )
        stdout = io.StringIO()
        canonical = {
            "name": "safe-build-fixture",
            "version": "1.0.0",
            "surface": {"kind": "mcp"},
        }
        context = WorktreeContext(
            root=ROOT,
            git_dir=ROOT / ".git",
            common_git_dir=ROOT / ".git",
            head_sha="0" * 40,
            worktree_id="wt-test",
            repository_id="repo-test",
        )

        with patch("sys.stdin", stdin), patch(
            "harness.cli.discover_worktree", return_value=context
        ), patch(
            "harness.evolution.discover_surface_capabilities",
            return_value={"capabilities": [{"name": canonical["name"]}]},
        ), patch(
            "harness.evolution._surface_canonical", return_value=canonical
        ), redirect_stdout(stdout):
            status = main(
                [
                    "capability",
                    "serve",
                    "--cwd",
                    str(ROOT),
                    "--name",
                    canonical["name"],
                    "--adapter",
                    "codex-direct",
                ]
            )

        self.assertEqual(status, 2)
        self.assertIn("MCP notification is invalid", stdout.getvalue())

    def test_capability_serve_returns_method_not_found_and_continues(self) -> None:
        messages = [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {},
                    "clientInfo": {"name": "test-client", "version": "1"},
                    "_meta": {
                        "io.modelcontextprotocol/related-task": {"taskId": "task-1"}
                    },
                },
            },
            {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
                "params": {"_meta": {"trace": "bounded"}},
            },
            {"jsonrpc": "2.0", "id": 2, "method": "resources/list"},
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "stale-tool"},
            },
            {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "ping",
                "params": {"_meta": {"progressToken": "ping-1"}},
            },
        ]
        stdin = io.TextIOWrapper(
            io.BytesIO(
                "".join(json.dumps(item) + "\n" for item in messages).encode()
            )
        )
        stdout = io.StringIO()
        canonical = {
            "name": "safe-build-fixture",
            "version": "1.0.0",
            "surface": {"kind": "mcp"},
            "skill": {"interface": {"operations": ["inspect"]}},
        }
        context = WorktreeContext(
            root=ROOT,
            git_dir=ROOT / ".git",
            common_git_dir=ROOT / ".git",
            head_sha="0" * 40,
            worktree_id="wt-test",
            repository_id="repo-test",
        )

        with patch("sys.stdin", stdin), patch(
            "harness.cli.discover_worktree", return_value=context
        ), patch(
            "harness.evolution.discover_surface_capabilities",
            return_value={"capabilities": [{"name": canonical["name"]}]},
        ), patch(
            "harness.evolution._surface_canonical", return_value=canonical
        ), redirect_stdout(stdout):
            status = main(
                [
                    "capability",
                    "serve",
                    "--cwd",
                    str(ROOT),
                    "--name",
                    canonical["name"],
                    "--adapter",
                    "codex-direct",
                ]
            )

        self.assertEqual(status, 0, stdout.getvalue())
        responses = [json.loads(line) for line in stdout.getvalue().splitlines()]
        self.assertEqual([item["id"] for item in responses], [1, 2, 3, 4])
        self.assertEqual(responses[1]["error"]["code"], -32601)
        self.assertEqual(responses[2]["error"]["code"], -32602)
        self.assertEqual(responses[3]["result"], {})

    def test_capability_serve_returns_invalid_params_and_continues(self) -> None:
        messages = [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {},
                    "clientInfo": {"name": "test-client", "version": "1"},
                },
            },
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "inspect", "arguments": {"invalid": True}},
            },
            {"jsonrpc": "2.0", "id": 3, "method": "ping"},
        ]
        stdin = io.TextIOWrapper(
            io.BytesIO(
                "".join(json.dumps(item) + "\n" for item in messages).encode()
            )
        )
        stdout = io.StringIO()
        canonical = {
            "name": "safe-build-fixture",
            "version": "1.0.0",
            "surface": {"kind": "mcp"},
            "skill": {"interface": {"operations": ["inspect"]}},
        }
        context = WorktreeContext(
            root=ROOT,
            git_dir=ROOT / ".git",
            common_git_dir=ROOT / ".git",
            head_sha="0" * 40,
            worktree_id="wt-test",
            repository_id="repo-test",
        )

        with patch("sys.stdin", stdin), patch(
            "harness.cli.discover_worktree", return_value=context
        ), patch(
            "harness.evolution.discover_surface_capabilities",
            return_value={"capabilities": [{"name": canonical["name"]}]},
        ), patch(
            "harness.evolution._surface_canonical", return_value=canonical
        ), redirect_stdout(stdout):
            status = main(
                [
                    "capability",
                    "serve",
                    "--cwd",
                    str(ROOT),
                    "--name",
                    canonical["name"],
                    "--adapter",
                    "codex-direct",
                ]
            )

        self.assertEqual(status, 0, stdout.getvalue())
        responses = [json.loads(line) for line in stdout.getvalue().splitlines()]
        self.assertEqual([item["id"] for item in responses], [1, 2, 3])
        self.assertEqual(responses[1]["error"]["code"], -32602)
        self.assertEqual(responses[2]["result"], {})

    def test_three_adapter_conformance_uses_one_contract_and_kernel(self) -> None:
        fixture = json.loads(
            (
                ROOT / "harness" / "fixtures" / "three-adapter-conformance.json"
            ).read_text(encoding="utf-8")
        )

        self.assertEqual(fixture["schema"], "harness.adapter-conformance/v1")
        self.assertEqual(fixture["contract_schema"], "harness.task-contract/v1")
        self.assertEqual(fixture["constitutional_kernel"], "RULES.md")
        self.assertEqual(
            {adapter["mode"] for adapter in fixture["adapters"]},
            {"codex-direct", "claude-direct", "codex-paseo-claude"},
        )
        self.assertEqual(
            fixture["pilot_checks"],
            [
                "mode-frozen-before-write",
                "second-writer-rejected",
                "manual-skill-reminder-no-write",
                "adapter-failure-stop-and-report",
                "ordinary-full-access-no-noise",
                "protected-effects",
                "exact-one-local-commit-no-remote",
                "canonical-worktree-dirty-primary-isolation",
                "typed-redacted-events",
                "capability-discovery-drift",
                "typed-memory-evolution",
            ],
        )
        self.assertEqual(
            fixture["migration_checks"],
            [
                "product-verification",
                "package-exclusion",
                "durable-memory",
                "clean-room",
            ],
        )

    def test_real_pilots_cover_the_shared_conformance_matrix(self) -> None:
        fixture_root = ROOT / "harness" / "fixtures"
        artifact_root = fixture_root / "pilot-artifacts"
        matrix = json.loads(
            (fixture_root / "three-adapter-conformance.json").read_text(
                encoding="utf-8"
            )
        )
        evidence = json.loads(
            (fixture_root / "three-adapter-pilot-evidence.json").read_text(
                encoding="utf-8"
            )
        )

        def digest(value: object) -> str:
            return hashlib.sha256(
                json.dumps(
                    value,
                    ensure_ascii=True,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()

        def exact_keys(value: dict[str, object], expected: set[str]) -> None:
            self.assertEqual(set(value), expected)

        def load_artifact(reference: dict[str, object]) -> dict[str, object]:
            exact_keys(reference, {"file", "sha256", "checks"})
            name = reference["file"]
            self.assertIsInstance(name, str)
            self.assertEqual(Path(name).name, name)
            raw = (artifact_root / name).read_bytes()
            canonical = raw.replace(b"\r\n", b"\n")
            self.assertEqual(hashlib.sha256(canonical).hexdigest(), reference["sha256"])
            return json.loads(raw)

        def git_object_id(kind: str, raw: bytes) -> str:
            header = f"{kind} {len(raw)}\0".encode("ascii")
            return hashlib.sha1(header + raw).hexdigest()

        def tree_object_id(entries: list[dict[str, str]]) -> str:
            raw = b"".join(
                entry["mode"].encode("ascii")
                + b" "
                + entry["name"].encode("utf-8")
                + b"\0"
                + bytes.fromhex(entry["oid"])
                for entry in sorted(entries, key=lambda item: item["name"].encode())
            )
            return git_object_id("tree", raw)

        def validate_run(run: dict) -> None:
            execution = run["contract"]["execution"]
            context = WorktreeContext(
                root=ROOT,
                git_dir=ROOT / ".git",
                common_git_dir=ROOT / ".git",
                head_sha=run["baseline"]["head_sha"],
                worktree_id=execution["worktree_id"],
                repository_id=execution["repository_id"],
            )
            _validate_run_shape(run, context, run["contract"]["task"]["id"])

        exact_keys(evidence, {"schema", "matrix_digest", "pilots", "migration"})
        self.assertEqual(evidence["schema"], "harness.adapter-pilot-evidence/v1")
        self.assertEqual(evidence["matrix_digest"], digest(matrix))
        self.assertEqual(
            {pilot["mode"] for pilot in evidence["pilots"]},
            {adapter["mode"] for adapter in matrix["adapters"]},
        )
        pilot_artifacts = []
        for reference in evidence["pilots"]:
            with self.subTest(mode=reference["mode"]):
                exact_keys(reference, {"mode", "file", "sha256", "checks"})
                self.assertEqual(set(reference["checks"]), set(matrix["pilot_checks"]))
                self.assertEqual(set(reference["checks"].values()), {"pass"})
                artifact = load_artifact(
                    {key: reference[key] for key in ("file", "sha256", "checks")}
                )
                pilot_artifacts.append(artifact)
                exact_keys(
                    artifact,
                    {
                        "schema",
                        "mode",
                        "controller_run",
                        "git",
                        "events",
                        "manual_gate",
                        "recovery",
                        "authority",
                        "capability",
                        "memory_evolution",
                    },
                )
                self.assertEqual(artifact["schema"], "harness.pilot-artifact/v1")
                self.assertEqual(artifact["mode"], reference["mode"])
                adapter = next(
                    item
                    for item in matrix["adapters"]
                    if item["mode"] == artifact["mode"]
                )

                run = artifact["controller_run"]
                validate_run(run)
                self.assertEqual(run["schema"], adapter["run_schema"])
                self.assertEqual(run["state"], "accepted")
                self.assertEqual(run["contract"]["execution"]["mode"], artifact["mode"])
                self.assertEqual(
                    run["contract"]["writer_lease"],
                    {"holder": adapter["writer"], "state": "released"},
                )
                self.assertEqual(run["accepted_diff"]["paths"], ["pilot.txt"])
                self.assertEqual(run["commit_sha"], artifact["git"]["accepted"]["oid"])

                git = artifact["git"]
                exact_keys(
                    git,
                    {
                        "base",
                        "accepted",
                        "trees",
                        "files",
                        "commit_count",
                        "changed_paths",
                        "remote_effects",
                    },
                )
                self.assertEqual(git["commit_count"], 1)
                self.assertEqual(git["changed_paths"], ["pilot.txt"])
                self.assertEqual(git["remote_effects"], [])
                for name in ("base", "accepted"):
                    commit = git[name]
                    exact_keys(commit, {"oid", "raw"})
                    raw = commit["raw"].encode("utf-8")
                    self.assertEqual(git_object_id("commit", raw), commit["oid"])
                    tree_line = next(
                        line
                        for line in commit["raw"].splitlines()
                        if line.startswith("tree ")
                    )
                    self.assertEqual(
                        tree_line.removeprefix("tree "),
                        tree_object_id(git["trees"][name]),
                    )
                self.assertIn(f"parent {git['base']['oid']}\n", git["accepted"]["raw"])
                self.assertEqual(run["baseline"]["head_sha"], git["base"]["oid"])
                for tree in git["trees"].values():
                    for entry in tree:
                        exact_keys(entry, {"mode", "name", "oid"})
                        self.assertEqual(entry["mode"], "100644")
                        content = git["files"][entry["name"]].encode("utf-8")
                        self.assertEqual(entry["oid"], git_object_id("blob", content))
                base_paths = {entry["name"] for entry in git["trees"]["base"]}
                accepted_paths = {entry["name"] for entry in git["trees"]["accepted"]}
                self.assertEqual(accepted_paths - base_paths, {"pilot.txt"})
                pilot_digest = hashlib.sha256(
                    git["files"]["pilot.txt"].encode("utf-8")
                ).hexdigest()
                self.assertEqual(
                    run["accepted_diff"]["snapshot"][0]["digest"], pilot_digest
                )

                self.assertEqual(
                    artifact["manual_gate"],
                    {
                        "first": "reminder-emitted",
                        "second": "already-reminded",
                        "implementation_write_count": 0,
                    },
                )
                exact_keys(artifact["recovery"], {"run", "bundle"})
                recovery_run = artifact["recovery"]["run"]
                recovery_bundle = artifact["recovery"]["bundle"]
                validate_run(recovery_run)
                _validate_recovery_bundle_shape(
                    recovery_bundle,
                    recovery_run,
                    recovery_run["recovery_bundle"],
                )
                self.assertEqual(
                    recovery_bundle["adapter_switch_policy"], "stop-and-report"
                )
                self.assertEqual(recovery_bundle["changed_path_count"], 0)
                self.assertEqual(
                    artifact["authority"],
                    {
                        "ordinary": "allowed",
                        "ssh": "blocked",
                        "publish": "user-authorization-required",
                        "second_writer": "rejected",
                    },
                )
                self.assertEqual(artifact["capability"]["status"], "pass")
                self.assertEqual(artifact["memory_evolution"]["status"], "pass")
                exact_keys(artifact["capability"], {"status", "command_id"})
                exact_keys(artifact["memory_evolution"], {"status", "command_id"})
                self.assertEqual(
                    {event["terminal_state"] for event in artifact["events"]},
                    {"active", "stopped"},
                )
                for event in artifact["events"]:
                    exact_keys(
                        event,
                        {
                            "schema",
                            "timestamp",
                            "source_adapter",
                            "provenance",
                            "sensitivity",
                            "digest",
                            "terminal_state",
                            "session_id",
                            "event_id",
                            "semantic",
                            "repository_id",
                            "worktree_id",
                            "head_sha",
                        },
                    )
                    event_source = {
                        key: event[key]
                        for key in (
                            "session_id",
                            "provenance",
                            "sensitivity",
                            "terminal_state",
                            "semantic",
                        )
                    }
                    self.assertEqual(event["digest"], digest(event_source))
                    self.assertEqual(event["event_id"], event["digest"][:20])
                    self.assertEqual(event["sensitivity"], "metadata")
                    exact_keys(event["provenance"], {"adapter", "host_event"})
                    exact_keys(
                        event["semantic"],
                        {
                            "event",
                            "tool_class",
                            "category",
                            "outcome",
                            "exit_code",
                            "has_error",
                        },
                    )

        migration_reference = evidence["migration"]
        migration = load_artifact(migration_reference)
        self.assertEqual(
            set(migration_reference["checks"]), set(matrix["migration_checks"])
        )
        self.assertEqual(set(migration_reference["checks"].values()), {"pass"})
        exact_keys(
            migration,
            {
                "schema",
                "primary_checkout",
                "commands",
                "package",
                "durable_memory",
                "clean_room",
            },
        )
        self.assertEqual(migration["schema"], "harness.migration-artifact/v1")
        primary = migration["primary_checkout"]
        exact_keys(
            primary,
            {
                "head_sha",
                "branch",
                "status_digest_before",
                "status_digest_after",
                "receipt_digest",
            },
        )
        self.assertEqual(
            primary["status_digest_before"], primary["status_digest_after"]
        )
        self.assertEqual(
            primary["receipt_digest"],
            digest(
                {
                    key: value
                    for key, value in primary.items()
                    if key != "receipt_digest"
                }
            ),
        )
        expected_commands = {
            "product-build": "npm run build",
            "product-tests": "npm test",
            "harness-tests": (
                "python -m unittest harness.tests.test_contracts "
                "harness.tests.test_events "
                "harness.tests.test_claude_direct.ClaudeDirectProcessTests."
                "test_shared_fixture_drives_both_public_direct_lifecycles "
                "harness.tests.test_claude_direct.ClaudeDirectProcessTests."
                "test_guard_matches_the_shared_direct_authority_matrix "
                "harness.tests.test_claude_direct.ClaudeDirectProcessTests."
                "test_full_path_creates_exactly_one_scoped_local_commit_without_remote_effects "
                "harness.tests.test_claude_direct.ClaudeDirectProcessTests."
                "test_repeated_failure_without_progress_emits_a_complete_recovery_bundle "
                "harness.tests.test_paseo_collaboration.PaseoCollaborationFunctionTests."
                "test_shared_fixture_drives_public_paseo_lifecycle "
                "harness.tests.test_paseo_collaboration.PaseoCollaborationFunctionTests."
                "test_dispatch_rejects_second_call "
                "harness.tests.test_paseo_collaboration.PaseoCollaborationFunctionTests."
                "test_recovery_preserves_lease_and_mode"
            ),
            "typed-memory-evolution-tests": (
                "python -m unittest issue36-typed-memory-evolution-final"
            ),
        }
        commands = {item["id"]: item for item in migration["commands"]}
        self.assertEqual(set(commands), set(expected_commands))
        for command_id, command in commands.items():
            exact_keys(
                command,
                {
                    "id",
                    "argv_digest",
                    "status",
                    "exit_code",
                    "stdout_digest",
                    "stderr_digest",
                    "sensitivity",
                    "receipt_digest",
                },
            )
            self.assertEqual(
                command["argv_digest"], digest(expected_commands[command_id])
            )
            self.assertEqual(command["status"], "pass")
            self.assertEqual(command["exit_code"], 0)
            self.assertEqual(command["sensitivity"], "metadata")
            self.assertRegex(command["stdout_digest"], r"^[0-9a-f]{64}$")
            self.assertRegex(command["stderr_digest"], r"^[0-9a-f]{64}$")
            self.assertEqual(
                command["receipt_digest"],
                digest(
                    {
                        key: value
                        for key, value in command.items()
                        if key != "receipt_digest"
                    }
                ),
            )
        for artifact in pilot_artifacts:
            self.assertIn(artifact["capability"]["command_id"], commands)
            self.assertIn(artifact["memory_evolution"]["command_id"], commands)
        package = migration["package"]
        exact_keys(package, {"pack_output", "output_digest"})
        live_pack = subprocess.run(
            [
                shutil.which("npm") or "npm",
                "pack",
                "--dry-run",
                "--json",
                "--ignore-scripts",
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        live_pack_output = json.loads(live_pack.stdout)
        self.assertEqual(package["output_digest"], digest(package["pack_output"]))
        self.assertEqual(
            package["pack_output"][0]["name"], live_pack_output[0]["name"]
        )
        self.assertEqual(
            package["pack_output"][0]["version"], live_pack_output[0]["version"]
        )
        package_files = [item["path"] for item in live_pack_output[0]["files"]]
        forbidden = (
            "harness/",
            ".harness/",
            "docs/agent-memory/",
            "recovery-bundle",
            "events.jsonl",
        )
        self.assertFalse(
            [
                path
                for path in package_files
                if path.startswith(forbidden)
                or any(marker in path for marker in forbidden[3:])
            ]
        )
        required_memory = {
            "docs/agent-memory/project-facts.md",
            "docs/agent-memory/decisions.md",
            "docs/agent-memory/lessons-learned.md",
            "docs/agent-memory/codemap.md",
            "docs/agent-memory/harness-security.md",
            "docs/agent-memory/harness-eval.md",
            "docs/agent-memory/verification-log.md",
        }
        durable_memory = migration["durable_memory"]
        self.assertTrue(required_memory.issubset(durable_memory))
        for relative, expected_digest in durable_memory.items():
            raw = (ROOT / relative).read_bytes().replace(b"\r\n", b"\n")
            self.assertEqual(
                hashlib.sha256(raw).hexdigest(),
                expected_digest,
            )
        clean_room = migration["clean_room"]
        exact_keys(
            clean_room,
            {"base_sha", "copied_external_code", "paths", "review_repairs"},
        )
        self.assertFalse(clean_room["copied_external_code"])
        self.assertEqual(
            clean_room["base_sha"], "8de058e772e97a6ab8d16d65386081db76953320"
        )
        self.assertEqual(
            set(clean_room["paths"]),
            {
                "RULES.md",
                "harness/fixtures/evolution-build-capability.json",
                "harness/fixtures/evolution-build-surface.json",
            },
        )
        for relative in clean_room["paths"]:
            baseline = subprocess.check_output(
                ["git", "show", f"{clean_room['base_sha']}:{relative}"],
                cwd=ROOT,
            )
            current = subprocess.check_output(
                ["git", "show", f"HEAD:{relative}"], cwd=ROOT
            )
            self.assertEqual(baseline, current)
            subprocess.run(
                ["git", "diff", "--quiet", "--", relative],
                cwd=ROOT,
                check=True,
            )
        review_repairs = clean_room["review_repairs"]
        expected_repairs = {
            ".gitattributes": "pr-39-head-bound-memory-eol",
            "harness/cli.py": "pr-39-mcp-session-lifetime",
            "harness/codex_direct.py": "pr-39-verified-index-installation",
            "harness/contracts.py": "pr-39-canonical-task-source",
            "harness/evolution.py": "pr-39-verified-zero-candidate-channels",
            "harness/memory.py": "pr-39-recoverable-memory-transaction",
            "harness/paseo_collaboration.py": "pr-39-private-ephemeral-prompt-files",
            "harness/safe_io.py": "pr-39-verified-jsonl-descriptor",
        }
        exact_keys(review_repairs, set(expected_repairs))
        for relative, finding in expected_repairs.items():
            repair = review_repairs[relative]
            exact_keys(repair, {"finding", "sha256"})
            self.assertEqual(repair["finding"], finding)
            repaired = (ROOT / relative).read_bytes().replace(b"\r\n", b"\n")
            self.assertEqual(hashlib.sha256(repaired).hexdigest(), repair["sha256"])
            baseline = subprocess.run(
                ["git", "show", f"{clean_room['base_sha']}:{relative}"],
                cwd=ROOT,
                capture_output=True,
            )
            if relative == ".gitattributes":
                self.assertNotEqual(baseline.returncode, 0)
            else:
                self.assertEqual(baseline.returncode, 0)
                self.assertNotEqual(baseline.stdout, repaired)

        forbidden_raw_keys = {
            "command",
            "stdout",
            "stderr",
            "environment",
            "env",
            "credential",
            "credentials",
            "secret",
            "token",
        }

        def all_keys(value: object) -> set[str]:
            if isinstance(value, dict):
                return set(value) | {
                    key for child in value.values() for key in all_keys(child)
                }
            if isinstance(value, list):
                return {key for child in value for key in all_keys(child)}
            return set()

        self.assertTrue(forbidden_raw_keys.isdisjoint(all_keys(evidence)))
        self.assertTrue(forbidden_raw_keys.isdisjoint(all_keys(pilot_artifacts)))
        self.assertTrue(forbidden_raw_keys.isdisjoint(all_keys(migration)))

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
            tracked = {
                "hooks": {
                    "Stop": [{"hooks": [{"type": "command", "command": "tracked"}]}]
                }
            }
            local = {
                "hooks": {
                    "Stop": [{"hooks": [{"type": "command", "command": "local"}]}]
                }
            }
            (repo / ".claude" / "settings.json").write_text(
                json.dumps(tracked), encoding="utf-8"
            )
            (repo / ".claude" / "settings.local.json").write_text(
                json.dumps(local), encoding="utf-8"
            )

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
            with patch(
                "harness.cli.persist_hook_event", side_effect=OSError("fixture")
            ):
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
        self.assertIn("python -m harness claude-direct", claude)
        self.assertIn("Never control a Claude Direct task", claude)
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
        context_budget = (ROOT / ".codex" / "scripts" / "context_budget.py").read_text(
            encoding="utf-8"
        )
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

    def test_loop_step_cli_stops_without_progress_yields_and_never_switches(
        self,
    ) -> None:
        policy = {
            "origin": "accepted-gap",
            "max_attempts": 2,
            "no_progress_limit": 1,
            "yield_to_user": True,
            "adapter_switch_policy": "stop-and-report",
        }
        fingerprint = "1" * 64
        evidence = "2" * 64

        def run(
            *,
            attempts: list[dict[str, str]],
            requested: str = "codex-direct",
            user_input: bool = False,
        ) -> dict[str, object]:
            with tempfile.NamedTemporaryFile(
                "w", suffix=".json", encoding="utf-8", delete=False
            ) as handle:
                json.dump(
                    {
                        "schema": "harness.loop-step/v1",
                        "policy": policy,
                        "frozen_adapter": "codex-direct",
                        "requested_adapter": requested,
                        "attempts": attempts,
                        "current": {
                            "fingerprint": fingerprint,
                            "evidence_digest": evidence,
                        },
                        "user_input": user_input,
                    },
                    handle,
                )
                path = handle.name
            try:
                result = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "harness",
                        "capability",
                        "loop-step",
                        path,
                        "--adapter",
                        "codex-direct",
                    ],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                )
            finally:
                Path(path).unlink(missing_ok=True)
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            return json.loads(result.stdout)

        current = {"fingerprint": fingerprint, "evidence_digest": evidence}
        self.assertEqual(run(attempts=[])["action"], "continue")
        self.assertEqual(run(attempts=[current])["reason"], "no-progress")
        self.assertEqual(run(attempts=[], user_input=True)["action"], "yield-to-user")
        switched = run(attempts=[], requested="claude-direct")
        self.assertEqual(switched["action"], "stop")
        self.assertEqual(switched["reason"], "adapter-switch-prohibited")

    def test_codex_hook_commands_preserve_stdin_from_a_nested_directory(self) -> None:
        raw_session = "SYNTHETIC_PROCESS_BOUNDARY_SESSION_29"
        config = json.loads(
            (ROOT / ".codex" / "hooks.json").read_text(encoding="utf-8")
        )
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
