from __future__ import annotations

import json
import hashlib
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from harness.evolution import (
    EvolutionError,
    _evolution_contract_name,
    compile_evolution_capability,
    verify_evolution_projection,
)


ROOT = Path(__file__).resolve().parents[2]


def digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=True, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


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
            "PYTHONPATH": str(ROOT),
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


class EvolutionCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        git(self.repo, "init", "-b", "main")
        git(self.repo, "config", "user.name", "Harness Evolution")
        git(self.repo, "config", "user.email", "evolution@example.invalid")
        (self.repo / ".gitignore").write_text(".harness/\n", encoding="utf-8")
        self.codex_home = self.root / "codex-home"
        route = self.codex_home / "skills/find-skills/SKILL.md"
        route.parent.mkdir(parents=True)
        route.write_text("# Synthetic find-skills route\n", encoding="utf-8")
        self.route_digest = hashlib.sha256(route.read_bytes()).hexdigest()
        self.candidate_artifact = self.root / "candidate-SKILL.md"
        self.candidate_artifact.write_text(
            "---\nname: vitest\ndescription: Synthetic pinned candidate.\n---\n",
            encoding="utf-8",
        )
        self.candidate_license = self.root / "candidate-LICENSE.md"
        self.candidate_license.write_text(
            "MIT License\n\nPermission is hereby granted for this synthetic fixture.\n",
            encoding="utf-8",
        )
        self.channel_evidence = self.root / "channel-evidence"
        self.channel_evidence.mkdir()
        (self.repo / "README.md").write_text("seed\n", encoding="utf-8")
        evaluation = self.repo / "evaluation"
        evaluation.mkdir()
        (evaluation / "evaluator.json").write_text(
            json.dumps(
                {
                    "schema": "harness.evolution-evaluator/v1",
                    "id": "independent-evaluator",
                    "required_cases": [
                        "canonical-source",
                        "codex-discovery",
                        "claude-discovery",
                    ],
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        (evaluation / "holdout.json").write_text(
            json.dumps(
                {
                    "schema": "harness.evolution-holdout/v1",
                    "id": "fixed-holdout",
                    "required_cases": ["read-only-agent", "no-agent-tree"],
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        for relative in (".codex/hooks.json", ".claude/settings.json"):
            target = self.repo / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("{}\n", encoding="utf-8")
        git(
            self.repo,
            "add",
            ".gitignore",
            "README.md",
            "evaluation",
            ".codex/hooks.json",
            ".claude/settings.json",
        )
        git(self.repo, "commit", "-m", "seed")

    def harness_at(
        self, repo: Path, *args: str, input_text: str | None = None
    ) -> subprocess.CompletedProcess[str]:
        command = list(args)
        if command and command[0] == "evolution" and "--mode" not in command:
            command.extend(("--mode", "codex-direct"))
        if command and command[0] == "evolution" and "--actor" not in command:
            command.extend(("--actor", "codex"))
        environment = isolated_environment()
        environment["CODEX_HOME"] = str(self.codex_home)
        environment["HARNESS_TEST_CANDIDATE_ARTIFACT"] = str(self.candidate_artifact)
        environment["HARNESS_TEST_CANDIDATE_LICENSE"] = str(self.candidate_license)
        environment["HARNESS_TEST_CHANNEL_EVIDENCE"] = str(self.channel_evidence)
        wrapper = """
import json
import io
import os
import sys
import urllib.request
import urllib.error
from urllib.parse import urlsplit
from pathlib import Path

class Response:
    status = 200
    def __init__(self, request):
        self.url = request.full_url
        parsed = urlsplit(self.url)
        if parsed.hostname == "registry.modelcontextprotocol.io":
            source = str(Path(os.environ["HARNESS_TEST_CHANNEL_EVIDENCE"]) / "registry.json")
        elif parsed.hostname == "registry.npmjs.org":
            source = str(Path(os.environ["HARNESS_TEST_CHANNEL_EVIDENCE"]) / "package.json")
        elif self.url.endswith("/LICENSE.md"):
            source = os.environ["HARNESS_TEST_CANDIDATE_LICENSE"]
        elif self.url.endswith("/README.md"):
            source = str(Path(os.environ["HARNESS_TEST_CHANNEL_EVIDENCE"]) / "official.txt")
        elif (Path(os.environ["HARNESS_TEST_CHANNEL_EVIDENCE"]) / "live-not-found.json").exists():
            source = str(Path(os.environ["HARNESS_TEST_CHANNEL_EVIDENCE"]) / "live-not-found.json")
        else:
            source = os.environ["HARNESS_TEST_CANDIDATE_ARTIFACT"]
        self.data = Path(source).read_bytes()
    def __enter__(self): return self
    def __exit__(self, *_): return False
    def geturl(self): return self.url
    def read(self, _limit): return self.data

class Opener:
    def open(self, request, timeout):
        response = Response(request)
        if urlsplit(request.full_url).hostname == "registry.npmjs.org":
            raise urllib.error.HTTPError(
                request.full_url, 404, "Not Found", {}, io.BytesIO(response.data)
            )
        if (urlsplit(request.full_url).hostname == "raw.githubusercontent.com"
                and request.full_url.endswith("/capability.json")
                and (Path(os.environ["HARNESS_TEST_CHANNEL_EVIDENCE"]) / "live-not-found.json").exists()):
            raise urllib.error.HTTPError(
                request.full_url, 404, "Not Found", {}, io.BytesIO(response.data)
            )
        return response

urllib.request.build_opener = lambda *_: Opener()
from harness.cli import main
raise SystemExit(main())
"""
        return subprocess.run(
            [sys.executable, "-c", wrapper, *command],
            cwd=repo,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            input=input_text,
        )

    def harness(self, *args: str) -> subprocess.CompletedProcess[str]:
        return self.harness_at(self.repo, *args)

    def write_contract(self, repo: Path, task_id: str, owned_paths: list[str]) -> Path:
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
                        "canonical_worktree": str(repo.resolve()),
                        "base_sha": git(repo, "rev-parse", "HEAD"),
                        "branch": git(repo, "branch", "--show-current"),
                        "adapter_switch_policy": "stop-and-report",
                    },
                    "plan": {
                        "objective": f"Exercise {task_id}.",
                        "owned_paths": owned_paths,
                        "acceptance_criteria": [
                            {"id": "done", "description": "The task passes."}
                        ],
                        "verification_plan": [
                            {
                                "id": "check",
                                "command": "inspect bounded output",
                                "required": True,
                            },
                            {
                                "id": "review",
                                "command": "review current diff",
                                "required": True,
                            },
                        ],
                        "repair_policy": {"max_attempts": 2},
                        "stop_conditions": ["adapter-failure", "new-authority"],
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

    def start_direct(self, repo: Path, contract: Path) -> None:
        result = self.harness_at(
            repo, "codex-direct", "start", "--cwd", str(repo), str(contract)
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def accept_direct(self, repo: Path, task_id: str, evidence: str) -> str:
        for command in (
            ("advance", "--to", "verifying"),
            (
                "record-check",
                "--check",
                "check",
                "--status",
                "pass",
                "--source",
                "command",
                "--exit-code",
                "0",
                "--sensitivity",
                "metadata",
                "--digest",
                evidence,
            ),
            (
                "record-check",
                "--check",
                "review",
                "--status",
                "pass",
                "--source",
                "review",
                "--sensitivity",
                "metadata",
                "--digest",
                hashlib.sha256(f"{task_id}-review".encode()).hexdigest(),
            ),
            ("advance", "--to", "reviewing"),
            (
                "judge",
                "--criterion",
                "done",
                "--status",
                "pass",
                "--evidence-digest",
                evidence,
            ),
        ):
            result = self.harness_at(
                repo,
                "codex-direct",
                *command,
                "--cwd",
                str(repo),
                "--task",
                task_id,
            )
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        accepted = self.harness_at(
            repo,
            "codex-direct",
            "accept",
            "--cwd",
            str(repo),
            "--task",
            task_id,
            "--message",
            f"test(harness): accept {task_id}",
        )
        self.assertEqual(accepted.returncode, 0, accepted.stderr or accepted.stdout)
        return json.loads(accepted.stdout)["commit_sha"]

    def assert_acceptance_blocked(
        self, repo: Path, task_id: str, error_fragment: str
    ) -> None:
        for command in (
            ("advance", "--to", "verifying"),
            ("accept",),
            ("commit", "--message", "test commit"),
        ):
            result = self.harness_at(
                repo,
                "codex-direct",
                *command,
                "--cwd",
                str(repo),
                "--task",
                task_id,
            )
            self.assertEqual(result.returncode, 2, result.stdout)
            self.assertIn(error_fragment, json.loads(result.stdout)["error"])

    def accepted_gap_worktree(self) -> tuple[Path, str]:
        envelope: dict[str, object] = {
            "schema": "harness.memory-evidence/v1",
            "source": {"task_id": "gap-source", "commit_sha": "0" * 40},
            "candidates": [
                {
                    "type": "capability-gap",
                    "subject": "harness.fixture-capability",
                    "value": {"need": "safe declarative fixture"},
                    "evidence_kind": "verified-capability-gap",
                    "evidence_digest": "0" * 64,
                    "sensitivity": "metadata",
                    "valid_from": "2026-08-13T00:00:00Z",
                }
            ],
        }
        draft = self.root / "gap-draft.json"
        draft.write_text(json.dumps(envelope), encoding="utf-8")
        digest_result = self.harness(
            "memory", "digest", str(draft), "--cwd", str(self.repo)
        )
        self.assertEqual(digest_result.returncode, 0, digest_result.stdout)
        gap_evidence = json.loads(digest_result.stdout)["evidence_digest"]
        envelope["candidates"][0]["evidence_digest"] = gap_evidence

        source_contract = self.write_contract(
            self.repo, "gap-source", ["accepted-gap.json"]
        )
        self.start_direct(self.repo, source_contract)
        (self.repo / "accepted-gap.json").write_text(
            json.dumps(envelope, sort_keys=True) + "\n", encoding="utf-8"
        )
        source_commit = self.accept_direct(self.repo, "gap-source", gap_evidence)
        envelope["source"]["commit_sha"] = source_commit

        memory_contract = self.write_contract(
            self.repo,
            "gap-memory",
            [
                "docs/agent-memory/typed-memory.json",
                "docs/agent-memory/current-memory.json",
            ],
        )
        self.start_direct(self.repo, memory_contract)
        accepted = self.root / "accepted-gap.json"
        accepted.write_text(json.dumps(envelope), encoding="utf-8")
        projected = self.harness(
            "memory",
            "project",
            str(accepted),
            "--cwd",
            str(self.repo),
            "--task",
            "gap-memory",
        )
        self.assertEqual(projected.returncode, 0, projected.stdout)
        self.accept_direct(
            self.repo, "gap-memory", hashlib.sha256(b"gap-memory").hexdigest()
        )

        startup = self.harness("memory", "startup", "--cwd", str(self.repo))
        gap_id = json.loads(startup.stdout)["records"][0]["record_id"]
        linked = self.root / "evolution-worktree"
        git(self.repo, "worktree", "add", "-b", "evolution", str(linked), "HEAD")
        return linked, gap_id

    def request(self, **overrides: object) -> Path:
        value: dict[str, object] = {
            "schema": "harness.evolution-request/v1",
            "gap_id": f"mem-{'0' * 64}",
            "capability_name": "safe-build-fixture",
            "evaluator": {
                "path": "evaluation/evaluator.json",
                "digest": "1" * 64,
            },
            "holdout": {
                "path": "evaluation/holdout.json",
                "digest": "2" * 64,
            },
            "rollback": "git-head-snapshot",
        }
        value.update(overrides)
        path = self.root / "evolution-request.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def search_value(self, decision: str) -> dict[str, object]:
        artifact = self.candidate_artifact.read_bytes()
        license_bytes = self.candidate_license.read_bytes()
        artifact_digest = hashlib.sha256(artifact).hexdigest()
        license_digest = hashlib.sha256(license_bytes).hexdigest()
        candidate = {
            "id": "antfu-skills-vitest",
            "canonical_source": "https://github.com/antfu/skills",
            "immutable_revision": "a74f281a27dadc02397bc1a174b0f2c97531b6ae",
            "artifact_path": "skills/vitest/SKILL.md",
            "artifact_digest": artifact_digest,
            "license": "MIT",
            "license_path": "LICENSE.md",
            "license_digest": license_digest,
            "invocation": {
                "mode": "model",
                "disable_model_invocation": False,
                "allow_implicit_invocation": True,
                "metadata": {},
                "metadata_digest": digest({}),
            },
            "permissions": ["read-repository"],
            "network": "none",
            "data": "repository-local-metadata",
            "compatibility": {
                "hosts": ["codex", "claude"],
                "status": "unverified",
                "evidence_digest": "4" * 64,
            },
            "smoke": {"status": "not-run", "evidence_digest": None},
            "rollback": {
                "scope": "repository-local",
                "method": "git-head-snapshot",
                "reversible": True,
            },
            "manifest": {
                "files": [
                    {
                        "path": "skills/vitest/SKILL.md",
                        "digest": artifact_digest,
                        "bytes": len(artifact),
                        "mode": "100644",
                    },
                    {
                        "path": "LICENSE.md",
                        "digest": license_digest,
                        "bytes": len(license_bytes),
                        "mode": "100644",
                    },
                ],
                "total_bytes": len(artifact) + len(license_bytes),
                "dependencies": [],
                "scripts": [],
                "resources": [],
                "executables": False,
                "symlinks": False,
                "submodules": False,
            },
            "effects": {
                "credentials": False,
                "elevation": False,
                "daemon": False,
                "open_port": False,
                "global_policy": False,
            },
            "installed": {
                "artifact_digest": "3dcdc45fba7d7665d22fc4efc5c6c67efc364c2754563eff18f806746ea06375",
                "provenance": "unknown",
            },
        }
        return {
            "schema": "harness.evolution-search/v1",
            "query": "vitest testing capability",
            "installed_catalog": {
                "host": "codex",
                "route": "find-skills",
                "route_digest": self.route_digest,
                "status": "available",
                "cli": "absent",
            },
            "sources_consulted": [
                {
                    key: candidate[key]
                    for key in (
                        "canonical_source",
                        "immutable_revision",
                        "artifact_path",
                        "artifact_digest",
                        "license_path",
                        "license_digest",
                    )
                }
                | {"result": "candidate"}
            ],
            "candidates": [candidate],
            "decision": decision,
            "selected_candidate": "antfu-skills-vitest",
            "reason_code": (
                "no-suitable-candidate"
                if decision == "build"
                else "installed-provenance-mismatch"
            ),
        }

    def surface_search_value(
        self,
        source: dict[str, object],
        *,
        decision: str = "adapt",
        effects: dict[str, bool] | None = None,
    ) -> dict[str, object]:
        artifact = (
            json.dumps(source, sort_keys=True, separators=(",", ":")) + "\n"
        ).encode()
        self.candidate_artifact.write_bytes(artifact)
        artifact_digest = hashlib.sha256(artifact).hexdigest()
        search = self.search_value(decision)
        search["schema"] = "harness.evolution-search/v2"
        search["channels"] = [
            "official",
            "registry",
            "package-manager",
            "live-github",
        ]
        candidate = search["candidates"][0]
        old_path = candidate["artifact_path"]
        candidate.update(
            {
                "artifact_format": "canonical-json",
                "artifact_path": "capability.json",
                "artifact_digest": artifact_digest,
                "surface": source["surface"],
                "invocation": source["skill"]["invocation"],
                "install": {
                    "scope": "repository-local",
                    "method": "verified-copy",
                    "uninstall": "git-head-snapshot",
                },
                "package": {
                    "name": "@modelcontextprotocol/inspector",
                    "version": "2.2.0",
                },
            }
        )
        candidate["compatibility"] = {
            "hosts": [
                "codex-direct",
                "claude-direct",
                "codex-paseo-claude",
            ],
            "status": "unverified",
            "evidence_digest": "4" * 64,
        }
        candidate["smoke"] = {"status": "not-run", "evidence_digest": None}
        candidate["installed"] = {
            "artifact_digest": "0" * 64,
            "provenance": "not-installed",
        }
        candidate["effects"].update(
            {
                "global_mutation": False,
                "ssh": False,
                "publish": False,
                **(effects or {}),
            }
        )
        manifest_item = next(
            item for item in candidate["manifest"]["files"] if item["path"] == old_path
        )
        manifest_item.update(
            {
                "path": "capability.json",
                "digest": artifact_digest,
                "bytes": len(artifact),
            }
        )
        candidate["manifest"]["total_bytes"] = sum(
            item["bytes"] for item in candidate["manifest"]["files"]
        )
        source_record = search["sources_consulted"][0]
        source_record.update(
            {
                "artifact_path": "capability.json",
                "artifact_digest": artifact_digest,
                "channel": "live-github",
            }
        )
        search["sources_consulted"] = [
            source_record,
            *(
                {**source_record, "channel": channel, "result": "no-match"}
                for channel in ("official", "registry", "package-manager")
            ),
        ]
        repository = candidate["canonical_source"].removeprefix("https://github.com/")
        evidence_urls = {
            "official": (
                f"https://raw.githubusercontent.com/{repository}/"
                f"{candidate['immutable_revision']}/README.md"
            ),
            "registry": (
                "https://registry.modelcontextprotocol.io/v0/servers"
                f"?search={candidate['id']}"
            ),
            "package-manager": (
                "https://registry.npmjs.org/"
                "%40modelcontextprotocol%2Finspector/2.2.0"
            ),
            "live-github": (
                f"https://raw.githubusercontent.com/{repository}/"
                f"{candidate['immutable_revision']}/capability.json"
            ),
        }
        evidence = {
            "official": b"# Synthetic upstream catalog\nNo matching capability.\n",
            "registry": b'{"servers":[]}\n',
            "package-manager": b'{"error":"Not found"}\n',
            "live-github": artifact,
        }
        (self.channel_evidence / "official.txt").write_bytes(evidence["official"])
        (self.channel_evidence / "registry.json").write_bytes(evidence["registry"])
        (self.channel_evidence / "package.json").write_bytes(
            evidence["package-manager"]
        )
        for item in search["sources_consulted"]:
            raw = evidence[item["channel"]]
            item.update(
                {
                    "evidence_url": evidence_urls[item["channel"]],
                    "evidence_digest": hashlib.sha256(raw).hexdigest(),
                    "evidence_bytes": len(raw),
                }
            )
        return search

    def surface_source(self, kind: str) -> dict[str, object]:
        source = json.loads(
            (ROOT / "harness/fixtures/evolution-build-capability.json").read_text()
        )
        source["schema"] = "harness.evolution-capability/v2"
        source["license"] = "MIT"
        source["adapted_from"] = {
            "source": "https://github.com/antfu/skills",
            "revision": "a74f281a27dadc02397bc1a174b0f2c97531b6ae",
        }
        source["trust"]["source"] = "pinned-adaptation"
        source["surface"] = {
            "kind": kind,
            "adapters": [
                "codex-direct",
                "claude-direct",
                "codex-paseo-claude",
            ],
            "external_system": kind == "mcp",
            "entrypoint": "harness-shared-cli",
            "hook": None,
            "loop": None,
        }
        return source

    def start_evolution_run(self, repo: Path, task_id: str, gap_id: str) -> None:
        contract = self.write_contract(repo, task_id, self.evolution_owned(task_id))
        self.start_direct(repo, contract)
        evaluator = repo / "evaluation/evaluator.json"
        holdout = repo / "evaluation/holdout.json"
        request = self.request(
            gap_id=gap_id,
            evaluator={
                "path": "evaluation/evaluator.json",
                "digest": hashlib.sha256(evaluator.read_bytes()).hexdigest(),
            },
            holdout={
                "path": "evaluation/holdout.json",
                "digest": hashlib.sha256(holdout.read_bytes()).hexdigest(),
            },
        )
        started = self.harness_at(
            repo,
            "evolution",
            "start",
            str(request),
            "--cwd",
            str(repo),
            "--task",
            task_id,
        )
        self.assertEqual(started.returncode, 0, started.stdout)

    def evolution_paths(
        self, task_id: str, name: str = "safe-build-fixture"
    ) -> dict[str, str]:
        task_key = hashlib.sha256(task_id.encode("utf-8")).hexdigest()[:12]
        package = f"harness/capability-packages/{name}"
        return {
            "package": package,
            "canonical": f"{package}/canonical.json",
            "codex": f"{package}/codex",
            "claude": f"{package}/claude",
            "codex_skill": f".agents/skills/{name}",
            "claude_skill": f".claude/skills/{name}",
            "codex_agent": f".codex/agents/{name}.toml",
            "claude_agent": f".claude/agents/{name}.md",
            "report": f"docs/agent-memory/evolution-reports/{name}-{task_key}.json",
        }

    def evolution_owned(
        self, task_id: str, name: str = "safe-build-fixture"
    ) -> list[str]:
        paths = self.evolution_paths(task_id, name)
        return sorted(
            [
                f"{paths['package']}/",
                f"{paths['codex_skill']}/",
                f"{paths['claude_skill']}/",
                paths["codex_agent"],
                paths["claude_agent"],
                paths["report"],
            ]
        )

    def test_mcp_initialize_negotiates_supported_protocol_versions(self) -> None:
        from harness.evolution import mcp_surface_message

        canonical = {
            "name": "safe-build-fixture",
            "version": "1.0.0",
            "surface": {"kind": "mcp"},
        }
        versions = (
            "2025-11-25",
            "2025-06-18",
            "2025-03-26",
            "2024-11-05",
            "2024-10-07",
            "unsupported-version",
        )
        with patch(
            "harness.evolution.discover_surface_capabilities",
            return_value={"capabilities": [{"name": canonical["name"]}]},
        ), patch("harness.evolution._surface_canonical", return_value=canonical):
            for requested in versions:
                with self.subTest(requested=requested):
                    response = mcp_surface_message(
                        object(),
                        name=canonical["name"],
                        adapter="codex-direct",
                        value={
                            "jsonrpc": "2.0",
                            "id": 1,
                            "method": "initialize",
                            "params": {
                                "protocolVersion": requested,
                                "capabilities": {},
                                "clientInfo": {"name": "test", "version": "1"},
                            },
                        },
                    )
                    self.assertIsNotNone(response)
                    self.assertEqual(
                        response["result"]["protocolVersion"],
                        requested
                        if requested != "unsupported-version"
                        else "2025-11-25",
                    )

    def test_mcp_notifications_accept_bounded_metadata(self) -> None:
        from harness.evolution import mcp_surface_message

        canonical = {
            "name": "safe-build-fixture",
            "version": "1.0.0",
            "surface": {"kind": "mcp"},
        }
        with patch(
            "harness.evolution.discover_surface_capabilities",
            return_value={"capabilities": [{"name": canonical["name"]}]},
        ), patch("harness.evolution._surface_canonical", return_value=canonical):
            self.assertIsNone(
                mcp_surface_message(
                    object(),
                    name=canonical["name"],
                    adapter="codex-direct",
                    value={
                        "jsonrpc": "2.0",
                        "method": "notifications/cancelled",
                        "params": {"requestId": 7, "reason": "user cancelled"},
                    },
                )
            )
            self.assertIsNone(
                mcp_surface_message(
                    object(),
                    name=canonical["name"],
                    adapter="codex-direct",
                    value={
                        "jsonrpc": "2.0",
                        "method": "notifications/initialized",
                        "params": {"_meta": {"trace": "bounded"}},
                    },
                )
            )
            for meta in ("invalid", {"trace": "x" * 4096}):
                with self.assertRaisesRegex(
                    EvolutionError, "notification (params|metadata)"
                ):
                    mcp_surface_message(
                        object(),
                        name=canonical["name"],
                        adapter="codex-direct",
                        value={
                            "jsonrpc": "2.0",
                            "method": "notifications/initialized",
                            "params": {"_meta": meta},
                        },
                    )

    def test_mcp_tool_call_accepts_optional_arguments_and_progress_meta(self) -> None:
        from harness.evolution import mcp_surface_message

        canonical = {
            "name": "safe-build-fixture",
            "version": "1.0.0",
            "surface": {"kind": "mcp"},
            "skill": {"interface": {"operations": ["inspect"]}},
        }
        with patch(
            "harness.evolution.discover_surface_capabilities",
            return_value={"capabilities": [{"name": canonical["name"]}]},
        ), patch(
            "harness.evolution._surface_canonical", return_value=canonical
        ), patch(
            "harness.evolution._surface_operation_result",
            return_value={"operation": "inspect"},
        ):
            for request_id, params in (
                (1, {"name": "inspect"}),
                (
                    2,
                    {
                        "name": "inspect",
                        "arguments": {},
                        "_meta": {"progressToken": "progress-1"},
                    },
                ),
            ):
                response = mcp_surface_message(
                    object(),
                    name=canonical["name"],
                    adapter="codex-direct",
                    value={
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "method": "tools/call",
                        "params": params,
                    },
                )
                self.assertEqual(response["id"], request_id)
                self.assertFalse(response["result"]["isError"])
            for meta in (
                {"progressToken": []},
                {"progressToken": "x" * 129},
            ):
                with self.assertRaisesRegex(EvolutionError, "progress token"):
                    mcp_surface_message(
                        object(),
                        name=canonical["name"],
                        adapter="codex-direct",
                        value={
                            "jsonrpc": "2.0",
                            "id": 3,
                            "method": "tools/call",
                            "params": {"name": "inspect", "_meta": meta},
                        },
                    )

    def test_mcp_requests_accept_bounded_base_metadata(self) -> None:
        from harness.evolution import mcp_surface_message

        canonical = {
            "name": "safe-build-fixture",
            "version": "1.0.0",
            "surface": {"kind": "mcp"},
            "skill": {"interface": {"operations": ["inspect"]}},
        }
        with patch(
            "harness.evolution.discover_surface_capabilities",
            return_value={"capabilities": [{"name": canonical["name"]}]},
        ), patch("harness.evolution._surface_canonical", return_value=canonical):
            requests = (
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-11-25",
                        "capabilities": {},
                        "clientInfo": {"name": "test", "version": "1"},
                        "_meta": {
                            "io.modelcontextprotocol/related-task": {
                                "taskId": "task-1"
                            }
                        },
                    },
                },
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "ping",
                    "params": {"_meta": {"progressToken": "ping-1"}},
                },
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/list",
                    "params": {
                        "cursor": "opaque-cursor",
                        "_meta": {"extension.trace": "bounded"},
                    },
                },
            )
            for request in requests:
                with self.subTest(method=request["method"]):
                    response = mcp_surface_message(
                        object(),
                        name=canonical["name"],
                        adapter="codex-direct",
                        value=request,
                    )
                    self.assertEqual(response["id"], request["id"])
            with self.assertRaisesRegex(EvolutionError, "related task id"):
                mcp_surface_message(
                    object(),
                    name=canonical["name"],
                    adapter="codex-direct",
                    value={
                        "jsonrpc": "2.0",
                        "id": 4,
                        "method": "ping",
                        "params": {
                            "_meta": {
                                "io.modelcontextprotocol/related-task": {"taskId": []}
                            }
                        },
                    },
                )
            for cursor in ([], "x" * 2049, "bad\ncursor"):
                with self.subTest(cursor=cursor), self.assertRaisesRegex(
                    EvolutionError, "cursor"
                ):
                    mcp_surface_message(
                        object(),
                        name=canonical["name"],
                        adapter="codex-direct",
                        value={
                            "jsonrpc": "2.0",
                            "id": 5,
                            "method": "tools/list",
                            "params": {"cursor": cursor},
                        },
                    )

    def test_start_rejects_a_gap_that_is_not_in_accepted_current_memory(self) -> None:
        request = self.request()

        result = self.harness(
            "evolution",
            "start",
            str(request),
            "--cwd",
            str(self.repo),
            "--task",
            "evolution-task",
        )

        self.assertEqual(result.returncode, 2)
        self.assertEqual(
            json.loads(result.stdout),
            {
                "schema": "harness.error/v1",
                "error": "accepted current capability gap is unavailable",
            },
        )

    def test_start_rejects_a_forged_acceptance_receipt(self) -> None:
        linked, gap_id = self.accepted_gap_worktree()
        store_path = linked / "docs/agent-memory/typed-memory.json"
        projection_path = linked / "docs/agent-memory/current-memory.json"
        store = json.loads(store_path.read_text(encoding="utf-8"))
        receipt = store["records"][0]["provenance"][0]["acceptance_receipt"]
        receipt["diff_digest"] = "f" * 64
        store_bytes = (
            json.dumps(store, ensure_ascii=True, sort_keys=True, indent=2) + "\n"
        ).encode("utf-8")
        store_path.write_bytes(store_bytes)
        projection = json.loads(projection_path.read_text(encoding="utf-8"))
        projection["records"] = json.loads(json.dumps(store["records"]))
        projection["store_digest"] = hashlib.sha256(store_bytes).hexdigest()
        projection_path.write_bytes(
            (
                json.dumps(projection, ensure_ascii=True, sort_keys=True, indent=2)
                + "\n"
            ).encode("utf-8")
        )
        git(linked, "add", "docs/agent-memory")
        git(linked, "commit", "-m", "forge an untrusted receipt")

        contract = self.write_contract(
            linked, "forged-receipt-task", self.evolution_owned("forged-receipt-task")
        )
        self.start_direct(linked, contract)
        evaluator = linked / "evaluation/evaluator.json"
        holdout = linked / "evaluation/holdout.json"
        request = self.request(
            gap_id=gap_id,
            evaluator={
                "path": "evaluation/evaluator.json",
                "digest": hashlib.sha256(evaluator.read_bytes()).hexdigest(),
            },
            holdout={
                "path": "evaluation/holdout.json",
                "digest": hashlib.sha256(holdout.read_bytes()).hexdigest(),
            },
        )
        result = self.harness_at(
            linked,
            "evolution",
            "start",
            str(request),
            "--cwd",
            str(linked),
            "--task",
            "forged-receipt-task",
        )
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn(
            "accepted current capability gap", json.loads(result.stdout)["error"]
        )

    def test_request_derives_safe_paths_and_rejects_windows_aliases(self) -> None:
        for capability_name in (
            "../RULES.md",
            "RULES.md.",
            "EVOLUT~1",
            "CON",
            "name:stream",
        ):
            with self.subTest(capability_name=capability_name):
                result = self.harness(
                    "evolution",
                    "start",
                    str(self.request(capability_name=capability_name)),
                    "--cwd",
                    str(self.repo),
                    "--task",
                    "evolution-task",
                )
                self.assertEqual(result.returncode, 2)
                self.assertIn("capability name", json.loads(result.stdout)["error"])

        request = json.loads(self.request().read_text(encoding="utf-8"))
        request["report_path"] = "harness/cli.py"
        injected = self.root / "injected-path.json"
        injected.write_text(json.dumps(request), encoding="utf-8")
        result = self.harness(
            "evolution",
            "start",
            str(injected),
            "--cwd",
            str(self.repo),
            "--task",
            "evolution-task",
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("request is invalid", json.loads(result.stdout)["error"])

    def test_search_rejects_unpinned_unknown_or_raw_install_candidates(self) -> None:
        from harness.evolution import record_search
        from harness.context import discover_worktree

        search = self.search_value("deferred")
        candidate = search["candidates"][0]
        candidate["immutable_revision"] = "main"
        with self.assertRaisesRegex(EvolutionError, "immutable"):
            record_search(
                discover_worktree(self.repo),
                search,
                task_id="missing",
                expected_mode="codex-direct",
                actor="codex",
            )
        candidate["immutable_revision"] = "a" * 40
        candidate["license"] = "UNKNOWN"
        with self.assertRaisesRegex(EvolutionError, "license"):
            record_search(
                discover_worktree(self.repo),
                search,
                task_id="missing",
                expected_mode="codex-direct",
                actor="codex",
            )
        candidate["license"] = "MIT"
        candidate["install_command"] = "npx skills add owner/repo"
        with self.assertRaisesRegex(EvolutionError, "candidate"):
            record_search(
                discover_worktree(self.repo),
                search,
                task_id="missing",
                expected_mode="codex-direct",
                actor="codex",
            )
        candidate.pop("install_command")
        search["sources_consulted"] = []
        with self.assertRaisesRegex(EvolutionError, "official or live GitHub"):
            record_search(
                discover_worktree(self.repo),
                search,
                task_id="missing",
                expected_mode="codex-direct",
                actor="codex",
            )
        search = self.search_value("deferred")
        search["candidates"][0]["artifact_digest"] = "9" * 64
        with self.assertRaisesRegex(EvolutionError, "manifest"):
            record_search(
                discover_worktree(self.repo),
                search,
                task_id="missing",
                expected_mode="codex-direct",
                actor="codex",
            )

    def test_start_binds_an_accepted_gap_to_one_active_independent_writer(self) -> None:
        linked, gap_id = self.accepted_gap_worktree()
        contract = self.write_contract(
            linked,
            "evolution-task",
            self.evolution_owned("evolution-task"),
        )
        self.start_direct(linked, contract)
        evaluator = linked / "evaluation/evaluator.json"
        holdout = linked / "evaluation/holdout.json"
        request = self.request(
            gap_id=gap_id,
            evaluator={
                "path": "evaluation/evaluator.json",
                "digest": hashlib.sha256(evaluator.read_bytes()).hexdigest(),
            },
            holdout={
                "path": "evaluation/holdout.json",
                "digest": hashlib.sha256(holdout.read_bytes()).hexdigest(),
            },
        )

        exclude = self.repo / ".git/info/exclude"
        exclude.write_text(
            exclude.read_text(encoding="utf-8")
            + "\nharness/capability-packages/safe-build-fixture/codex/ignored.env\n",
            encoding="utf-8",
        )
        ignored = (
            linked / "harness/capability-packages/safe-build-fixture/codex/ignored.env"
        )
        ignored.parent.mkdir(parents=True, exist_ok=True)
        ignored.write_text("user data\n", encoding="utf-8")
        refused_ignored = self.harness_at(
            linked,
            "evolution",
            "start",
            str(request),
            "--cwd",
            str(linked),
            "--task",
            "evolution-task",
        )
        self.assertEqual(refused_ignored.returncode, 2)
        self.assertIn("ignored", json.loads(refused_ignored.stdout)["error"])
        ignored.unlink()

        started = self.harness_at(
            linked,
            "evolution",
            "start",
            str(request),
            "--cwd",
            str(linked),
            "--task",
            "evolution-task",
        )
        duplicate = self.harness_at(
            linked,
            "evolution",
            "start",
            str(request),
            "--cwd",
            str(linked),
            "--task",
            "evolution-task",
        )

        self.assertEqual(started.returncode, 0, started.stderr or started.stdout)
        self.assertEqual(json.loads(started.stdout)["state"], "search-required")
        self.assertEqual(duplicate.returncode, 2)
        self.assertEqual(
            json.loads(duplicate.stdout)["error"],
            "Evolution Run already exists for this task",
        )
        self.assert_acceptance_blocked(linked, "evolution-task", "not ready")
        for suffix, managed_root in (
            ("lower", ".agents/skills/plain-capability/"),
            ("case", ".AGENTS/skills/plain-capability/"),
        ):
            task_id = f"plain-capability-{suffix}"
            with self.assertRaisesRegex(EvolutionError, "owned paths"):
                _evolution_contract_name(
                    task_id, {"plan": {"owned_paths": [managed_root]}}
                )

        search = self.root / "search.json"
        search.write_text(json.dumps(self.search_value("deferred")), encoding="utf-8")
        wrong_mode = self.harness_at(
            linked,
            "evolution",
            "search",
            str(search),
            "--cwd",
            str(linked),
            "--task",
            "evolution-task",
            "--mode",
            "claude-direct",
        )
        self.assertEqual(wrong_mode.returncode, 2)
        self.assertIn("mode", json.loads(wrong_mode.stdout)["error"].lower())
        evolution_state = next(
            (linked / ".harness/runtime").glob("*/tasks/*/evolution.json")
        )
        frozen_state = evolution_state.read_bytes()
        evolution_state.unlink()
        self.assert_acceptance_blocked(
            linked, "evolution-task", "required Evolution state is missing"
        )
        evolution_state.write_bytes(frozen_state)
        wrong_actor = self.harness_at(
            linked,
            "evolution",
            "search",
            str(search),
            "--cwd",
            str(linked),
            "--task",
            "evolution-task",
            "--actor",
            "claude",
        )
        self.assertEqual(wrong_actor.returncode, 2)
        self.assertIn("writer lease", json.loads(wrong_actor.stdout)["error"])
        tampered_state = json.loads(frozen_state)
        tampered_state["outputs"]["codex"] = "README.md"
        evolution_state.write_text(json.dumps(tampered_state), encoding="utf-8")
        tampered = self.harness_at(
            linked,
            "evolution",
            "search",
            str(search),
            "--cwd",
            str(linked),
            "--task",
            "evolution-task",
        )
        self.assertEqual(tampered.returncode, 2)
        self.assertIn("state is invalid", json.loads(tampered.stdout)["error"])
        evolution_state.write_bytes(frozen_state)
        searched = self.harness_at(
            linked,
            "evolution",
            "search",
            str(search),
            "--cwd",
            str(linked),
            "--task",
            "evolution-task",
        )

        self.assertEqual(searched.returncode, 0, searched.stderr or searched.stdout)
        self.assertEqual(json.loads(searched.stdout)["state"], "deferred")
        paths = self.evolution_paths("evolution-task")
        package = linked / paths["package"]
        self.assertEqual(
            (
                [item for item in package.rglob("*") if item.is_file()]
                if package.exists()
                else []
            ),
            [],
        )
        report = json.loads((linked / paths["report"]).read_text())
        self.assertEqual(report["outcome"], "deferred")
        self.assertEqual(report["strategy"], "Search")
        search_base = git(linked, "rev-parse", "HEAD")
        search_commit = self.accept_direct(
            linked,
            "evolution-task",
            hashlib.sha256(b"search-pilot-evidence").hexdigest(),
        )
        self.assertEqual(
            git(linked, "rev-list", "--count", f"{search_base}..HEAD"), "1"
        )
        self.assertEqual(git(linked, "rev-parse", "HEAD"), search_commit)
        self.assertEqual(git(linked, "remote"), "")

        authorization = self.root / "authorization-worktree"
        git(
            self.repo,
            "worktree",
            "add",
            "-b",
            "authorization",
            str(authorization),
            "HEAD",
        )
        auth_contract = self.write_contract(
            authorization,
            "authorization-task",
            self.evolution_owned("authorization-task"),
        )
        self.start_direct(authorization, auth_contract)
        auth_request = self.request(
            gap_id=gap_id,
            evaluator={
                "path": "evaluation/evaluator.json",
                "digest": hashlib.sha256(
                    (authorization / "evaluation/evaluator.json").read_bytes()
                ).hexdigest(),
            },
            holdout={
                "path": "evaluation/holdout.json",
                "digest": hashlib.sha256(
                    (authorization / "evaluation/holdout.json").read_bytes()
                ).hexdigest(),
            },
        )
        self.assertEqual(
            self.harness_at(
                authorization,
                "evolution",
                "start",
                str(auth_request),
                "--cwd",
                str(authorization),
                "--task",
                "authorization-task",
            ).returncode,
            0,
        )
        adapt_search = self.root / "adapt-search.json"
        unsafe_adapt = self.search_value("adapt")
        unsafe_candidate = unsafe_adapt["candidates"][0]
        unsafe_candidate["compatibility"]["status"] = "pass"
        unsafe_candidate["smoke"] = {
            "status": "pass",
            "evidence_digest": "8" * 64,
        }
        adapt_search.write_text(json.dumps(unsafe_adapt), encoding="utf-8")
        first_request = self.harness_at(
            authorization,
            "evolution",
            "search",
            str(adapt_search),
            "--cwd",
            str(authorization),
            "--task",
            "authorization-task",
        )
        repeated_request = self.harness_at(
            authorization,
            "evolution",
            "search",
            str(adapt_search),
            "--cwd",
            str(authorization),
            "--task",
            "authorization-task",
        )
        self.assertEqual(first_request.returncode, 0, first_request.stdout)
        self.assertEqual(repeated_request.returncode, 0, repeated_request.stdout)
        self.assertTrue(json.loads(first_request.stdout)["requires_user"])
        self.assertEqual(first_request.stdout, repeated_request.stdout)
        authorization_payload = json.loads(first_request.stdout)["authorization"]
        self.assertEqual(
            authorization_payload["alternatives"],
            ["defer", "build-repository-local"],
        )
        self.assertIn(
            "installed-provenance-not-pinned", authorization_payload["blocks"]
        )
        self.assertIn("installed-artifact-mismatch", authorization_payload["blocks"])
        self.assertFalse(
            (authorization / "harness/capability-packages/safe-build-fixture").exists()
        )
        self.assert_acceptance_blocked(authorization, "authorization-task", "not ready")
        forged_resolution = self.harness_at(
            authorization,
            "evolution",
            "resolve",
            str(adapt_search),
            "--cwd",
            str(authorization),
            "--task",
            "authorization-task",
        )
        self.assertNotEqual(forged_resolution.returncode, 0)
        self.assertIn("invalid choice", forged_resolution.stderr)
        self.assertFalse(
            (authorization / "harness/capability-packages/safe-build-fixture").exists()
        )

    def test_build_fixture_compiles_deterministic_skill_and_agent_projections(
        self,
    ) -> None:
        source = json.loads(
            (ROOT / "harness/fixtures/evolution-build-capability.json").read_text()
        )

        packages = {
            host: compile_evolution_capability(source, host)
            for host in ("codex", "claude")
        }

        self.assertEqual(
            set(packages["codex"]),
            {
                "skills/safe-build-fixture/SKILL.md",
                "skills/safe-build-fixture/interface.json",
                "skills/safe-build-fixture/governance.json",
                "skills/safe-build-fixture/trust.json",
                "skills/safe-build-fixture/packaging.json",
                "skills/safe-build-fixture/evaluation.json",
                "skills/safe-build-fixture/agents/openai.yaml",
                "agents/safe-build-fixture.toml",
                "manifest.json",
            },
        )
        self.assertEqual(
            set(packages["claude"]),
            {
                "skills/safe-build-fixture/SKILL.md",
                "skills/safe-build-fixture/interface.json",
                "skills/safe-build-fixture/governance.json",
                "skills/safe-build-fixture/trust.json",
                "skills/safe-build-fixture/packaging.json",
                "skills/safe-build-fixture/evaluation.json",
                "agents/safe-build-fixture.md",
                "manifest.json",
            },
        )
        for host, package in packages.items():
            skill = package["skills/safe-build-fixture/SKILL.md"]
            manifest = json.loads(package["manifest.json"])
            self.assertIn("name: safe-build-fixture", skill)
            if host == "codex":
                self.assertNotIn("disable-model-invocation: true", skill)
            else:
                self.assertIn("disable-model-invocation: true", skill)
            self.assertEqual(manifest["host"], host)
            self.assertEqual(manifest["source_digest"], manifest["canonical_digest"])
            self.assertLessEqual(manifest["total_bytes"], 65536)
        codex_agent = packages["codex"]["agents/safe-build-fixture.toml"]
        self.assertIn('sandbox_mode = "read-only"', codex_agent)
        self.assertIn("[agents]\nenabled = false", codex_agent)
        self.assertNotIn("max_children", codex_agent)
        self.assertNotIn("writer_lease_required", codex_agent)
        self.assertIn(
            "tools: Read, Grep, Glob",
            packages["claude"]["agents/safe-build-fixture.md"],
        )
        self.assertEqual(
            packages["codex"]["skills/safe-build-fixture/interface.json"],
            packages["claude"]["skills/safe-build-fixture/interface.json"],
        )
        self.assertEqual(
            packages["codex"]["skills/safe-build-fixture/packaging.json"],
            packages["claude"]["skills/safe-build-fixture/packaging.json"],
        )
        self.assertEqual(
            packages["codex"]["skills/safe-build-fixture/evaluation.json"],
            packages["claude"]["skills/safe-build-fixture/evaluation.json"],
        )

        for host, package in packages.items():
            projection = self.root / f"{host}-projection"
            for relative, content in package.items():
                target = projection / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content.encode("utf-8"))
            self.assertEqual(
                verify_evolution_projection(source, host, projection)["status"],
                "pass",
            )
        codex_projection = self.root / "codex-projection"
        (codex_projection / "agents/safe-build-fixture.toml").write_text(
            "not = [valid", encoding="utf-8"
        )
        with self.assertRaisesRegex(EvolutionError, "projection drift|discovery"):
            verify_evolution_projection(source, "codex", codex_projection)

    def test_zero_candidate_search_can_build_repository_local_capability(self) -> None:
        repo, gap_id = self.accepted_gap_worktree()
        task_id = "zero-candidate-build"
        self.start_evolution_run(repo, task_id, gap_id)
        value = self.search_value("build")
        value["candidates"] = []
        value["selected_candidate"] = None
        search = self.root / f"{task_id}-search.json"
        search.write_text(json.dumps(value), encoding="utf-8")

        inconsistent = self.harness_at(
            repo,
            "evolution",
            "search",
            str(search),
            "--cwd",
            str(repo),
            "--task",
            task_id,
        )

        self.assertNotEqual(inconsistent.returncode, 0, inconsistent.stdout)

        value["sources_consulted"][0]["result"] = "no-match"
        search.write_text(json.dumps(value), encoding="utf-8")

        searched = self.harness_at(
            repo,
            "evolution",
            "search",
            str(search),
            "--cwd",
            str(repo),
            "--task",
            task_id,
        )

        self.assertEqual(searched.returncode, 0, searched.stdout)
        self.assertEqual(json.loads(searched.stdout)["state"], "build-ready")
        self.assertIsNone(json.loads(searched.stdout)["candidate_id"])

        built = self.harness_at(
            repo,
            "evolution",
            "build",
            str(ROOT / "harness/fixtures/evolution-build-capability.json"),
            "--cwd",
            str(repo),
            "--task",
            task_id,
        )

        self.assertEqual(built.returncode, 0, built.stdout)
        self.assertEqual(json.loads(built.stdout)["state"], "evaluating")

        evaluation = self.root / f"{task_id}-evaluation.json"
        evaluation.write_text(
            json.dumps(
                {
                    "schema": "harness.evolution-evaluation-request/v1",
                    "candidate_digest": json.loads(built.stdout)["candidate_digest"],
                }
            ),
            encoding="utf-8",
        )
        evaluated = self.harness_at(
            repo,
            "evolution",
            "evaluate",
            str(evaluation),
            "--cwd",
            str(repo),
            "--task",
            task_id,
        )

        self.assertEqual(evaluated.returncode, 0, evaluated.stdout)
        self.assertEqual(json.loads(evaluated.stdout)["state"], "promotion-ready")
        base = git(repo, "rev-parse", "HEAD")
        commit = self.accept_direct(
            repo, task_id, hashlib.sha256(task_id.encode()).hexdigest()
        )
        self.assertEqual(git(repo, "rev-list", "--count", f"{base}..{commit}"), "1")

    def test_zero_candidate_surface_search_verifies_no_match_channels(self) -> None:
        repo, gap_id = self.accepted_gap_worktree()
        task_id = "zero-candidate-surface-build"
        self.start_evolution_run(repo, task_id, gap_id)
        value = self.surface_search_value(
            self.surface_source("skill"), decision="build"
        )
        value["candidates"] = []
        value["selected_candidate"] = None
        value["query"] = "@modelcontextprotocol/inspector"
        for source in value["sources_consulted"]:
            source["result"] = "no-match"
            if source["channel"] == "registry":
                source["evidence_url"] = (
                    "https://registry.modelcontextprotocol.io/v0/servers"
                    "?search=%40modelcontextprotocol%2Finspector"
                )
            if source["channel"] == "package-manager":
                source["evidence_url"] = (
                    "https://registry.npmjs.org/"
                    "%40modelcontextprotocol%2Finspector"
                )

        live_body = b'{"error":"Not Found"}\n'
        (self.channel_evidence / "live-not-found.json").write_bytes(live_body)
        live_source = next(
            source
            for source in value["sources_consulted"]
            if source["channel"] == "live-github"
        )
        live_source["evidence_digest"] = hashlib.sha256(live_body).hexdigest()
        live_source["evidence_bytes"] = len(live_body)
        search = self.root / f"{task_id}-search.json"

        version_scoped = json.loads(json.dumps(value))
        next(
            source
            for source in version_scoped["sources_consulted"]
            if source["channel"] == "package-manager"
        )["evidence_url"] += "/definitely-missing"
        search.write_text(json.dumps(version_scoped), encoding="utf-8")
        version_result = self.harness_at(
            repo,
            "evolution",
            "search",
            str(search),
            "--cwd",
            str(repo),
            "--task",
            task_id,
        )
        self.assertNotEqual(version_result.returncode, 0, version_result.stdout)

        unrelated = json.loads(json.dumps(value))
        unrelated_sources = {
            source["channel"]: source
            for source in unrelated["sources_consulted"]
        }
        unrelated_sources["official"]["evidence_url"] = (
            "https://raw.githubusercontent.com/other/project/"
            + "f" * 40
            + "/README.md"
        )
        unrelated_sources["registry"]["evidence_url"] = (
            "https://registry.modelcontextprotocol.io/v0/servers?search=unrelated"
        )
        unrelated_sources["package-manager"]["evidence_url"] = (
            "https://registry.npmjs.org/unrelated/0.0.0"
        )
        unrelated_sources["live-github"]["evidence_url"] = (
            "https://raw.githubusercontent.com/other/project/"
            + "f" * 40
            + "/capability.json"
        )
        search.write_text(json.dumps(unrelated), encoding="utf-8")
        unrelated_result = self.harness_at(
            repo,
            "evolution",
            "search",
            str(search),
            "--cwd",
            str(repo),
            "--task",
            task_id,
        )
        self.assertNotEqual(
            unrelated_result.returncode, 0, unrelated_result.stdout
        )

        forged = json.loads(json.dumps(value))
        forged["sources_consulted"][0]["evidence_digest"] = "0" * 64
        search.write_text(json.dumps(forged), encoding="utf-8")
        rejected = self.harness_at(
            repo,
            "evolution",
            "search",
            str(search),
            "--cwd",
            str(repo),
            "--task",
            task_id,
        )
        self.assertNotEqual(rejected.returncode, 0, rejected.stdout)

        search.write_text(json.dumps(value), encoding="utf-8")
        searched = self.harness_at(
            repo,
            "evolution",
            "search",
            str(search),
            "--cwd",
            str(repo),
            "--task",
            task_id,
        )
        self.assertEqual(searched.returncode, 0, searched.stdout)
        self.assertEqual(json.loads(searched.stdout)["state"], "build-ready")

        built = self.harness_at(
            repo,
            "evolution",
            "build",
            str(ROOT / "harness/fixtures/evolution-build-surface.json"),
            "--cwd",
            str(repo),
            "--task",
            task_id,
        )
        self.assertEqual(built.returncode, 0, built.stdout)
        evaluation = self.root / f"{task_id}-evaluation.json"
        evaluation.write_text(
            json.dumps(
                {
                    "schema": "harness.evolution-evaluation-request/v1",
                    "candidate_digest": json.loads(built.stdout)["candidate_digest"],
                }
            ),
            encoding="utf-8",
        )
        evaluated = self.harness_at(
            repo,
            "evolution",
            "evaluate",
            str(evaluation),
            "--cwd",
            str(repo),
            "--task",
            task_id,
        )
        self.assertEqual(evaluated.returncode, 0, evaluated.stdout)
        self.assertEqual(json.loads(evaluated.stdout)["state"], "promotion-ready")
        commit = self.accept_direct(
            repo, task_id, hashlib.sha256(task_id.encode()).hexdigest()
        )
        self.assertEqual(git(repo, "rev-parse", "HEAD"), commit)

    def test_projection_drift_and_manual_invocation_metadata_fail_closed(self) -> None:
        source = json.loads(
            (ROOT / "harness/fixtures/evolution-build-capability.json").read_text()
        )
        upstream_manual_metadata = {
            "openai_yaml": "policy:\n  allow_implicit_invocation: false\n"
        }
        source["skill"]["invocation"] = {
            "mode": "manual",
            "disable_model_invocation": True,
            "allow_implicit_invocation": False,
            "metadata": upstream_manual_metadata,
            "metadata_digest": digest(upstream_manual_metadata),
        }
        package = compile_evolution_capability(source, "codex")
        projection = self.root / "projection"
        for relative, content in package.items():
            path = projection / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content.encode("utf-8"))

        verified = verify_evolution_projection(source, "codex", projection)

        self.assertEqual(verified["status"], "pass")
        self.assertNotIn(
            "disable-model-invocation: true",
            package["skills/safe-build-fixture/SKILL.md"],
        )
        self.assertEqual(
            package["skills/safe-build-fixture/agents/openai.yaml"],
            upstream_manual_metadata["openai_yaml"],
        )
        source["skill"]["invocation"]["metadata_digest"] = "0" * 64
        with self.assertRaisesRegex(EvolutionError, "metadata"):
            compile_evolution_capability(source, "codex")
        source["skill"]["invocation"]["metadata_digest"] = digest(
            upstream_manual_metadata
        )
        contradictory = {"openai_yaml": "policy:\n  allow_implicit_invocation: true\n"}
        source["skill"]["invocation"]["metadata"] = contradictory
        source["skill"]["invocation"]["metadata_digest"] = digest(contradictory)
        with self.assertRaisesRegex(EvolutionError, "contradicts"):
            compile_evolution_capability(source, "codex")
        source["skill"]["invocation"]["metadata"] = upstream_manual_metadata
        source["skill"]["invocation"]["metadata_digest"] = digest(
            upstream_manual_metadata
        )
        (projection / "unexpected.txt").write_text("drift\n", encoding="utf-8")
        with self.assertRaisesRegex(EvolutionError, "projection drift"):
            verify_evolution_projection(source, "codex", projection)

        source["trust"]["source"] = "pinned-adaptation"
        source["adapted_from"] = {
            "candidate_id": "synthetic-candidate",
            "candidate_digest": "1" * 64,
            "source": "https://github.com/example/synthetic",
            "revision": "2" * 40,
            "artifact_digest": "3" * 64,
        }
        source["agent"]["instructions"].append('unsafe\n"""')
        with self.assertRaisesRegex(EvolutionError, "Agent instructions"):
            compile_evolution_capability(source, "codex")
        source["agent"]["instructions"].pop()
        for secret_like in (
            "DedeUserID=" + "1" * 12,
            "BILIBILI_SESSDATA=" + "A" * 32,
            "BILIBILI_BILI_JCT=" + "B" * 32,
            "BILIBILI_DEDEUSERID=" + "2" * 12,
            "npm_" + "C" * 24,
            "github_pat_" + "D" * 24,
            "Cookie: SESSDATA=" + "E" * 32,
        ):
            source["skill"]["body"].append(secret_like)
            with self.assertRaisesRegex(EvolutionError, "unsafe operational content"):
                compile_evolution_capability(source, "codex")
            source["skill"]["body"].pop()
        for container, secret_like in (
            (
                source["skill"]["interface"]["operations"],
                "DedeUserID=synthetic-interface-user-123456",
            ),
            (
                source["evaluation"]["required_cases"],
                "npm_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
            ),
        ):
            container.append(secret_like)
            with self.assertRaisesRegex(EvolutionError, "unsafe operational content"):
                compile_evolution_capability(source, "codex")
            container.pop()
        secret_metadata = {
            "openai_yaml": (
                "policy:\n  allow_implicit_invocation: false\n"
                + "DedeUserID: "
                + "3" * 12
                + "\n"
            )
        }
        source["skill"]["invocation"]["metadata"] = secret_metadata
        source["skill"]["invocation"]["metadata_digest"] = digest(secret_metadata)
        with self.assertRaisesRegex(EvolutionError, "unsafe operational content"):
            compile_evolution_capability(source, "codex")

    def test_safe_pinned_candidate_is_verified_but_cannot_self_authorize_adapt(
        self,
    ) -> None:
        linked, gap_id = self.accepted_gap_worktree()
        contract = self.write_contract(
            linked,
            "adapt-task",
            self.evolution_owned("adapt-task"),
        )
        self.start_direct(linked, contract)
        evaluator = linked / "evaluation/evaluator.json"
        holdout = linked / "evaluation/holdout.json"
        request = self.request(
            gap_id=gap_id,
            evaluator={
                "path": "evaluation/evaluator.json",
                "digest": hashlib.sha256(evaluator.read_bytes()).hexdigest(),
            },
            holdout={
                "path": "evaluation/holdout.json",
                "digest": hashlib.sha256(holdout.read_bytes()).hexdigest(),
            },
        )
        self.assertEqual(
            self.harness_at(
                linked,
                "evolution",
                "start",
                str(request),
                "--cwd",
                str(linked),
                "--task",
                "adapt-task",
            ).returncode,
            0,
        )
        search_value = self.search_value("adapt")
        candidate = search_value["candidates"][0]
        candidate["compatibility"] = {
            "hosts": ["codex", "claude"],
            "status": "pass",
            "evidence_digest": "4" * 64,
        }
        candidate["smoke"] = {"status": "pass", "evidence_digest": "8" * 64}
        candidate["installed"] = {
            "artifact_digest": candidate["artifact_digest"],
            "provenance": "pinned",
        }
        secret_searches = []
        secret_id = json.loads(json.dumps(search_value))
        secret_id["candidates"][0]["id"] = "npm_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        secret_id["selected_candidate"] = secret_id["candidates"][0]["id"]
        secret_searches.append(secret_id)
        secret_path = json.loads(json.dumps(search_value))
        old_path = secret_path["candidates"][0]["artifact_path"]
        new_path = "skills/DedeUserID=synthetic-path-user-123456/SKILL.md"
        secret_path["candidates"][0]["artifact_path"] = new_path
        next(
            item
            for item in secret_path["candidates"][0]["manifest"]["files"]
            if item["path"] == old_path
        )["path"] = new_path
        secret_path["sources_consulted"][0]["artifact_path"] = new_path
        secret_searches.append(secret_path)
        secret_metadata = json.loads(json.dumps(search_value))
        metadata = {
            "openai_yaml": "policy:\n  allow_implicit_invocation: false\nDedeUserID: synthetic-search-user-123456\n"
        }
        secret_metadata["candidates"][0]["invocation"] = {
            "mode": "manual",
            "disable_model_invocation": True,
            "allow_implicit_invocation": False,
            "metadata": metadata,
            "metadata_digest": digest(metadata),
        }
        secret_searches.append(secret_metadata)
        for index, unsafe_search in enumerate(secret_searches):
            unsafe_path = self.root / f"unsafe-search-{index}.json"
            unsafe_path.write_text(json.dumps(unsafe_search), encoding="utf-8")
            rejected = self.harness_at(
                linked,
                "evolution",
                "search",
                str(unsafe_path),
                "--cwd",
                str(linked),
                "--task",
                "adapt-task",
            )
            self.assertEqual(rejected.returncode, 2, rejected.stdout)
            self.assertIn("secret-like", json.loads(rejected.stdout)["error"])
        search = self.root / "safe-adapt-search.json"
        search.write_text(json.dumps(search_value), encoding="utf-8")
        searched = self.harness_at(
            linked,
            "evolution",
            "search",
            str(search),
            "--cwd",
            str(linked),
            "--task",
            "adapt-task",
        )
        searched_payload = json.loads(searched.stdout)
        self.assertEqual(searched_payload["state"], "authorization-required")
        self.assertTrue(searched_payload["requires_user"])
        self.assertIn(
            "trusted-machine-evidence-unavailable",
            searched_payload["authorization"]["blocks"],
        )
        paths = self.evolution_paths("adapt-task")
        self.assertFalse((linked / paths["package"]).exists())
        state = json.loads(
            next(
                (linked / ".harness/runtime").glob("*/tasks/*/evolution.json")
            ).read_text()
        )
        self.assertEqual(
            state["source_verification"]["observations"]["artifact"]["digest"],
            candidate["artifact_digest"],
        )

    def test_safe_declarative_cli_candidate_auto_adopts_after_live_verification(
        self,
    ) -> None:
        linked, gap_id = self.accepted_gap_worktree()
        contract = self.write_contract(
            linked,
            "surface-adapt-task",
            self.evolution_owned("surface-adapt-task"),
        )
        self.start_direct(linked, contract)
        evaluator = linked / "evaluation/evaluator.json"
        holdout = linked / "evaluation/holdout.json"
        request = self.request(
            gap_id=gap_id,
            evaluator={
                "path": "evaluation/evaluator.json",
                "digest": hashlib.sha256(evaluator.read_bytes()).hexdigest(),
            },
            holdout={
                "path": "evaluation/holdout.json",
                "digest": hashlib.sha256(holdout.read_bytes()).hexdigest(),
            },
        )
        started = self.harness_at(
            linked,
            "evolution",
            "start",
            str(request),
            "--cwd",
            str(linked),
            "--task",
            "surface-adapt-task",
        )
        self.assertEqual(started.returncode, 0, started.stdout)

        source = self.surface_source("cli")
        artifact = (
            json.dumps(source, sort_keys=True, separators=(",", ":")) + "\n"
        ).encode()
        search_value = self.surface_search_value(source)
        search = self.root / "surface-adapt-search.json"
        search.write_text(json.dumps(search_value), encoding="utf-8")

        searched = self.harness_at(
            linked,
            "evolution",
            "search",
            str(search),
            "--cwd",
            str(linked),
            "--task",
            "surface-adapt-task",
        )

        self.assertEqual(searched.returncode, 0, searched.stdout)
        payload = json.loads(searched.stdout)
        self.assertEqual(payload["state"], "adapt-ready")
        self.assertFalse(payload["requires_user"])
        self.assertIsNone(payload["authorization"])

        canonical = self.root / "surface-adapt-capability.json"
        canonical.write_bytes(artifact)
        adapted = self.harness_at(
            linked,
            "evolution",
            "adapt",
            str(canonical),
            "--cwd",
            str(linked),
            "--task",
            "surface-adapt-task",
        )
        self.assertEqual(adapted.returncode, 0, adapted.stdout)
        adapted_payload = json.loads(adapted.stdout)
        self.assertEqual(adapted_payload["state"], "evaluating")
        evaluation = self.root / "surface-adapt-evaluation.json"
        evaluation.write_text(
            json.dumps(
                {
                    "schema": "harness.evolution-evaluation-request/v1",
                    "candidate_digest": adapted_payload["candidate_digest"],
                }
            ),
            encoding="utf-8",
        )
        evaluated = self.harness_at(
            linked,
            "evolution",
            "evaluate",
            str(evaluation),
            "--cwd",
            str(linked),
            "--task",
            "surface-adapt-task",
        )
        self.assertEqual(evaluated.returncode, 0, evaluated.stdout)
        self.assertEqual(json.loads(evaluated.stdout)["state"], "promotion-ready")
        report = json.loads(
            (linked / self.evolution_paths("surface-adapt-task")["report"]).read_text()
        )
        self.assertEqual(report["candidate"]["surface"]["kind"], "cli")
        self.assertEqual(
            report["adapter_smoke"],
            {
                "codex-direct": "pass",
                "claude-direct": "pass",
                "codex-paseo-claude": "pass",
            },
        )
        for adapter in (
            "codex-direct",
            "claude-direct",
            "codex-paseo-claude",
        ):
            smoke = self.harness_at(
                linked,
                "capability",
                "smoke",
                "--cwd",
                str(linked),
                "--name",
                "safe-build-fixture",
                "--adapter",
                adapter,
            )
            self.assertEqual(smoke.returncode, 0, smoke.stderr or smoke.stdout)
            smoke_payload = json.loads(smoke.stdout)
            self.assertEqual(smoke_payload["status"], "pass")
            self.assertEqual(smoke_payload["kind"], "cli")

    def test_surface_candidate_cannot_use_legacy_search_schema(self) -> None:
        repo, gap_id = self.accepted_gap_worktree()
        task_id = "surface-legacy-search"
        self.start_evolution_run(repo, task_id, gap_id)
        value = self.surface_search_value(self.surface_source("cli"))
        value["schema"] = "harness.evolution-search/v1"
        value.pop("channels")
        source = value["sources_consulted"][0]
        source.pop("channel")
        value["sources_consulted"] = [source]
        search = self.root / f"{task_id}-search.json"
        search.write_text(json.dumps(value), encoding="utf-8")
        result = self.harness_at(
            repo,
            "evolution",
            "search",
            str(search),
            "--cwd",
            str(repo),
            "--task",
            task_id,
        )
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("v2 Search", result.stdout + result.stderr)

    def test_surface_search_verifies_each_channel_response(self) -> None:
        repo, gap_id = self.accepted_gap_worktree()
        task_id = "surface-channel-evidence"
        self.start_evolution_run(repo, task_id, gap_id)
        value = self.surface_search_value(self.surface_source("cli"))
        registry = next(
            item for item in value["sources_consulted"] if item["channel"] == "registry"
        )
        registry["evidence_digest"] = "0" * 64
        search = self.root / f"{task_id}-search.json"
        search.write_text(json.dumps(value), encoding="utf-8")
        result = self.harness_at(
            repo,
            "evolution",
            "search",
            str(search),
            "--cwd",
            str(repo),
            "--task",
            task_id,
        )
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("channel evidence", result.stdout + result.stderr)

    def test_surface_search_derives_channel_result_from_response(self) -> None:
        repo, gap_id = self.accepted_gap_worktree()
        task_id = "surface-channel-result"
        self.start_evolution_run(repo, task_id, gap_id)
        value = self.surface_search_value(self.surface_source("cli"))
        registry = next(
            item for item in value["sources_consulted"] if item["channel"] == "registry"
        )
        registry["result"] = "candidate"
        search = self.root / f"{task_id}-search.json"
        search.write_text(json.dumps(value), encoding="utf-8")
        result = self.harness_at(
            repo,
            "evolution",
            "search",
            str(search),
            "--cwd",
            str(repo),
            "--task",
            task_id,
        )
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("channel result", result.stdout + result.stderr)

    def test_dangerous_surface_candidate_stops_at_one_user_authorization(self) -> None:
        linked, gap_id = self.accepted_gap_worktree()
        self.start_evolution_run(linked, "dangerous-surface-task", gap_id)
        invalid_hook = self.root / "invalid-hook-surface-search.json"
        invalid_hook.write_text(
            json.dumps(self.surface_search_value(self.surface_source("hook"))),
            encoding="utf-8",
        )
        rejected_hook = self.harness_at(
            linked,
            "evolution",
            "search",
            str(invalid_hook),
            "--cwd",
            str(linked),
            "--task",
            "dangerous-surface-task",
        )
        self.assertEqual(rejected_hook.returncode, 2, rejected_hook.stdout)
        self.assertIn("Hook surface policy", json.loads(rejected_hook.stdout)["error"])

        source = self.surface_source("mcp")
        search_value = self.surface_search_value(
            source,
            effects={
                "credentials": True,
                "elevation": True,
                "daemon": True,
                "open_port": True,
                "global_policy": True,
                "global_mutation": True,
                "ssh": True,
                "publish": True,
            },
        )
        search = self.root / "dangerous-surface-search.json"
        search.write_text(json.dumps(search_value), encoding="utf-8")

        first = self.harness_at(
            linked,
            "evolution",
            "search",
            str(search),
            "--cwd",
            str(linked),
            "--task",
            "dangerous-surface-task",
        )
        repeated = self.harness_at(
            linked,
            "evolution",
            "search",
            str(search),
            "--cwd",
            str(linked),
            "--task",
            "dangerous-surface-task",
        )

        self.assertEqual(first.returncode, 0, first.stdout)
        self.assertEqual(first.stdout, repeated.stdout)
        payload = json.loads(first.stdout)
        self.assertEqual(payload["state"], "authorization-required")
        self.assertTrue(payload["requires_user"])
        self.assertEqual(
            set(payload["authorization"]["blocks"]),
            {
                "effect-credentials",
                "effect-elevation",
                "effect-daemon",
                "effect-open_port",
                "effect-global_policy",
                "effect-global_mutation",
                "effect-ssh",
                "effect-publish",
            },
        )
        self.assertFalse(
            (
                linked / self.evolution_paths("dangerous-surface-task")["package"]
            ).exists()
        )

    def test_repository_local_surface_builds_promote_in_all_three_adapters(
        self,
    ) -> None:
        first, gap_id = self.accepted_gap_worktree()
        kinds = {
            "cli": {"hook": None, "loop": None},
            "mcp": {"hook": None, "loop": None},
            "hook": {
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
            },
            "loop": {
                "hook": None,
                "loop": {
                    "origin": "accepted-gap",
                    "max_attempts": 2,
                    "no_progress_limit": 1,
                    "yield_to_user": True,
                    "adapter_switch_policy": "stop-and-report",
                },
            },
        }
        for index, (kind, policy) in enumerate(kinds.items()):
            with self.subTest(kind=kind):
                repo = first
                if index:
                    repo = self.root / f"surface-{kind}-worktree"
                    git(
                        self.repo,
                        "worktree",
                        "add",
                        "-b",
                        f"surface-{kind}",
                        str(repo),
                        "HEAD",
                    )
                task_id = f"surface-build-{kind}"
                self.start_evolution_run(repo, task_id, gap_id)
                source = json.loads(
                    (ROOT / "harness/fixtures/evolution-build-surface.json").read_text()
                )
                source["surface"].update(
                    {
                        "kind": kind,
                        "external_system": kind == "mcp",
                        **policy,
                    }
                )
                search = self.root / f"{task_id}-search.json"
                search.write_text(
                    json.dumps(
                        self.surface_search_value(
                            {**source, "license": "MIT"},
                            decision="build",
                            effects={"daemon": True},
                        )
                    ),
                    encoding="utf-8",
                )
                searched = self.harness_at(
                    repo,
                    "evolution",
                    "search",
                    str(search),
                    "--cwd",
                    str(repo),
                    "--task",
                    task_id,
                )
                self.assertEqual(searched.returncode, 0, searched.stdout)
                source_path = self.root / f"{task_id}-source.json"
                source_path.write_text(json.dumps(source), encoding="utf-8")
                built = self.harness_at(
                    repo,
                    "evolution",
                    "build",
                    str(source_path),
                    "--cwd",
                    str(repo),
                    "--task",
                    task_id,
                )
                self.assertEqual(built.returncode, 0, built.stdout)
                candidate_digest = json.loads(built.stdout)["candidate_digest"]
                evaluation = self.root / f"{task_id}-evaluation.json"
                evaluation.write_text(
                    json.dumps(
                        {
                            "schema": "harness.evolution-evaluation-request/v1",
                            "candidate_digest": candidate_digest,
                        }
                    ),
                    encoding="utf-8",
                )
                evaluated = self.harness_at(
                    repo,
                    "evolution",
                    "evaluate",
                    str(evaluation),
                    "--cwd",
                    str(repo),
                    "--task",
                    task_id,
                )
                self.assertEqual(evaluated.returncode, 0, evaluated.stdout)
                self.assertEqual(
                    json.loads(evaluated.stdout)["state"],
                    "promotion-ready",
                    evaluated.stdout,
                )
                paths = self.evolution_paths(task_id)
                for host in ("codex", "claude"):
                    runtime = json.loads(
                        (
                            repo
                            / paths[host]
                            / "skills/safe-build-fixture/surface.json"
                        ).read_text()
                    )
                    self.assertEqual(runtime["schema"], "harness.surface-runtime/v1")
                    if kind == "hook":
                        self.assertEqual(
                            runtime["entrypoint"]["command"][-1], "hook-event"
                        )
                for adapter in (
                    "codex-direct",
                    "claude-direct",
                    "codex-paseo-claude",
                ):
                    smoke = self.harness_at(
                        repo,
                        "capability",
                        "smoke",
                        "--cwd",
                        str(repo),
                        "--name",
                        "safe-build-fixture",
                        "--adapter",
                        adapter,
                    )
                    self.assertEqual(smoke.returncode, 0, smoke.stdout)
                    smoke_payload = json.loads(smoke.stdout)
                    self.assertEqual(smoke_payload["status"], "pass")
                    self.assertTrue(smoke_payload["observations"])
                    self.assertEqual(
                        smoke_payload["hosts"],
                        (
                            ["codex", "claude"]
                            if adapter == "codex-paseo-claude"
                            else ["codex" if adapter == "codex-direct" else "claude"]
                        ),
                    )
                if kind == "cli":
                    request = self.root / f"{task_id}-call.json"
                    request.write_text(
                        json.dumps(
                            {
                                "schema": "harness.surface-call/v1",
                                "operation": "inspect",
                                "arguments": {},
                            }
                        ),
                        encoding="utf-8",
                    )
                    called = self.harness_at(
                        repo,
                        "capability",
                        "call",
                        str(request),
                        "--cwd",
                        str(repo),
                        "--name",
                        "safe-build-fixture",
                        "--adapter",
                        "codex-direct",
                    )
                    self.assertEqual(called.returncode, 0, called.stdout)
                    self.assertEqual(json.loads(called.stdout)["operation"], "inspect")
                if kind == "mcp":
                    requests = [
                        {
                            "jsonrpc": "2.0",
                            "id": 1,
                            "method": "initialize",
                            "params": {
                                "protocolVersion": "2025-03-26",
                                "capabilities": {},
                                "clientInfo": {
                                    "name": "harness-test",
                                    "version": "1",
                                    "title": "Harness Test",
                                    "websiteUrl": "https://example.invalid/harness",
                                    "description": "Bounded test client",
                                    "icons": [
                                        {
                                            "src": "data:image/png;base64,AA==",
                                            "mimeType": "image/png",
                                            "sizes": ["16x16", "any"],
                                            "theme": "dark",
                                        }
                                    ],
                                },
                                "_meta": {
                                    "io.modelcontextprotocol/related-task": {
                                        "taskId": "task-1"
                                    }
                                },
                            },
                        },
                        {
                            "jsonrpc": "2.0",
                            "method": "notifications/initialized",
                        },
                        {
                            "jsonrpc": "2.0",
                            "id": 2,
                            "method": "ping",
                            "params": {"_meta": {"progressToken": "ping-1"}},
                        },
                        {
                            "jsonrpc": "2.0",
                            "id": 3,
                            "method": "tools/list",
                            "params": {
                                "cursor": "opaque-cursor",
                                "_meta": {"extension.trace": "bounded"},
                            },
                        },
                        {
                            "jsonrpc": "2.0",
                            "id": 4,
                            "method": "tools/call",
                            "params": {"name": "inspect", "arguments": {}},
                        },
                    ]
                    served = self.harness_at(
                        repo,
                        "capability",
                        "serve",
                        "--cwd",
                        str(repo),
                        "--name",
                        "safe-build-fixture",
                        "--adapter",
                        "codex-direct",
                        input_text="".join(
                            json.dumps(item) + "\n" for item in requests
                        ),
                    )
                    self.assertEqual(served.returncode, 0, served.stdout)
                    responses = [
                        json.loads(line) for line in served.stdout.splitlines()
                    ]
                    self.assertEqual(
                        [item["id"] for item in responses], [1, 2, 3, 4]
                    )
                    self.assertEqual(
                        responses[0]["result"]["protocolVersion"], "2025-03-26"
                    )
                    self.assertEqual(responses[1]["result"], {})
                    self.assertEqual(
                        [tool["name"] for tool in responses[2]["result"]["tools"]],
                        ["inspect", "report"],
                    )
                    self.assertNotIn("nextCursor", responses[2]["result"])
                    self.assertFalse(responses[3]["result"]["isError"])
                if kind == "hook":
                    payload = self.root / f"{task_id}-hook.json"
                    payload.write_text(
                        json.dumps(
                            {
                                "session_id": "hook-public-cli",
                                "tool_name": "shell_command",
                                "tool_input": {"command": "npm test"},
                                "tool_response": {"exit_code": 0},
                            }
                        ),
                        encoding="utf-8",
                    )
                    invoked = self.harness_at(
                        repo,
                        "capability",
                        "hook-event",
                        str(payload),
                        "--cwd",
                        str(repo),
                        "--name",
                        "safe-build-fixture",
                        "--adapter",
                        "codex-direct",
                        "--host",
                        "codex",
                        "--event",
                        "post-tool-use",
                    )
                    self.assertEqual(invoked.returncode, 0, invoked.stdout)
                    self.assertEqual(json.loads(invoked.stdout)["status"], "recorded")
                report = json.loads((repo / paths["report"]).read_text())
                self.assertEqual(report["surface"]["kind"], kind)
                self.assertEqual(
                    report["adapter_smoke"],
                    {
                        "codex-direct": "pass",
                        "claude-direct": "pass",
                        "codex-paseo-claude": "pass",
                    },
                )
                if kind == "hook":
                    self.assertEqual(
                        report["surface_checks"],
                        {phase: "pass" for phase in policy["hook"]["phases"]},
                    )
                if kind == "loop":
                    self.assertEqual(
                        report["surface_checks"],
                        {
                            "bounded": "pass",
                            "no-progress-stop": "pass",
                            "yield-to-user": "pass",
                            "no-adapter-switch": "pass",
                        },
                    )
                base = git(repo, "rev-parse", "HEAD")
                commit = self.accept_direct(
                    repo, task_id, hashlib.sha256(task_id.encode()).hexdigest()
                )
                self.assertEqual(git(repo, "rev-list", "--count", f"{base}..HEAD"), "1")
                self.assertEqual(git(repo, "rev-parse", "HEAD"), commit)
                self.assertEqual(git(repo, "remote"), "")
                self.assertTrue(
                    all(
                        not path.startswith("src/")
                        for path in git(
                            repo, "show", "--pretty=", "--name-only", "HEAD"
                        ).splitlines()
                    )
                )

    def test_surface_build_requires_v2_search_evidence(self) -> None:
        repo, gap_id = self.accepted_gap_worktree()
        task_id = "surface-build-search-version"
        self.start_evolution_run(repo, task_id, gap_id)
        search = self.root / f"{task_id}-search.json"
        search.write_text(json.dumps(self.search_value("build")), encoding="utf-8")
        searched = self.harness_at(
            repo,
            "evolution",
            "search",
            str(search),
            "--cwd",
            str(repo),
            "--task",
            task_id,
        )
        self.assertEqual(searched.returncode, 0, searched.stdout)
        built = self.harness_at(
            repo,
            "evolution",
            "build",
            str(ROOT / "harness/fixtures/evolution-build-surface.json"),
            "--cwd",
            str(repo),
            "--task",
            task_id,
        )
        self.assertNotEqual(built.returncode, 0, built.stdout)
        self.assertIn("v2 Search evidence", built.stdout + built.stderr)

    def test_build_fixture_rolls_back_failure_and_promotes_once_after_independent_pass(
        self,
    ) -> None:
        first, gap_id = self.accepted_gap_worktree()
        prior = {
            "harness/capability-packages/existing-capability/canonical.json": b'{"schema":"prior/v1"}\n',
            "harness/capability-packages/existing-capability/codex/existing.txt": b"prior codex\n",
            "harness/capability-packages/existing-capability/claude/existing.txt": b"prior claude\n",
        }
        for relative, content in prior.items():
            target = first / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        git(first, "add", "harness/capability-packages")
        git(first, "commit", "-m", "seed prior capability")

        def begin(repo: Path, task_id: str) -> str:
            contract = self.write_contract(
                repo,
                task_id,
                self.evolution_owned(task_id),
            )
            self.start_direct(repo, contract)
            evaluator = repo / "evaluation/evaluator.json"
            holdout = repo / "evaluation/holdout.json"
            request = self.request(
                gap_id=gap_id,
                evaluator={
                    "path": "evaluation/evaluator.json",
                    "digest": hashlib.sha256(evaluator.read_bytes()).hexdigest(),
                },
                holdout={
                    "path": "evaluation/holdout.json",
                    "digest": hashlib.sha256(holdout.read_bytes()).hexdigest(),
                },
            )
            started = self.harness_at(
                repo,
                "evolution",
                "start",
                str(request),
                "--cwd",
                str(repo),
                "--task",
                task_id,
            )
            self.assertEqual(started.returncode, 0, started.stdout)
            search = self.root / f"{task_id}-search.json"
            search.write_text(json.dumps(self.search_value("build")), encoding="utf-8")
            searched = self.harness_at(
                repo,
                "evolution",
                "search",
                str(search),
                "--cwd",
                str(repo),
                "--task",
                task_id,
            )
            self.assertEqual(searched.returncode, 0, searched.stdout)
            built = self.harness_at(
                repo,
                "evolution",
                "build",
                str(ROOT / "harness/fixtures/evolution-build-capability.json"),
                "--cwd",
                str(repo),
                "--task",
                task_id,
            )
            self.assertEqual(built.returncode, 0, built.stderr or built.stdout)
            payload = json.loads(built.stdout)
            self.assertEqual(payload["state"], "evaluating")
            blocked_acceptance = self.harness_at(
                repo,
                "codex-direct",
                "advance",
                "--to",
                "verifying",
                "--cwd",
                str(repo),
                "--task",
                task_id,
            )
            self.assertEqual(blocked_acceptance.returncode, 2)
            self.assertIn("not ready", json.loads(blocked_acceptance.stdout)["error"])
            return payload["candidate_digest"]

        def evaluate(
            repo: Path, task_id: str, candidate_digest: str
        ) -> subprocess.CompletedProcess[str]:
            path = self.root / f"{task_id}-evaluation.json"
            path.write_text(
                json.dumps(
                    {
                        "schema": "harness.evolution-evaluation-request/v1",
                        "candidate_digest": candidate_digest,
                    }
                ),
                encoding="utf-8",
            )
            return self.harness_at(
                repo,
                "evolution",
                "evaluate",
                str(path),
                "--cwd",
                str(repo),
                "--task",
                task_id,
            )

        rejected_digest = begin(first, "build-rejected")
        rejected_paths = self.evolution_paths("build-rejected")
        rejected_evaluator = first / "evaluation/evaluator.json"
        evaluator_bytes = rejected_evaluator.read_bytes()
        rejected_evaluator.write_text("drift\n", encoding="utf-8")
        rejected = evaluate(first, "build-rejected", rejected_digest)
        self.assertEqual(rejected.returncode, 0, rejected.stderr or rejected.stdout)
        self.assertEqual(json.loads(rejected.stdout)["state"], "rejected")
        rejected_evaluator.write_bytes(evaluator_bytes)
        for relative, content in prior.items():
            self.assertEqual((first / relative).read_bytes(), content)
        self.assertFalse((first / rejected_paths["package"]).exists())
        rejected_report = json.loads((first / rejected_paths["report"]).read_text())
        self.assertEqual(rejected_report["outcome"], "rejected")
        rejected_base = git(first, "rev-parse", "HEAD")
        rejected_commit = self.accept_direct(
            first,
            "build-rejected",
            hashlib.sha256(b"build-rejected-evidence").hexdigest(),
        )
        self.assertEqual(
            git(first, "rev-list", "--count", f"{rejected_base}..HEAD"), "1"
        )
        self.assertEqual(git(first, "rev-parse", "HEAD"), rejected_commit)

        second = self.root / "build-success-worktree"
        git(self.repo, "worktree", "add", "-b", "build-success", str(second), "HEAD")
        promoted_digest = begin(second, "build-promoted")
        promoted = evaluate(second, "build-promoted", promoted_digest)
        self.assertEqual(promoted.returncode, 0, promoted.stderr or promoted.stdout)
        self.assertEqual(json.loads(promoted.stdout)["state"], "promotion-ready")
        promoted_paths = self.evolution_paths("build-promoted")
        for key, child in (
            ("codex_skill", "SKILL.md"),
            ("claude_skill", "SKILL.md"),
            ("codex_agent", None),
            ("claude_agent", None),
        ):
            target = second / promoted_paths[key]
            self.assertTrue((target / child if child else target).is_file())
        clean_home = self.root / "build-clean-home"
        clean_home.mkdir()
        doctor_env = isolated_environment()
        doctor_env.update({"HOME": str(clean_home), "USERPROFILE": str(clean_home)})
        doctor = subprocess.run(
            [
                sys.executable,
                "-m",
                "harness",
                "doctor",
                "--json",
                "--repo",
                str(second),
            ],
            cwd=second,
            env=doctor_env,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(doctor.returncode, 0, doctor.stdout)
        discovered = json.loads(doctor.stdout)["capabilities"]
        self.assertIn("safe-build-fixture", discovered["codex_agents"])
        self.assertIn("safe-build-fixture", discovered["claude_agents"])
        (second / promoted_paths["codex"] / "manifest.json").unlink()
        terminal_revalidation = self.harness_at(
            second,
            "codex-direct",
            "advance",
            "--to",
            "verifying",
            "--cwd",
            str(second),
            "--task",
            "build-promoted",
        )
        self.assertEqual(
            terminal_revalidation.returncode, 0, terminal_revalidation.stdout
        )
        self.assertFalse((second / promoted_paths["package"]).exists())
        terminal_report = json.loads((second / promoted_paths["report"]).read_text())
        self.assertEqual(terminal_report["outcome"], "rejected")
        self.assertEqual(terminal_report["reason_code"], "terminal-revalidation-failed")
        existing = self.root / "existing-capability-worktree"
        git(first, "worktree", "add", "-b", "existing-success", str(existing), "HEAD")
        existing_base = git(existing, "rev-parse", "HEAD")
        promoted_digest = begin(existing, "existing-promoted")
        promoted = evaluate(existing, "existing-promoted", promoted_digest)
        self.assertEqual(promoted.returncode, 0, promoted.stderr or promoted.stdout)
        self.assertEqual(json.loads(promoted.stdout)["state"], "promotion-ready")
        commit = self.accept_direct(
            existing,
            "existing-promoted",
            hashlib.sha256(b"existing-promoted-evidence").hexdigest(),
        )
        for relative, content in prior.items():
            self.assertEqual((existing / relative).read_bytes(), content)
        self.assertEqual(
            git(existing, "rev-list", "--count", f"{existing_base}..HEAD"), "1"
        )
        repeated = self.harness_at(
            existing,
            "codex-direct",
            "accept",
            "--cwd",
            str(existing),
            "--task",
            "existing-promoted",
            "--message",
            "test(harness): accept existing-promoted",
        )
        self.assertEqual(repeated.returncode, 0, repeated.stdout)
        self.assertEqual(
            json.loads(repeated.stdout)["commit_status"], "already-committed"
        )
        self.assertEqual(git(existing, "rev-parse", "HEAD"), commit)
        self.assertEqual(git(existing, "remote"), "")
        self.assertEqual(git(existing, "status", "--short"), "")

    def test_evaluator_and_projection_drift_roll_back_without_self_approval(
        self,
    ) -> None:
        linked, gap_id = self.accepted_gap_worktree()
        contract = self.write_contract(
            linked,
            "drift-task",
            self.evolution_owned("drift-task"),
        )
        self.start_direct(linked, contract)
        evaluator = linked / "evaluation/evaluator.json"
        holdout = linked / "evaluation/holdout.json"
        request = self.request(
            gap_id=gap_id,
            evaluator={
                "path": "evaluation/evaluator.json",
                "digest": hashlib.sha256(evaluator.read_bytes()).hexdigest(),
            },
            holdout={
                "path": "evaluation/holdout.json",
                "digest": hashlib.sha256(holdout.read_bytes()).hexdigest(),
            },
        )
        self.assertEqual(
            self.harness_at(
                linked,
                "evolution",
                "start",
                str(request),
                "--cwd",
                str(linked),
                "--task",
                "drift-task",
            ).returncode,
            0,
        )
        search = self.root / "drift-search.json"
        search.write_text(json.dumps(self.search_value("build")), encoding="utf-8")
        self.assertEqual(
            self.harness_at(
                linked,
                "evolution",
                "search",
                str(search),
                "--cwd",
                str(linked),
                "--task",
                "drift-task",
            ).returncode,
            0,
        )
        built = self.harness_at(
            linked,
            "evolution",
            "build",
            str(ROOT / "harness/fixtures/evolution-build-capability.json"),
            "--cwd",
            str(linked),
            "--task",
            "drift-task",
        )
        candidate_digest = json.loads(built.stdout)["candidate_digest"]
        drift_state = next(
            (linked / ".harness/runtime").glob("*/tasks/*/evolution.json")
        )
        frozen_drift_state = drift_state.read_bytes()
        forged = json.loads(frozen_drift_state)
        forged.update(
            {
                "state": "promotion-ready",
                "outcome": "promotable",
                "outcome_reason": "independent-evaluation-passed",
            }
        )
        drift_state.write_text(json.dumps(forged), encoding="utf-8")
        self.assert_acceptance_blocked(linked, "drift-task", "state is invalid")
        drift_state.write_bytes(frozen_drift_state)
        evaluation = self.root / "drift-evaluation.json"
        evaluation.write_text(
            json.dumps(
                {
                    "schema": "harness.evolution-evaluation-request/v1",
                    "candidate_digest": candidate_digest,
                    "evaluator": {"id": "codex", "result": "pass"},
                }
            ),
            encoding="utf-8",
        )
        self_approval = self.harness_at(
            linked,
            "evolution",
            "evaluate",
            str(evaluation),
            "--cwd",
            str(linked),
            "--task",
            "drift-task",
        )
        self.assertEqual(self_approval.returncode, 2)
        self.assertIn("evaluation request", json.loads(self_approval.stdout)["error"])

        evaluation.write_text(
            json.dumps(
                {
                    "schema": "harness.evolution-evaluation-request/v1",
                    "candidate_digest": candidate_digest,
                }
            ),
            encoding="utf-8",
        )
        paths = self.evolution_paths("drift-task")
        (linked / paths["codex"] / "manifest.json").write_text("{}\n", encoding="utf-8")
        drifted = self.harness_at(
            linked,
            "evolution",
            "evaluate",
            str(evaluation),
            "--cwd",
            str(linked),
            "--task",
            "drift-task",
        )
        self.assertEqual(drifted.returncode, 6, drifted.stdout)
        self.assertEqual(json.loads(drifted.stdout)["state"], "recovery-required")
        self.assertEqual(
            (linked / paths["codex"] / "manifest.json").read_text(encoding="utf-8"),
            "{}\n",
        )

        other = self.root / "evaluator-drift-worktree"
        git(self.repo, "worktree", "add", "-b", "evaluator-drift", str(other), "HEAD")
        other_contract = self.write_contract(
            other,
            "evaluator-drift-task",
            self.evolution_owned("evaluator-drift-task"),
        )
        self.start_direct(other, other_contract)
        other_evaluator = other / "evaluation/evaluator.json"
        other_holdout = other / "evaluation/holdout.json"
        other_evaluator_bytes = other_evaluator.read_bytes()
        other_holdout_digest = hashlib.sha256(other_holdout.read_bytes()).hexdigest()
        other_request = self.request(
            gap_id=gap_id,
            evaluator={
                "path": "evaluation/evaluator.json",
                "digest": hashlib.sha256(other_evaluator.read_bytes()).hexdigest(),
            },
            holdout={
                "path": "evaluation/holdout.json",
                "digest": other_holdout_digest,
            },
        )
        self.assertEqual(
            self.harness_at(
                other,
                "evolution",
                "start",
                str(other_request),
                "--cwd",
                str(other),
                "--task",
                "evaluator-drift-task",
            ).returncode,
            0,
        )
        other_evaluator.write_text("drift\n", encoding="utf-8")
        blocked = self.harness_at(
            other,
            "evolution",
            "search",
            str(search),
            "--cwd",
            str(other),
            "--task",
            "evaluator-drift-task",
        )
        self.assertEqual(blocked.returncode, 2, blocked.stdout)
        self.assertIn("evaluator", json.loads(blocked.stdout)["error"])
        self.assertFalse(
            (other / self.evolution_paths("evaluator-drift-task")["package"]).exists()
        )

        other_evaluator.write_bytes(other_evaluator_bytes)
        searched_after_restore = self.harness_at(
            other,
            "evolution",
            "search",
            str(search),
            "--cwd",
            str(other),
            "--task",
            "evaluator-drift-task",
        )
        self.assertEqual(
            searched_after_restore.returncode, 0, searched_after_restore.stdout
        )
        built_after_restore = self.harness_at(
            other,
            "evolution",
            "build",
            str(ROOT / "harness/fixtures/evolution-build-capability.json"),
            "--cwd",
            str(other),
            "--task",
            "evaluator-drift-task",
        )
        self.assertEqual(built_after_restore.returncode, 0, built_after_restore.stdout)
        other_holdout.write_text("drift\n", encoding="utf-8")
        other_evidence = {
            "schema": "harness.evolution-evaluation-request/v1",
            "candidate_digest": json.loads(built_after_restore.stdout)[
                "candidate_digest"
            ],
        }
        other_evaluation = self.root / "evaluator-drift-evaluation.json"
        other_evaluation.write_text(json.dumps(other_evidence), encoding="utf-8")
        drift_after_build = self.harness_at(
            other,
            "evolution",
            "evaluate",
            str(other_evaluation),
            "--cwd",
            str(other),
            "--task",
            "evaluator-drift-task",
        )
        self.assertEqual(drift_after_build.returncode, 0, drift_after_build.stdout)
        self.assertEqual(json.loads(drift_after_build.stdout)["state"], "rejected")
        self.assertFalse(
            (other / self.evolution_paths("evaluator-drift-task")["package"]).exists()
        )


if __name__ == "__main__":
    unittest.main()
