"""Governed Skill and Agent evolution from accepted typed capability gaps."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path, PurePosixPath
from typing import Any

from harness.codex_direct import (
    CodexDirectAdapterError,
    _changed_paths,
    _commit_parents,
    _commit_paths,
    _commit_tree_snapshot,
    _git_bytes,
    _load_run,
    _path_is_owned,
    _run_git_bytes,
    _task_key,
    _task_dir,
)
from harness.context import WorktreeContext
from harness.memory import (
    FORBIDDEN_TEXT,
    SECRET_TEXT,
    MemoryProjectionError,
    compile_host_package,
    startup_memory,
)
from harness.safe_io import (
    _atomic_write_bytes,
    _rmdir_nofollow,
    _unlink_nofollow,
    bounded_file_lock,
    ensure_no_link_components,
    read_bounded_bytes,
    read_bounded_json_object,
    validate_json_shape,
    write_bounded_text,
)


TASK_RE = re.compile(r"[A-Za-z0-9_.:#-]{1,128}")
DIGEST_RE = re.compile(r"[0-9a-f]{64}")
CAPABILITY_RE = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")
WINDOWS_RESERVED = {
    "con",
    "prn",
    "aux",
    "nul",
    *(f"com{index}" for index in range(1, 10)),
    *(f"lpt{index}" for index in range(1, 10)),
}
EVALUATOR_CASES = ["canonical-source", "codex-discovery", "claude-discovery"]
HOLDOUT_CASES = ["read-only-agent", "no-agent-tree"]
EVOLUTION_SURFACES = {"mcp", "cli", "hook", "loop"}
SURFACE_ADAPTERS = [
    "codex-direct",
    "claude-direct",
    "codex-paseo-claude",
]
MCP_LATEST_PROTOCOL_VERSION = "2025-11-25"
MCP_SUPPORTED_PROTOCOL_VERSIONS = (
    MCP_LATEST_PROTOCOL_VERSION,
    "2025-06-18",
    "2025-03-26",
    "2024-11-05",
    "2024-10-07",
)
SEARCH_CHANNELS = ["official", "registry", "package-manager", "live-github"]
SEARCH_CHANNEL_HOSTS = {
    "official": {"raw.githubusercontent.com"},
    "registry": {"registry.modelcontextprotocol.io"},
    "package-manager": {"registry.npmjs.org"},
    "live-github": {"raw.githubusercontent.com"},
}
HOOK_PHASES = [
    "replay",
    "shadow",
    "no-secret",
    "multi-worktree",
    "canary",
    "rollback",
]
LICENSES = {
    "Apache-2.0",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "GPL-3.0-only",
    "ISC",
    "MIT",
    "MPL-2.0",
}
LICENSE_MARKERS = {
    "Apache-2.0": ("Apache License", "Version 2.0"),
    "BSD-2-Clause": ("Redistribution and use in source and binary forms",),
    "BSD-3-Clause": ("Redistribution and use in source and binary forms",),
    "GPL-3.0-only": ("GNU GENERAL PUBLIC LICENSE", "Version 3"),
    "ISC": ("Permission to use, copy, modify, and/or distribute",),
    "MIT": ("MIT License", "Permission is hereby granted"),
    "MPL-2.0": ("Mozilla Public License Version 2.0",),
}
SAFE_BUILD_BODY = [
    "Resolve the active worktree before inspecting metadata.",
    "Inspect only repository-relative paths explicitly supplied by the parent task.",
    "Refuse ignored, environment, credential, configuration, and private paths.",
    "Return bounded metadata findings without file contents, commands, or private paths.",
]
SAFE_BUILD_AGENT_INSTRUCTIONS = [
    "Inspect only the repository-relative paths named by the parent task.",
    "Refuse ignored, environment, credential, configuration, and private paths.",
    "Do not edit files, acquire a writer lease, delegate, or spawn another agent.",
    "Report bounded metadata findings without file contents, then stop.",
]


class EvolutionError(ValueError):
    """An Evolution Run violates its governed contract."""


class EvolutionAdapterError(CodexDirectAdapterError):
    """An Evolution Run failed while applying or restoring local effects."""


def _canonical_text(value: Any) -> str:
    return json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_text(value).encode("utf-8")).hexdigest()


def _exact(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise EvolutionError(f"{label} is invalid")
    return value


def _nonempty(value: Any, label: str, limit: int = 256) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or value != value.strip()
        or len(value) > limit
        or any(ord(char) < 32 or ord(char) == 127 for char in value)
    ):
        raise EvolutionError(f"{label} is invalid")
    return value


def _bounded_string(value: Any, label: str, limit: int) -> str:
    if (
        not isinstance(value, str)
        or len(value) > limit
        or any(ord(char) < 32 or ord(char) == 127 for char in value)
    ):
        raise EvolutionError(f"{label} is invalid")
    return value


def _relative_path(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 256:
        raise EvolutionError(f"{label} is invalid")
    path = PurePosixPath(value.replace("\\", "/"))
    if path.is_absolute() or any(
        part in {"", ".", ".."}
        or part.endswith((".", " "))
        or ":" in part
        or "~" in part
        or part.split(".", 1)[0].casefold() in WINDOWS_RESERVED
        for part in path.parts
    ):
        raise EvolutionError(f"{label} is invalid")
    return path.as_posix()


def _capability_paths(task_id: str, name: str) -> dict[str, str]:
    if (
        not CAPABILITY_RE.fullmatch(name)
        or name.split(".", 1)[0].casefold() in WINDOWS_RESERVED
    ):
        raise EvolutionError("capability name is invalid")
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


def _required_owned_paths(task_id: str, name: str) -> set[str]:
    paths = _capability_paths(task_id, name)
    return {
        f"{paths['package']}/",
        f"{paths['codex_skill']}/",
        f"{paths['claude_skill']}/",
        paths["codex_agent"],
        paths["claude_agent"],
        paths["report"],
    }


def _expected_writer(mode: str) -> str | None:
    return {
        "codex-direct": "codex",
        "claude-direct": "claude",
        "codex-paseo-claude": "claude",
    }.get(mode)


def _require_writer_actor(mode: str, actor: str | None) -> str:
    writer = _expected_writer(mode)
    if writer is None or actor != writer:
        raise EvolutionError("Evolution mutation actor does not hold the writer lease")
    return writer


def _ignored_path(context: WorktreeContext, path: str) -> bool:
    return bool(
        _run_git_bytes(
            context.root,
            ("check-ignore", "--no-index", "--", path),
            {0, 1},
            env_overrides={"GIT_LITERAL_PATHSPECS": "0"},
        )
    )


def _assert_tracked_targets(context: WorktreeContext, paths: dict[str, str]) -> None:
    probes = (
        paths["canonical"],
        f"{paths['codex']}/manifest.json",
        f"{paths['claude']}/manifest.json",
        f"{paths['codex_skill']}/SKILL.md",
        f"{paths['claude_skill']}/SKILL.md",
        paths["codex_agent"],
        paths["claude_agent"],
        paths["report"],
    )
    if any(_ignored_path(context, path) for path in probes):
        raise EvolutionError("Evolution managed output is ignored by Git")


def _assert_projection_tracked(
    context: WorktreeContext, projection: dict[str, Any], report_path: str
) -> None:
    if any(
        _ignored_path(context, path) for path in (*projection["files"], report_path)
    ):
        raise EvolutionError("Evolution managed output is ignored by Git")


def _fixed_artifact(
    value: Any, label: str, *, descriptor: bool = False
) -> dict[str, Any]:
    keys = (
        {"path", "digest", "id", "required_cases"} if descriptor else {"path", "digest"}
    )
    if not isinstance(value, dict) or set(value) != keys:
        raise EvolutionError(f"{label} is invalid")
    path = _relative_path(value["path"], f"{label} path")
    digest = value["digest"]
    if not isinstance(digest, str) or not DIGEST_RE.fullmatch(digest):
        raise EvolutionError(f"{label} digest is invalid")
    result: dict[str, Any] = {"path": path, "digest": digest}
    if descriptor:
        actor = _nonempty(value["id"], f"{label} identity", 96)
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", actor):
            raise EvolutionError(f"{label} identity is invalid")
        result.update(
            {
                "id": actor,
                "required_cases": _string_list(
                    value["required_cases"], f"{label} required cases"
                ),
            }
        )
    return result


def _overlaps(left: str, right: str) -> bool:
    left = left.rstrip("/").casefold()
    right = right.rstrip("/").casefold()
    return left == right or left.startswith(f"{right}/") or right.startswith(f"{left}/")


def _output_roots(value: Any, protected: tuple[str, ...]) -> dict[str, str]:
    if not isinstance(value, dict) or set(value) != {"codex", "claude"}:
        raise EvolutionError("evolution outputs are invalid")
    outputs = {
        host: _relative_path(value[host], f"{host} output")
        for host in ("codex", "claude")
    }
    if _overlaps(outputs["codex"], outputs["claude"]) or any(
        _overlaps(output, boundary)
        for output in outputs.values()
        for boundary in protected
    ):
        raise EvolutionError("evolution output overlaps a protected path")
    return outputs


def _invocation(value: Any, label: str, *, metadata: bool) -> dict[str, Any]:
    keys = {
        "mode",
        "disable_model_invocation",
        "allow_implicit_invocation",
        "metadata",
        "metadata_digest",
    }
    invocation = _exact(value, keys, label)
    if (
        invocation["mode"] not in {"manual", "model"}
        or any(
            not isinstance(invocation[key], bool)
            for key in ("disable_model_invocation", "allow_implicit_invocation")
        )
        or (
            invocation["mode"] == "manual"
            and (
                not invocation["disable_model_invocation"]
                or invocation["allow_implicit_invocation"]
            )
        )
        or (
            invocation["mode"] == "model"
            and (
                invocation["disable_model_invocation"]
                or not invocation["allow_implicit_invocation"]
            )
        )
    ):
        raise EvolutionError(f"{label} semantics are invalid")
    raw_metadata = invocation["metadata"]
    if (
        not isinstance(raw_metadata, dict)
        or any(
            not isinstance(key, str)
            or not re.fullmatch(r"[a-z0-9_]{1,64}", key)
            or not isinstance(item, str)
            or not item
            or len(item.encode("utf-8")) > 16 * 1024
            for key, item in raw_metadata.items()
        )
        or len(raw_metadata) > 8
        or not isinstance(invocation["metadata_digest"], str)
        or invocation["metadata_digest"] != _digest(raw_metadata)
        or (invocation["mode"] == "model" and raw_metadata != {})
        or (invocation["mode"] == "manual" and set(raw_metadata) != {"openai_yaml"})
    ):
        raise EvolutionError(f"{label} metadata is invalid")
    if metadata and (
        not isinstance(invocation["metadata_digest"], str)
        or not DIGEST_RE.fullmatch(invocation["metadata_digest"])
    ):
        raise EvolutionError(f"{label} metadata is invalid")
    if invocation["mode"] == "manual":
        policy = invocation["metadata"]["openai_yaml"]
        matches = re.findall(
            r"(?mi)^\s*allow_implicit_invocation\s*:\s*(true|false)\s*(?:#.*)?$",
            policy,
        )
        if matches != ["false"]:
            raise EvolutionError(
                f"{label} manual metadata contradicts invocation policy"
            )
    return dict(invocation)


def _surface(value: Any) -> dict[str, Any]:
    surface = _exact(
        value,
        {
            "kind",
            "adapters",
            "external_system",
            "entrypoint",
            "hook",
            "loop",
        },
        "evolution surface",
    )
    if (
        surface["kind"] not in EVOLUTION_SURFACES
        or surface["adapters"] != SURFACE_ADAPTERS
        or not isinstance(surface["external_system"], bool)
        or surface["entrypoint"] != "harness-shared-cli"
        or (surface["kind"] == "mcp") != surface["external_system"]
        or (surface["kind"] != "hook" and surface["hook"] is not None)
        or (surface["kind"] != "loop" and surface["loop"] is not None)
    ):
        raise EvolutionError("evolution surface is invalid")
    if surface["kind"] == "hook":
        hook = surface["hook"]
        if (
            not isinstance(hook, dict)
            or set(hook) != {"origin", "phases", "observation_only", "canary_scope"}
            or hook["origin"] != "accepted-gap"
            or hook["phases"] != HOOK_PHASES
            or hook["observation_only"] is not True
            or hook["canary_scope"] != "active-worktree"
        ):
            raise EvolutionError("Hook surface policy is unsafe")
    if surface["kind"] == "loop":
        loop = surface["loop"]
        if (
            not isinstance(loop, dict)
            or set(loop)
            != {
                "origin",
                "max_attempts",
                "no_progress_limit",
                "yield_to_user",
                "adapter_switch_policy",
            }
            or loop["origin"] != "accepted-gap"
            or not isinstance(loop["max_attempts"], int)
            or isinstance(loop["max_attempts"], bool)
            or not 1 <= loop["max_attempts"] <= 3
            or not isinstance(loop["no_progress_limit"], int)
            or isinstance(loop["no_progress_limit"], bool)
            or not 1 <= loop["no_progress_limit"] < loop["max_attempts"]
            or loop["yield_to_user"] is not True
            or loop["adapter_switch_policy"] != "stop-and-report"
        ):
            raise EvolutionError("Loop surface policy is unsafe")
    return dict(surface)


def _surface_check_names(surface: dict[str, Any]) -> list[str]:
    kind = surface["kind"]
    if kind == "hook":
        return list(surface["hook"]["phases"])
    if kind == "loop":
        return [
            "bounded",
            "no-progress-stop",
            "yield-to-user",
            "no-adapter-switch",
        ]
    return ["discovery", "smoke"]


def _surface_runtime(
    surface: dict[str, Any], interface: dict[str, Any], name: str
) -> dict[str, Any]:
    action = {
        "mcp": "serve",
        "cli": "call",
        "hook": "hook-event",
        "loop": "loop-step",
    }[surface["kind"]]
    return {
        "schema": "harness.surface-runtime/v1",
        "kind": surface["kind"],
        "name": name,
        "interface": interface,
        "entrypoint": {
            "command": ["python", "-m", "harness", "capability", action],
            "adapter": "required",
            "cwd": "active-worktree",
        },
        "transport": "stdio-jsonrpc" if surface["kind"] == "mcp" else "typed-json",
    }


def loop_surface_step(value: Any, adapter: str) -> dict[str, Any]:
    """Evaluate one bounded Loop step without executing or switching adapters."""

    if adapter not in SURFACE_ADAPTERS:
        raise EvolutionError("surface adapter is invalid")
    request = _exact(
        value,
        {
            "schema",
            "policy",
            "frozen_adapter",
            "requested_adapter",
            "attempts",
            "current",
            "user_input",
        },
        "Loop step request",
    )
    if request["schema"] != "harness.loop-step/v1":
        raise EvolutionError("Loop step request is invalid")
    surface = _surface(
        {
            "kind": "loop",
            "adapters": list(SURFACE_ADAPTERS),
            "external_system": False,
            "entrypoint": "harness-shared-cli",
            "hook": None,
            "loop": request["policy"],
        }
    )
    policy = surface["loop"]
    if (
        request["frozen_adapter"] != adapter
        or request["requested_adapter"] not in SURFACE_ADAPTERS
        or not isinstance(request["user_input"], bool)
        or not isinstance(request["attempts"], list)
        or len(request["attempts"]) > policy["max_attempts"]
    ):
        raise EvolutionError("Loop step request is invalid")

    def attempt(value: Any) -> dict[str, str]:
        item = _exact(value, {"fingerprint", "evidence_digest"}, "Loop attempt")
        if not all(DIGEST_RE.fullmatch(str(item[key])) for key in item):
            raise EvolutionError("Loop attempt is invalid")
        return dict(item)

    attempts = [attempt(item) for item in request["attempts"]]
    current = attempt(request["current"])
    if request["user_input"]:
        action, reason = "yield-to-user", "new-user-input"
    elif request["requested_adapter"] != request["frozen_adapter"]:
        action, reason = "stop", "adapter-switch-prohibited"
    elif len(attempts) >= policy["max_attempts"]:
        action, reason = "stop", "attempt-limit"
    else:
        repeated = sum(item == current for item in attempts)
        if repeated >= policy["no_progress_limit"]:
            action, reason = "stop", "no-progress"
        else:
            action, reason = "continue", "new-evidence"
    material = {
        "adapter": adapter,
        "policy": policy,
        "attempts": attempts,
        "current": current,
        "user_input": request["user_input"],
        "action": action,
        "reason": reason,
    }
    return {
        "schema": "harness.loop-control/v1",
        "adapter": adapter,
        "action": action,
        "reason": reason,
        "next_attempt": len(attempts) + 1 if action == "continue" else None,
        "evidence_digest": _digest(material),
    }


def _validate_candidate(value: Any) -> dict[str, Any]:
    surface_candidate = isinstance(value, dict) and "surface" in value
    extra_keys = (
        {"surface", "artifact_format", "install", "package"}
        if surface_candidate
        else set()
    )
    candidate = _exact(
        value,
        {
            "id",
            "canonical_source",
            "immutable_revision",
            "artifact_path",
            "artifact_digest",
            "license",
            "license_path",
            "license_digest",
            "invocation",
            "permissions",
            "network",
            "data",
            "compatibility",
            "smoke",
            "rollback",
            "manifest",
            "effects",
            "installed",
        }
        | extra_keys,
        "evolution candidate",
    )
    candidate_id = _nonempty(candidate["id"], "candidate identity", 96)
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", candidate_id):
        raise EvolutionError("candidate identity is invalid")
    source = _nonempty(candidate["canonical_source"], "candidate source", 512)
    if not re.fullmatch(r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", source):
        raise EvolutionError("candidate source must be canonical GitHub HTTPS")
    revision = candidate["immutable_revision"]
    if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise EvolutionError("candidate revision must be immutable")
    artifact_path = _relative_path(
        candidate["artifact_path"], "candidate artifact path"
    )
    license_path = _relative_path(candidate["license_path"], "candidate license path")
    if artifact_path.casefold() == license_path.casefold():
        raise EvolutionError("candidate artifact and license must be independent")
    for key in ("artifact_digest", "license_digest"):
        if not isinstance(candidate[key], str) or not DIGEST_RE.fullmatch(
            candidate[key]
        ):
            raise EvolutionError(f"candidate {key.replace('_', ' ')} is invalid")
    if candidate["license"] not in LICENSES:
        raise EvolutionError("candidate license is not clear")
    invocation = _invocation(
        candidate["invocation"], "candidate invocation", metadata=True
    )
    permissions = candidate["permissions"]
    if (
        not isinstance(permissions, list)
        or not 1 <= len(permissions) <= 16
        or any(
            permission not in {"none", "read-repository", "write-capability-package"}
            for permission in permissions
        )
        or len(set(permissions)) != len(permissions)
    ):
        raise EvolutionError("candidate permissions are invalid")
    if candidate["network"] not in {"none", "read-only-https"}:
        raise EvolutionError("candidate network behavior is invalid")
    if candidate["data"] not in {
        "none",
        "repository-local-metadata",
        "repository-local-content",
    }:
        raise EvolutionError("candidate data behavior is invalid")
    compatibility = _exact(
        candidate["compatibility"],
        {"hosts", "status", "evidence_digest"},
        "candidate compatibility",
    )
    if (
        compatibility["hosts"]
        != (SURFACE_ADAPTERS if surface_candidate else ["codex", "claude"])
        or compatibility["status"] not in {"pass", "fail", "unverified"}
        or not isinstance(compatibility["evidence_digest"], str)
        or not DIGEST_RE.fullmatch(compatibility["evidence_digest"])
    ):
        raise EvolutionError("candidate compatibility is invalid")
    smoke = _exact(candidate["smoke"], {"status", "evidence_digest"}, "candidate smoke")
    if (
        smoke["status"] not in {"pass", "fail", "not-run"}
        or (
            smoke["status"] == "pass"
            and (
                not isinstance(smoke["evidence_digest"], str)
                or not DIGEST_RE.fullmatch(smoke["evidence_digest"])
            )
        )
        or (smoke["status"] != "pass" and smoke["evidence_digest"] is not None)
    ):
        raise EvolutionError("candidate smoke evidence is invalid")
    rollback = _exact(
        candidate["rollback"],
        {"scope", "method", "reversible"},
        "candidate rollback",
    )
    if (
        rollback["scope"] != "repository-local"
        or rollback["method"] != "git-head-snapshot"
        or not isinstance(rollback["reversible"], bool)
    ):
        raise EvolutionError("candidate rollback is invalid")
    candidate_manifest = _exact(
        candidate["manifest"],
        {
            "files",
            "total_bytes",
            "dependencies",
            "scripts",
            "resources",
            "executables",
            "symlinks",
            "submodules",
        },
        "candidate manifest",
    )
    manifest_files = candidate_manifest["files"]
    if (
        not isinstance(manifest_files, list)
        or not 1 <= len(manifest_files) <= 32
        or any(
            not isinstance(item, dict)
            or set(item) != {"path", "digest", "bytes", "mode"}
            or _relative_path(item["path"], "candidate manifest path") != item["path"]
            or not isinstance(item["digest"], str)
            or not DIGEST_RE.fullmatch(item["digest"])
            or not isinstance(item["bytes"], int)
            or not 0 <= item["bytes"] <= 256 * 1024
            or item["mode"] not in {"100644", "100755"}
            for item in manifest_files
        )
        or len({item["path"] for item in manifest_files}) != len(manifest_files)
        or not isinstance(candidate_manifest["total_bytes"], int)
        or candidate_manifest["total_bytes"]
        != sum(item["bytes"] for item in manifest_files)
        or candidate_manifest["total_bytes"] > 256 * 1024
        or any(
            candidate_manifest[key] != []
            for key in ("dependencies", "scripts", "resources")
        )
        or candidate_manifest["executables"] is not False
        or candidate_manifest["symlinks"] is not False
        or candidate_manifest["submodules"] is not False
    ):
        raise EvolutionError("candidate manifest is unsafe")
    manifest_by_path = {item["path"]: item for item in manifest_files}
    if (
        manifest_by_path.get(artifact_path, {}).get("digest")
        != candidate["artifact_digest"]
        or manifest_by_path.get(license_path, {}).get("digest")
        != candidate["license_digest"]
    ):
        raise EvolutionError("candidate source digests are not bound to its manifest")
    effect_keys = {"credentials", "elevation", "daemon", "open_port", "global_policy"}
    if surface_candidate:
        effect_keys |= {"global_mutation", "ssh", "publish"}
    effects = _exact(
        candidate["effects"],
        effect_keys,
        "candidate effects",
    )
    if any(not isinstance(value, bool) for value in effects.values()):
        raise EvolutionError("candidate effects are invalid")
    installed = _exact(
        candidate["installed"],
        {"artifact_digest", "provenance"},
        "installed candidate",
    )
    if (
        not isinstance(installed["artifact_digest"], str)
        or not DIGEST_RE.fullmatch(installed["artifact_digest"])
        or installed["provenance"] not in {"pinned", "unknown", "not-installed"}
    ):
        raise EvolutionError("installed candidate evidence is invalid")
    normalized = {
        **candidate,
        "id": candidate_id,
        "canonical_source": source,
        "artifact_path": artifact_path,
        "license_path": license_path,
        "invocation": invocation,
    }
    if surface_candidate:
        if candidate["artifact_format"] != "canonical-json":
            raise EvolutionError("surface candidate artifact format is invalid")
        install = _exact(
            candidate["install"],
            {"scope", "method", "uninstall"},
            "surface candidate install",
        )
        if install != {
            "scope": "repository-local",
            "method": "verified-copy",
            "uninstall": "git-head-snapshot",
        }:
            raise EvolutionError("surface candidate install is unsafe")
        package = _exact(
            candidate["package"], {"name", "version"}, "surface package coordinate"
        )
        package_name = _nonempty(package["name"], "surface package name", 214)
        package_version = _nonempty(package["version"], "surface package version", 64)
        npm_part = r"[a-z0-9][a-z0-9._-]*"
        if not re.fullmatch(
            rf"(?:{npm_part}|@{npm_part}/{npm_part})", package_name
        ) or not re.fullmatch(r"[0-9A-Za-z][0-9A-Za-z._+-]*", package_version):
            raise EvolutionError("surface package coordinate is invalid")
        normalized["package"] = {
            "name": package_name,
            "version": package_version,
        }
        normalized["surface"] = _surface(candidate["surface"])
    _safe_persisted_value(normalized)
    return normalized


def _auto_safety_blocks(
    candidate: dict[str, Any], verification: dict[str, Any] | None = None
) -> list[str]:
    blocks: list[str] = []
    trusted_surface = (
        candidate.get("artifact_format") == "canonical-json"
        and isinstance(verification, dict)
        and isinstance(verification.get("surface"), dict)
        and verification["surface"].get("kind")
        == candidate.get("surface", {}).get("kind")
        and verification["surface"].get("adapters") == SURFACE_ADAPTERS
    )
    if not trusted_surface:
        if candidate["compatibility"]["status"] != "pass":
            blocks.append("compatibility-not-passing")
        if candidate["smoke"]["status"] != "pass":
            blocks.append("smoke-not-passing")
        if candidate["installed"]["provenance"] != "pinned":
            blocks.append("installed-provenance-not-pinned")
        if candidate["installed"]["artifact_digest"] != candidate["artifact_digest"]:
            blocks.append("installed-artifact-mismatch")
    if not candidate["rollback"]["reversible"]:
        blocks.append("rollback-not-reversible")
    blocks.extend(
        f"effect-{effect}"
        for effect in sorted(candidate["effects"])
        if candidate["effects"][effect]
    )
    if candidate["network"] == "read-only-https" and candidate["data"] != "none":
        blocks.append("network-data-boundary")
    if set(candidate["permissions"]) - {"none", "read-repository"}:
        blocks.append("runtime-write-permission")
    # Legacy executable candidates still have no trusted machine evidence.
    # A v2 surface candidate is data-only canonical JSON: Search verifies its
    # exact immutable bytes and compiles every adapter projection before this
    # decision is made, so no untrusted executable is run.
    if not trusted_surface:
        blocks.append("trusted-machine-evidence-unavailable")
    return blocks


def _auto_safe(
    candidate: dict[str, Any], verification: dict[str, Any] | None = None
) -> bool:
    return not _auto_safety_blocks(candidate, verification)


def _fetch_https_bytes(
    url: str, label: str, *, allow_not_found: bool = False
) -> tuple[bytes, int]:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    request = urllib.request.Request(
        url, headers={"User-Agent": "bilibili-mcp-harness-evolution/1"}
    )
    try:
        with opener.open(request, timeout=20) as response:
            raw = response.read(256 * 1024 + 1)
            status = response.status
            if (
                status != 200
                and not (allow_not_found and status == 404)
                or response.geturl() != url
            ):
                raise EvolutionError(f"{label} redirected or failed")
    except urllib.error.HTTPError as exc:
        if not (allow_not_found and exc.code == 404 and exc.geturl() == url):
            raise EvolutionError(f"{label} could not be verified") from exc
        raw = exc.read(256 * 1024 + 1)
        status = 404
    except (OSError, urllib.error.URLError) as exc:
        raise EvolutionError(f"{label} could not be verified") from exc
    if len(raw) > 256 * 1024:
        raise EvolutionError(f"{label} exceeds its bound")
    return raw, status


def _channel_result(
    channel: str,
    raw: bytes,
    status: int,
    candidate: dict[str, Any],
) -> str:
    """Derive Search meaning from bounded source bytes, never caller labels."""

    if channel == "live-github":
        if status == 404:
            return "no-match"
        return (
            "candidate"
            if hashlib.sha256(raw).hexdigest() == candidate["artifact_digest"]
            else "rejected"
        )
    if channel == "official":
        try:
            text = raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise EvolutionError("official channel evidence is invalid") from exc
        markers = [candidate.get("id"), candidate.get("artifact_path")]
        return (
            "candidate"
            if any(marker and marker in text for marker in markers)
            else "no-match"
        )
    if channel == "package-manager" and status == 404:
        return "no-match"
    try:
        payload = json.loads(raw.decode("utf-8", errors="strict"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvolutionError(f"{channel} channel evidence is invalid") from exc
    if not isinstance(payload, dict):
        raise EvolutionError(f"{channel} channel evidence is invalid")
    if channel == "registry":
        servers = payload.get("servers")
        if not isinstance(servers, list) or len(servers) > 256:
            raise EvolutionError("registry channel evidence is invalid")
        matches = []
        for item in servers:
            if not isinstance(item, dict):
                raise EvolutionError("registry channel evidence is invalid")
            server = item.get("server", item)
            if not isinstance(server, dict):
                raise EvolutionError("registry channel evidence is invalid")
            repository = server.get("repository")
            repository_url = (
                repository.get("url") if isinstance(repository, dict) else repository
            )
            if (
                (candidate.get("id") is not None and (
                    server.get("name") == candidate["id"]
                    or server.get("id") == candidate["id"]
                ))
                or repository_url == candidate.get("canonical_source")
            ):
                matches.append(server)
        if not matches:
            return "no-match"
        for match in matches:
            repository = match.get("repository")
            repository_url = (
                repository.get("url") if isinstance(repository, dict) else repository
            )
            if repository_url == candidate["canonical_source"]:
                return "candidate"
        return "rejected"
    if "error" in payload:
        return "rejected"
    repository = payload.get("repository")
    repository_url = (
        repository.get("url") if isinstance(repository, dict) else repository
    )
    if isinstance(repository_url, str):
        repository_url = repository_url.removeprefix("git+").removesuffix(".git")
    dist = payload.get("dist")
    package = candidate.get("package")
    if not isinstance(package, dict):
        return "rejected"
    expected_version = package["version"]
    return (
        "candidate"
        if payload.get("name") == package["name"]
        and payload.get("version") == expected_version
        and payload.get("license") == candidate["license"]
        and repository_url == candidate["canonical_source"]
        and isinstance(dist, dict)
        and isinstance(dist.get("integrity"), str)
        and dist["integrity"].startswith("sha512-")
        else "rejected"
    )


def _verify_search_channels(
    search: dict[str, Any], candidate: dict[str, Any] | None
) -> dict[str, Any]:
    if search.get("schema") != "harness.evolution-search/v2":
        raise EvolutionError("surface candidate requires v2 Search evidence")
    observations: dict[str, Any] = {}
    for source in search["sources_consulted"]:
        raw, status = _fetch_https_bytes(
            source["evidence_url"],
            "surface channel evidence",
            allow_not_found=(
                source["result"] == "no-match"
                and source["channel"] in {"package-manager", "live-github"}
            ),
        )
        digest = hashlib.sha256(raw).hexdigest()
        if digest != source["evidence_digest"] or len(raw) != source["evidence_bytes"]:
            raise EvolutionError("surface channel evidence does not match its record")
        result = _channel_result(source["channel"], raw, status, candidate or source)
        if result != source["result"]:
            raise EvolutionError("surface channel result does not match its response")
        observations[source["channel"]] = {
            "url": source["evidence_url"],
            "digest": digest,
            "bytes": len(raw),
            "status": status,
            "result": result,
        }
    if set(observations) != set(SEARCH_CHANNELS):
        raise EvolutionError("surface channel evidence is incomplete")
    return observations


def _verify_pinned_candidate(
    candidate: dict[str, Any], search: dict[str, Any] | None = None
) -> dict[str, Any]:
    repository = candidate["canonical_source"].removeprefix("https://github.com/")
    observations: dict[str, Any] = {}
    artifact_raw: bytes | None = None
    manifest = {item["path"]: item for item in candidate["manifest"]["files"]}
    for label, path_key, digest_key in (
        ("artifact", "artifact_path", "artifact_digest"),
        ("license", "license_path", "license_digest"),
    ):
        relative = candidate[path_key]
        quoted = "/".join(
            urllib.parse.quote(part, safe="._-")
            for part in PurePosixPath(relative).parts
        )
        url = (
            f"https://raw.githubusercontent.com/{repository}/"
            f"{candidate['immutable_revision']}/{quoted}"
        )
        raw, status = _fetch_https_bytes(url, "pinned candidate source")
        if status != 200:
            raise EvolutionError("pinned candidate source could not be verified")
        observed = hashlib.sha256(raw).hexdigest()
        if (
            observed != candidate[digest_key]
            or manifest[relative]["digest"] != observed
            or manifest[relative]["bytes"] != len(raw)
        ):
            raise EvolutionError("pinned candidate source does not match its record")
        observations[label] = {
            "path": relative,
            "digest": observed,
            "bytes": len(raw),
        }
        if label == "artifact":
            artifact_raw = raw
        if label == "license":
            try:
                license_text = raw.decode("utf-8", errors="strict")
            except UnicodeDecodeError as exc:
                raise EvolutionError("candidate license text is invalid") from exc
            if not all(
                marker.casefold() in license_text.casefold()
                for marker in LICENSE_MARKERS[candidate["license"]]
            ):
                raise EvolutionError(
                    "candidate license bytes do not match the declared license"
                )
    surface_evidence = None
    if candidate.get("artifact_format") == "canonical-json":
        try:
            source = json.loads((artifact_raw or b"").decode("utf-8", errors="strict"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise EvolutionError(
                "surface candidate artifact is not canonical JSON"
            ) from exc
        if (
            not isinstance(source, dict)
            or source.get("schema") != "harness.evolution-capability/v2"
            or source.get("surface") != candidate.get("surface")
            or source.get("license") != candidate["license"]
            or source.get("skill", {}).get("invocation") != candidate["invocation"]
            or (_canonical_text(source) + "\n").encode("utf-8") != artifact_raw
        ):
            raise EvolutionError("surface candidate artifact is not canonical")
        packages = {
            host: compile_evolution_capability(source, host)
            for host in ("codex", "claude")
        }
        surface_evidence = {
            "kind": candidate["surface"]["kind"],
            "adapters": list(candidate["surface"]["adapters"]),
            "source_digest": _digest(source),
            "projection_digests": {
                "codex-direct": _digest(packages["codex"]),
                "claude-direct": _digest(packages["claude"]),
                "codex-paseo-claude": _digest(
                    {
                        "codex": packages["codex"],
                        "claude": packages["claude"],
                    }
                ),
            },
            "channels": _verify_search_channels(search or {}, candidate),
        }
    material = {
        "source": candidate["canonical_source"],
        "revision": candidate["immutable_revision"],
        "observations": observations,
    }
    if surface_evidence is not None:
        material["surface"] = surface_evidence
    return {
        "schema": "harness.evolution-source-verification/v1",
        **material,
        "evidence_digest": _digest(material),
    }


def _authorization(
    candidate: dict[str, Any], verification: dict[str, Any] | None = None
) -> dict[str, Any]:
    candidate_digest = _digest(candidate)
    return {
        "schema": "harness.evolution-authorization/v1",
        "request_id": f"evolution-auth-{candidate_digest[:24]}",
        "candidate_id": candidate["id"],
        "candidate_digest": candidate_digest,
        "blocks": _auto_safety_blocks(candidate, verification),
        "alternatives": ["defer", "build-repository-local"],
    }


def _validate_search(value: Any) -> dict[str, Any]:
    surface_search = (
        isinstance(value, dict) and value.get("schema") == "harness.evolution-search/v2"
    )
    search = _exact(
        value,
        {
            "schema",
            "query",
            "installed_catalog",
            "sources_consulted",
            "candidates",
            "decision",
            "selected_candidate",
            "reason_code",
        }
        | ({"channels"} if surface_search else set()),
        "evolution search",
    )
    if search["schema"] not in {
        "harness.evolution-search/v1",
        "harness.evolution-search/v2",
    }:
        raise EvolutionError("evolution search schema is unsupported")
    if surface_search and search["channels"] != SEARCH_CHANNELS:
        raise EvolutionError("surface Evolution Search channels are incomplete")
    query = _nonempty(search["query"], "evolution search query", 256)
    installed = _exact(
        search["installed_catalog"],
        {"host", "route", "route_digest", "status", "cli"},
        "installed capability catalog",
    )
    if (
        installed["host"] not in {"codex", "claude"}
        or installed["route"] != "find-skills"
        or not isinstance(installed["route_digest"], str)
        or not DIGEST_RE.fullmatch(installed["route_digest"])
        or installed["status"] not in {"available", "unavailable"}
        or installed["cli"] not in {"present", "absent"}
    ):
        raise EvolutionError("installed capability catalog is invalid")
    raw_candidates = search["candidates"]
    if not isinstance(raw_candidates, list) or len(raw_candidates) > 32:
        raise EvolutionError("evolution search candidates are invalid")
    candidates = [_validate_candidate(candidate) for candidate in raw_candidates]
    if len({candidate["id"] for candidate in candidates}) != len(candidates):
        raise EvolutionError("evolution candidate identities are duplicated")
    if any("surface" in candidate for candidate in candidates) and not surface_search:
        raise EvolutionError("surface candidate requires v2 Search evidence")
    raw_sources = search["sources_consulted"]
    if not isinstance(raw_sources, list) or not 1 <= len(raw_sources) <= 32:
        raise EvolutionError(
            "Evolution Search requires official or live GitHub evidence"
        )
    sources: list[dict[str, Any]] = []
    for raw_source in raw_sources:
        source_keys = {
            "canonical_source",
            "immutable_revision",
            "artifact_path",
            "artifact_digest",
            "license_path",
            "license_digest",
            "result",
        } | (
            {"channel", "evidence_url", "evidence_digest", "evidence_bytes"}
            if surface_search
            else set()
        )
        item = _exact(
            raw_source,
            source_keys,
            "evolution source evidence",
        )
        source = {
            "canonical_source": _nonempty(
                item["canonical_source"], "evolution source", 512
            ),
            "immutable_revision": item["immutable_revision"],
            "artifact_path": _relative_path(
                item["artifact_path"], "evolution source artifact"
            ),
            "artifact_digest": item["artifact_digest"],
            "license_path": _relative_path(
                item["license_path"], "evolution source license"
            ),
            "license_digest": item["license_digest"],
            "result": item["result"],
        }
        if surface_search:
            source.update(
                {
                    "channel": item["channel"],
                    "evidence_url": item["evidence_url"],
                    "evidence_digest": item["evidence_digest"],
                    "evidence_bytes": item["evidence_bytes"],
                }
            )
            parsed_evidence = urllib.parse.urlsplit(str(source["evidence_url"]))
        if (
            not re.fullmatch(
                r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+",
                source["canonical_source"],
            )
            or not re.fullmatch(r"[0-9a-f]{40}", str(source["immutable_revision"]))
            or not DIGEST_RE.fullmatch(str(source["artifact_digest"]))
            or not DIGEST_RE.fullmatch(str(source["license_digest"]))
            or source["result"] not in {"candidate", "no-match", "rejected"}
            or (surface_search and source["channel"] not in SEARCH_CHANNELS)
            or (
                surface_search
                and (
                    parsed_evidence.scheme != "https"
                    or parsed_evidence.username is not None
                    or parsed_evidence.password is not None
                    or parsed_evidence.port not in {None, 443}
                    or parsed_evidence.hostname
                    not in SEARCH_CHANNEL_HOSTS[source["channel"]]
                    or bool(parsed_evidence.fragment)
                    or not DIGEST_RE.fullmatch(str(source["evidence_digest"]))
                    or not isinstance(source["evidence_bytes"], int)
                    or not 1 <= source["evidence_bytes"] <= 256 * 1024
                )
            )
        ):
            raise EvolutionError("evolution source evidence is invalid")
        sources.append(source)
    if len({_digest(item) for item in sources}) != len(sources):
        raise EvolutionError("evolution source evidence is duplicated")
    if surface_search and sorted(item["channel"] for item in sources) != sorted(
        SEARCH_CHANNELS
    ):
        raise EvolutionError("surface Evolution Search channels are incomplete")
    for candidate in candidates:
        if not any(
            source["result"] == "candidate"
            and (not surface_search or source["channel"] == "live-github")
            and all(
                source[key] == candidate[key]
                for key in (
                    "canonical_source",
                    "immutable_revision",
                    "artifact_path",
                    "artifact_digest",
                    "license_path",
                    "license_digest",
                )
            )
            for source in sources
        ):
            raise EvolutionError("candidate is not bound to live source evidence")
    decision = search["decision"]
    if decision not in {"adapt", "build", "deferred"}:
        raise EvolutionError("evolution search decision is invalid")
    selected = search["selected_candidate"]
    candidate_ids = {candidate["id"] for candidate in candidates}
    zero_candidate_build = (
        decision == "build"
        and not candidates
        and selected is None
        and all(source["result"] == "no-match" for source in sources)
    )
    if not zero_candidate_build and selected not in candidate_ids:
        raise EvolutionError("evolution selected candidate is invalid")
    if surface_search:
        channel_sources = {item["channel"]: item for item in sources}
        candidate = (
            next(item for item in candidates if item["id"] == selected)
            if not zero_candidate_build
            else None
        )
        reference = candidate or channel_sources["live-github"]
        source_keys = (
            "canonical_source",
            "immutable_revision",
            "artifact_path",
            "artifact_digest",
            "license_path",
            "license_digest",
        )
        if zero_candidate_build and any(
            any(source[key] != reference[key] for key in source_keys)
            for source in sources
        ):
            raise EvolutionError("surface channel evidence is not query-bound")
        repository = reference["canonical_source"].removeprefix(
            "https://github.com/"
        )
        raw_prefix = (
            f"https://raw.githubusercontent.com/{repository}/"
            f"{reference['immutable_revision']}/"
        )
        artifact_suffix = "/".join(
            urllib.parse.quote(part, safe="._-")
            for part in PurePosixPath(reference["artifact_path"]).parts
        )
        registry_query = urllib.parse.parse_qs(
            urllib.parse.urlsplit(channel_sources["registry"]["evidence_url"]).query
        )
        package_path = urllib.parse.urlsplit(
            channel_sources["package-manager"]["evidence_url"]
        ).path
        if candidate is None:
            registry_coordinate = query
            package_prefix = "/" + urllib.parse.quote(query, safe="")
            package_bound = package_path == package_prefix
        else:
            registry_coordinate = candidate["id"]
            package_coordinate = candidate["package"]
            package_bound = package_path == (
                "/"
                + urllib.parse.quote(package_coordinate["name"], safe="")
                + "/"
                + urllib.parse.quote(package_coordinate["version"], safe="")
            )
        if (
            not channel_sources["official"]["evidence_url"].startswith(raw_prefix)
            or channel_sources["live-github"]["evidence_url"]
            != raw_prefix + artifact_suffix
            or registry_query.get("search") != [registry_coordinate]
            or not package_bound
        ):
            boundary = "query" if candidate is None else "candidate"
            raise EvolutionError(f"surface channel evidence is not {boundary}-bound")
    reason = _nonempty(search["reason_code"], "evolution search reason", 96)
    if not re.fullmatch(r"[a-z0-9-]+", reason):
        raise EvolutionError("evolution search reason is invalid")
    normalized = {
        "schema": search["schema"],
        "query_digest": hashlib.sha256(query.encode("utf-8")).hexdigest(),
        "installed_catalog": installed,
        "sources_consulted": sources,
        "candidates": candidates,
        "decision": decision,
        "selected_candidate": selected,
        "reason_code": reason,
    }
    if surface_search:
        normalized["channels"] = list(SEARCH_CHANNELS)
    _safe_persisted_value(normalized)
    return normalized


def _validate_stored_search(value: Any) -> dict[str, Any]:
    surface_search = (
        isinstance(value, dict) and value.get("schema") == "harness.evolution-search/v2"
    )
    search = _exact(
        value,
        {
            "schema",
            "query_digest",
            "installed_catalog",
            "sources_consulted",
            "candidates",
            "decision",
            "selected_candidate",
            "reason_code",
        }
        | ({"channels"} if surface_search else set()),
        "stored evolution search",
    )
    if (
        search["schema"]
        not in {"harness.evolution-search/v1", "harness.evolution-search/v2"}
        or not isinstance(search["query_digest"], str)
        or not DIGEST_RE.fullmatch(search["query_digest"])
        or (surface_search and search["channels"] != SEARCH_CHANNELS)
    ):
        raise EvolutionError("stored evolution search is invalid")
    installed = _exact(
        search["installed_catalog"],
        {"host", "route", "route_digest", "status", "cli"},
        "stored capability catalog",
    )
    if (
        installed["host"] not in {"codex", "claude"}
        or installed["route"] != "find-skills"
        or not isinstance(installed["route_digest"], str)
        or not DIGEST_RE.fullmatch(installed["route_digest"])
        or installed["status"] not in {"available", "unavailable"}
        or installed["cli"] not in {"present", "absent"}
    ):
        raise EvolutionError("stored capability catalog is invalid")
    raw_candidates = search["candidates"]
    if not isinstance(raw_candidates, list) or len(raw_candidates) > 32:
        raise EvolutionError("stored evolution candidates are invalid")
    candidates = [_validate_candidate(candidate) for candidate in raw_candidates]
    if len({candidate["id"] for candidate in candidates}) != len(candidates):
        raise EvolutionError("stored evolution candidates are duplicated")
    decision = search["decision"]
    selected = search["selected_candidate"]
    candidate_ids = {candidate["id"] for candidate in candidates}
    zero_candidate_build = decision == "build" and not candidates and selected is None
    if decision not in {"adapt", "build", "deferred"} or (
        not zero_candidate_build and selected not in candidate_ids
    ):
        raise EvolutionError("stored evolution decision is invalid")
    if not isinstance(search["reason_code"], str) or not re.fullmatch(
        r"[a-z0-9-]{1,96}", search["reason_code"]
    ):
        raise EvolutionError("stored evolution reason is invalid")
    probe_query = "stored-search"
    if surface_search and zero_candidate_build:
        channel_sources = {
            item.get("channel"): item
            for item in search["sources_consulted"]
            if isinstance(item, dict)
        }
        registry = channel_sources.get("registry", {})
        registry_query = urllib.parse.parse_qs(
            urllib.parse.urlsplit(str(registry.get("evidence_url", ""))).query
        ).get("search")
        if (
            not isinstance(registry_query, list)
            or len(registry_query) != 1
            or hashlib.sha256(registry_query[0].encode("utf-8")).hexdigest()
            != search["query_digest"]
        ):
            raise EvolutionError("stored evolution search is invalid")
        probe_query = registry_query[0]
    query_probe = {
        "schema": search["schema"],
        "query": probe_query,
        "installed_catalog": installed,
        "sources_consulted": search["sources_consulted"],
        "candidates": candidates,
        "decision": decision,
        "selected_candidate": selected,
        "reason_code": search["reason_code"],
    }
    if surface_search:
        query_probe["channels"] = list(SEARCH_CHANNELS)
    normalized_sources = _validate_search(query_probe)["sources_consulted"]
    normalized = {
        **search,
        "installed_catalog": installed,
        "sources_consulted": normalized_sources,
        "candidates": candidates,
    }
    return normalized


def _installed_catalog_evidence(mode: str) -> dict[str, str]:
    host = "codex" if mode == "codex-direct" else "claude"
    if host == "codex":
        raw_home = os.environ.get("CODEX_HOME")
        home = Path(raw_home) if raw_home else Path.home() / ".codex"
    else:
        raw_home = os.environ.get("CLAUDE_CONFIG_DIR")
        home = Path(raw_home) if raw_home else Path.home() / ".claude"
    target = home / "skills" / "find-skills" / "SKILL.md"
    try:
        ensure_no_link_components(home, target)
        raw = read_bounded_bytes(target, 64 * 1024)
        if raw is not None and target.stat().st_nlink == 1:
            status = "available"
            route_digest = hashlib.sha256(raw).hexdigest()
        else:
            status = "unavailable"
            route_digest = hashlib.sha256(b"find-skills-unavailable").hexdigest()
    except OSError:
        status = "unavailable"
        route_digest = hashlib.sha256(b"find-skills-unavailable").hexdigest()
    return {
        "host": host,
        "route": "find-skills",
        "route_digest": route_digest,
        "status": status,
        "cli": "present" if shutil.which("skills") else "absent",
    }


def _string_list(value: Any, label: str, *, limit: int = 16) -> list[str]:
    if (
        not isinstance(value, list)
        or not 1 <= len(value) <= limit
        or any(
            not isinstance(item, str) or _nonempty(item, label, 256) != item
            for item in value
        )
        or len(set(value)) != len(value)
    ):
        raise EvolutionError(f"{label} is invalid")
    return list(value)


def _safe_capability_text(values: list[str]) -> None:
    command_patterns = (
        r"(?i)\b(?:run|execute|invoke)\s+(?:bash|cmd|curl|gh|git|node|npm|npx|pip|powershell|pwsh|python|rm|sh|sudo|wget)\b",
        r"(?i)\binvoke-webrequest\b",
        r"(?i)(?:^|[\\/])\.env(?:\.|$)|\bignore\s+(?:the\s+)?(?:parent|scope|instructions?)\b",
    )
    if any(
        pattern.search(value) for value in values for pattern in FORBIDDEN_TEXT
    ) or any(
        re.search(pattern, value) for value in values for pattern in command_patterns
    ):
        raise EvolutionError("canonical capability contains unsafe operational content")


def _persisted_strings(value: Any) -> list[str]:
    pending = [value]
    strings: list[str] = []
    while pending:
        item = pending.pop()
        if isinstance(item, str):
            strings.append(item)
        elif isinstance(item, dict):
            pending.extend(item.values())
        elif isinstance(item, list):
            pending.extend(item)
    return strings


def _safe_persisted_value(value: Any) -> None:
    strings = _persisted_strings(value)
    text = "\n".join(strings)
    if any(pattern.search(text) for pattern in SECRET_TEXT):
        raise EvolutionError("evolution metadata contains secret-like content")


def compile_evolution_capability(source: dict[str, Any], host: str) -> dict[str, str]:
    """Compile one bounded Skill and Agent package from canonical source."""

    surface_capability = (
        isinstance(source, dict)
        and source.get("schema") == "harness.evolution-capability/v2"
    )
    canonical = _exact(
        source,
        {
            "schema",
            "name",
            "version",
            "owner",
            "description",
            "license",
            "adapted_from",
            "skill",
            "agent",
            "manifest",
            "governance",
            "trust",
            "packaging",
            "evaluation",
        }
        | ({"surface"} if surface_capability else set()),
        "canonical evolution capability",
    )
    if canonical["schema"] not in {
        "harness.evolution-capability/v1",
        "harness.evolution-capability/v2",
    }:
        raise EvolutionError("canonical capability schema is unsupported")
    surface = _surface(canonical["surface"]) if surface_capability else None
    name = _nonempty(canonical["name"], "capability name", 64)
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", name):
        raise EvolutionError("capability name is invalid")
    version = _nonempty(canonical["version"], "capability version", 32)
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise EvolutionError("capability version is invalid")
    owner = _nonempty(canonical["owner"], "capability owner", 128)
    description = _nonempty(canonical["description"], "capability description", 256)
    if canonical["license"] not in LICENSES:
        raise EvolutionError("canonical capability license is not clear")
    if canonical["adapted_from"] is not None:
        adapted_keys = (
            {"source", "revision"}
            if surface_capability
            else {
                "candidate_id",
                "candidate_digest",
                "source",
                "revision",
                "artifact_digest",
            }
        )
        adapted = _exact(
            canonical["adapted_from"], adapted_keys, "adapted capability source"
        )
        if (
            not re.fullmatch(
                r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+",
                str(adapted["source"]),
            )
            or not re.fullmatch(r"[0-9a-f]{40}", str(adapted["revision"]))
            or (
                not surface_capability
                and (
                    not re.fullmatch(
                        r"[A-Za-z0-9_.-]{1,96}", str(adapted["candidate_id"])
                    )
                    or not re.fullmatch(
                        r"[0-9a-f]{64}", str(adapted["candidate_digest"])
                    )
                    or not re.fullmatch(
                        r"[0-9a-f]{64}", str(adapted["artifact_digest"])
                    )
                )
            )
        ):
            raise EvolutionError("adapted capability source is invalid")

    skill = _exact(
        canonical["skill"],
        {"invocation", "triggers", "body", "interface"},
        "canonical Skill",
    )
    invocation = _invocation(skill["invocation"], "Skill invocation", metadata=False)
    triggers = _exact(
        skill["triggers"],
        {"positive", "negative", "near_neighbor_conflicts"},
        "Skill triggers",
    )
    positives = _string_list(triggers["positive"], "positive Skill triggers")
    negatives = _string_list(triggers["negative"], "negative Skill triggers")
    neighbors = _string_list(
        triggers["near_neighbor_conflicts"], "near-neighbor Skill conflicts"
    )
    body = _string_list(skill["body"], "Skill body", limit=64)
    interface = _exact(
        skill["interface"],
        {"schema", "name", "version", "operations"},
        "capability interface",
    )
    if (
        interface["schema"] != "harness.capability-interface/v1"
        or interface["name"] != name
        or interface["version"] != version
    ):
        raise EvolutionError("capability interface is inconsistent")
    operations = _string_list(interface["operations"], "capability operations")
    if (
        surface is not None
        and surface["kind"] in {"mcp", "cli"}
        and operations
        != [
            "inspect",
            "report",
        ]
    ):
        raise EvolutionError("surface capability operations have no trusted handler")

    agent = _exact(
        canonical["agent"],
        {
            "description",
            "instructions",
            "access",
            "writer_lease_required",
            "max_children",
            "capabilities",
        },
        "canonical Agent",
    )
    agent_description = _nonempty(agent["description"], "Agent description", 256)
    instructions = _string_list(agent["instructions"], "Agent instructions", limit=32)
    capabilities = _string_list(agent["capabilities"], "Agent capabilities")
    if (
        agent["access"] != "read-only"
        or agent["writer_lease_required"] is not True
        or agent["max_children"] != 0
        or set(capabilities) - {"read", "inspect", "report"}
    ):
        raise EvolutionError("Agent authority is not bounded")
    manifest = _exact(
        canonical["manifest"],
        {
            "max_files",
            "max_bytes",
            "dependencies",
            "scripts",
            "resources",
            "executables",
        },
        "canonical manifest",
    )
    if (
        not isinstance(manifest["max_files"], int)
        or not 6 <= manifest["max_files"] <= 32
        or not isinstance(manifest["max_bytes"], int)
        or not 4096 <= manifest["max_bytes"] <= 256 * 1024
        or manifest["dependencies"] != []
        or manifest["scripts"] != []
        or manifest["resources"] != []
        or manifest["executables"] is not False
    ):
        raise EvolutionError("canonical manifest is unsafe")
    governance = _exact(
        canonical["governance"],
        {"kernel", "evaluator", "holdout", "self_approval", "writer_lease_required"},
        "capability governance",
    )
    if governance != {
        "kernel": "immutable",
        "evaluator": "immutable",
        "holdout": "immutable",
        "self_approval": False,
        "writer_lease_required": True,
    }:
        raise EvolutionError("capability governance is unsafe")
    trust = _exact(
        canonical["trust"],
        {
            "source",
            "network",
            "data",
            "credentials",
            "elevation",
            "daemon",
            "open_port",
            "global_policy",
        },
        "capability trust",
    )
    if (
        trust["source"] not in {"repository-local-build", "pinned-adaptation"}
        or trust["network"] != "none"
        or trust["data"] not in {"none", "repository-local-metadata"}
        or trust["credentials"] != "none"
        or any(
            trust[key] is not False
            for key in ("elevation", "daemon", "open_port", "global_policy")
        )
    ):
        raise EvolutionError("capability trust is unsafe")
    packaging = _exact(
        canonical["packaging"],
        {"scope", "reversible", "hosts"},
        "capability packaging",
    )
    if packaging != {
        "scope": "repository-local",
        "reversible": True,
        "hosts": ["codex", "claude"],
    }:
        raise EvolutionError("capability packaging is unsafe")
    evaluation = _exact(
        canonical["evaluation"],
        {"schema", "name", "interface_version", "suite", "required_cases"},
        "capability evaluation",
    )
    if (
        evaluation["schema"] != "harness.capability-evaluation/v1"
        or evaluation["name"] != name
        or evaluation["interface_version"] != version
        or evaluation["suite"] != "declarative-discovery"
    ):
        raise EvolutionError("capability evaluation is inconsistent")
    _string_list(evaluation["required_cases"], "capability evaluation cases")
    if host not in {"codex", "claude"}:
        raise EvolutionError("capability host is invalid")
    if trust["source"] == "repository-local-build" and (
        invocation["mode"] != "manual"
        or body != SAFE_BUILD_BODY
        or instructions != SAFE_BUILD_AGENT_INSTRUCTIONS
        or interface["operations"] != ["inspect", "report"]
    ):
        raise EvolutionError("repository-local Build source is not the safe template")

    header = [
        "---",
        f"name: {name}",
        f"description: {json.dumps(description, ensure_ascii=True)}",
    ]
    if invocation["disable_model_invocation"] and host == "claude":
        header.append("disable-model-invocation: true")
    skill_text = "\n".join(
        [
            *header,
            "---",
            "",
            f"# {name}",
            "",
            "## Trigger positives",
            *(f"- {item}" for item in positives),
            "",
            "## Trigger negatives",
            *(f"- {item}" for item in negatives),
            "",
            "## Near-neighbor conflicts",
            *(f"- {item}" for item in neighbors),
            "",
            "## Workflow",
            *(f"- {item}" for item in body),
            "",
        ]
    )
    skill_root = f"skills/{name}"
    files = {
        f"{skill_root}/SKILL.md": skill_text,
        f"{skill_root}/interface.json": json.dumps(
            interface, ensure_ascii=True, sort_keys=True, indent=2, allow_nan=False
        )
        + "\n",
        f"{skill_root}/governance.json": json.dumps(
            governance, ensure_ascii=True, sort_keys=True, indent=2, allow_nan=False
        )
        + "\n",
        f"{skill_root}/trust.json": json.dumps(
            trust, ensure_ascii=True, sort_keys=True, indent=2, allow_nan=False
        )
        + "\n",
        f"{skill_root}/packaging.json": json.dumps(
            packaging, ensure_ascii=True, sort_keys=True, indent=2, allow_nan=False
        )
        + "\n",
        f"{skill_root}/evaluation.json": json.dumps(
            evaluation, ensure_ascii=True, sort_keys=True, indent=2, allow_nan=False
        )
        + "\n",
    }
    if surface is not None:
        files[f"{skill_root}/surface.json"] = (
            json.dumps(
                _surface_runtime(surface, interface, name),
                ensure_ascii=True,
                sort_keys=True,
                indent=2,
                allow_nan=False,
            )
            + "\n"
        )
    if invocation["mode"] == "manual" and host == "codex":
        manual_metadata = invocation["metadata"].get("openai_yaml")
        if not isinstance(manual_metadata, str):
            raise EvolutionError("manual Skill metadata is unavailable")
        files[f"{skill_root}/agents/openai.yaml"] = manual_metadata
    joined_instructions = "\n".join(f"- {item}" for item in instructions)
    if host == "codex":
        agent_path = f"agents/{name}.toml"
        files[agent_path] = "\n".join(
            [
                f"name = {json.dumps(name)}",
                f"description = {json.dumps(agent_description)}",
                'sandbox_mode = "read-only"',
                f"developer_instructions = {json.dumps(chr(10).join(instructions), ensure_ascii=True)}",
                "",
                "[agents]",
                "enabled = false",
                "",
            ]
        )
    else:
        agent_path = f"agents/{name}.md"
        files[agent_path] = "\n".join(
            [
                "---",
                f"name: {name}",
                f"description: {json.dumps(agent_description, ensure_ascii=True)}",
                "tools: Read, Grep, Glob",
                "---",
                "",
                f"# {name}",
                "",
                joined_instructions,
                "",
                "Writer lease required for any write: true",
                "Maximum children: 0",
                "",
            ]
        )
    # Scan the complete canonical payload so newly projected string fields cannot
    # bypass the credential and operational-content boundary.
    _safe_capability_text(_persisted_strings(canonical))
    try:
        return compile_host_package(
            name=name,
            version=version,
            owner=owner,
            host=host,
            source_label="canonical.json",
            source_digest=_digest(canonical),
            files=files,
            max_files=manifest["max_files"],
            max_bytes=manifest["max_bytes"],
            extended_manifest=True,
        )
    except MemoryProjectionError as exc:
        raise EvolutionError(str(exc)) from exc


def verify_evolution_projection(
    source: dict[str, Any], host: str, root: Path
) -> dict[str, Any]:
    """Verify exact files and bytes for one compiled host projection."""

    expected = compile_evolution_capability(source, host)
    if not root.is_dir() or root.is_symlink():
        raise EvolutionError("capability projection drift detected")
    ensure_no_link_components(root, root)
    entries = list(root.rglob("*"))
    if len(entries) > 64:
        raise EvolutionError("capability projection drift detected")
    actual: dict[str, bytes] = {}
    for path in entries:
        ensure_no_link_components(root, path)
        if path.is_dir():
            continue
        raw = read_bounded_bytes(path, 256 * 1024)
        if raw is None:
            raise EvolutionError("capability projection drift detected")
        actual[path.relative_to(root).as_posix()] = raw
    if set(actual) != set(expected) or any(
        actual[path] != content.encode("utf-8") for path, content in expected.items()
    ):
        raise EvolutionError("capability projection drift detected")
    _verify_host_conformance(source, host, root)
    material = {
        path: hashlib.sha256(raw).hexdigest() for path, raw in sorted(actual.items())
    }
    return {
        "schema": "harness.evolution-projection-check/v1",
        "host": host,
        "status": "pass",
        "projection_digest": _digest(material),
        "file_count": len(actual),
    }


def _surface_canonical(context: WorktreeContext, name: str) -> dict[str, Any] | None:
    raw = _read_single_link_file(
        context, f"harness/capability-packages/{name}/canonical.json"
    )
    try:
        canonical = json.loads(raw) if raw is not None else None
    except (UnicodeDecodeError, json.JSONDecodeError):
        canonical = None
    if not isinstance(canonical, dict):
        raise EvolutionError("surface capability canonical source is unsafe")
    if canonical.get("schema") != "harness.evolution-capability/v2":
        return None
    if canonical.get("name") != name or raw != (
        _canonical_text(canonical) + "\n"
    ).encode("utf-8"):
        raise EvolutionError("surface capability canonical source is inconsistent")
    return canonical


def discover_surface_capabilities(
    context: WorktreeContext, adapter: str
) -> dict[str, Any]:
    """Discover exact repository-local v2 packages for one execution adapter."""

    if adapter not in SURFACE_ADAPTERS:
        raise EvolutionError("surface adapter is invalid")
    package_root = context.root / "harness/capability-packages"
    ensure_no_link_components(context.root, package_root)
    hosts = {
        "codex-direct": ("codex",),
        "claude-direct": ("claude",),
        "codex-paseo-claude": ("codex", "claude"),
    }[adapter]
    capabilities: list[dict[str, Any]] = []
    if package_root.exists():
        roots = sorted(path for path in package_root.iterdir() if path.is_dir())
        if len(roots) > 64:
            raise EvolutionError("surface capability catalog exceeds its bound")
        for root in roots:
            if root.is_symlink() or not CAPABILITY_RE.fullmatch(root.name):
                raise EvolutionError("surface capability catalog is unsafe")
            canonical = _surface_canonical(context, root.name)
            if canonical is None:
                continue
            surface = _surface(canonical.get("surface"))
            if adapter not in surface["adapters"]:
                continue
            projection_digests: dict[str, str] = {}
            for host in hosts:
                verify_evolution_projection(canonical, host, root / host)
                expected = compile_evolution_capability(canonical, host)
                skill_prefix = f"skills/{root.name}/"
                skill_root = context.root / (
                    f".agents/skills/{root.name}"
                    if host == "codex"
                    else f".claude/skills/{root.name}"
                )
                deployed_skill = {
                    path.relative_to(skill_root)
                    .as_posix(): hashlib.sha256(
                        (read_bounded_bytes(path, 256 * 1024) or b"")
                    )
                    .hexdigest()
                    for path in _current_files(skill_root, context.root)
                }
                expected_skill = {
                    relative.removeprefix(skill_prefix): hashlib.sha256(
                        content.encode("utf-8")
                    ).hexdigest()
                    for relative, content in expected.items()
                    if relative.startswith(skill_prefix)
                }
                agent_relative = (
                    f".codex/agents/{root.name}.toml"
                    if host == "codex"
                    else f".claude/agents/{root.name}.md"
                )
                package_agent = (
                    f"agents/{root.name}.toml"
                    if host == "codex"
                    else f"agents/{root.name}.md"
                )
                deployed_agent = _read_single_link_file(context, agent_relative)
                if deployed_skill != expected_skill or deployed_agent != expected[
                    package_agent
                ].encode("utf-8"):
                    raise EvolutionError("surface capability deployment drift detected")
                projection_digests[host] = _digest(expected)
            capabilities.append(
                {
                    "name": root.name,
                    "kind": surface["kind"],
                    "hosts": list(hosts),
                    "source_digest": _digest(canonical),
                    "projection_digest": _digest(projection_digests),
                }
            )
    return {
        "schema": "harness.surface-discovery/v1",
        "adapter": adapter,
        "hosts": list(hosts),
        "status": "pass",
        "capabilities": capabilities,
        "evidence_digest": _digest(
            {"adapter": adapter, "hosts": list(hosts), "capabilities": capabilities}
        ),
    }


def _surface_operation_result(
    context: WorktreeContext, canonical: dict[str, Any], operation: str
) -> dict[str, Any]:
    operations = canonical["skill"]["interface"]["operations"]
    if operation not in operations:
        raise EvolutionError("surface capability operation is unavailable")
    if operation == "inspect":
        return {
            "capability": canonical["name"],
            "kind": canonical["surface"]["kind"],
            "head_sha": context.head_sha,
            "worktree_id": context.worktree_id,
        }
    if operation == "report":
        return {
            "capability": canonical["name"],
            "license": canonical["license"],
            "operations": list(operations),
            "source_digest": _digest(canonical),
        }
    raise EvolutionError("surface capability operation has no trusted handler")


def call_surface_capability(
    context: WorktreeContext,
    *,
    name: str,
    adapter: str,
    value: Any,
) -> dict[str, Any]:
    discovery = discover_surface_capabilities(context, adapter)
    if not any(item["name"] == name for item in discovery["capabilities"]):
        raise EvolutionError("surface capability is not discoverable")
    canonical = _surface_canonical(context, name)
    if canonical is None or canonical["surface"]["kind"] != "cli":
        raise EvolutionError("surface capability is not a CLI")
    request = _exact(
        value, {"schema", "operation", "arguments"}, "surface call request"
    )
    if request["schema"] != "harness.surface-call/v1" or request["arguments"] != {}:
        raise EvolutionError("surface call request is invalid")
    operation = _nonempty(request["operation"], "surface operation", 64)
    result = _surface_operation_result(context, canonical, operation)
    material = {
        "adapter": adapter,
        "name": name,
        "operation": operation,
        "result": result,
        "discovery_digest": discovery["evidence_digest"],
    }
    return {
        "schema": "harness.surface-call-result/v1",
        "adapter": adapter,
        "name": name,
        "operation": operation,
        "status": "pass",
        "result": result,
        "evidence_digest": _digest(material),
    }


def _bounded_mcp_object(
    value: Any,
    label: str,
    *,
    max_nodes: int = 64,
    max_depth: int = 4,
    max_bytes: int = 4096,
) -> dict[str, Any]:
    try:
        validate_json_shape(value, max_nodes=max_nodes, max_depth=max_depth)
        encoded_size = len(_canonical_text(value).encode("utf-8"))
    except (TypeError, ValueError) as exc:
        raise EvolutionError(f"{label} is invalid") from exc
    if not isinstance(value, dict) or encoded_size > max_bytes:
        raise EvolutionError(f"{label} is invalid")
    return value


def _bounded_mcp_metadata(value: Any, label: str) -> dict[str, Any]:
    metadata = _bounded_mcp_object(value, label)
    if "progressToken" in metadata:
        token = metadata["progressToken"]
        if isinstance(token, str):
            _bounded_string(token, "MCP progress token", 128)
        elif (
            not isinstance(token, int)
            or isinstance(token, bool)
            or abs(token) > 2**53 - 1
        ):
            raise EvolutionError("MCP progress token is invalid")
    if "io.modelcontextprotocol/related-task" in metadata:
        related = _bounded_mcp_object(
            metadata["io.modelcontextprotocol/related-task"],
            "MCP related task metadata",
        )
        if "taskId" not in related:
            raise EvolutionError("MCP related task metadata is invalid")
        _bounded_string(related["taskId"], "MCP related task id", 128)
    return metadata


def mcp_surface_message(
    context: WorktreeContext,
    *,
    name: str,
    adapter: str,
    value: Any,
) -> dict[str, Any] | None:
    discovery = discover_surface_capabilities(context, adapter)
    if not any(item["name"] == name for item in discovery["capabilities"]):
        raise EvolutionError("surface capability is not discoverable")
    canonical = _surface_canonical(context, name)
    if canonical is None or canonical["surface"]["kind"] != "mcp":
        raise EvolutionError("surface capability is not an MCP server")
    if not isinstance(value, dict) or value.get("jsonrpc") != "2.0":
        raise EvolutionError("MCP message is invalid")
    if "id" not in value:
        value = {"params": {}, **value}
        notification = _exact(
            value, {"jsonrpc", "method", "params"}, "MCP notification"
        )
        method = _nonempty(notification["method"], "MCP notification method", 128)
        params = _bounded_mcp_object(
            notification["params"],
            "MCP notification params",
            max_nodes=512,
            max_depth=8,
            max_bytes=64 * 1024,
        )
        if "_meta" in params:
            _bounded_mcp_metadata(params["_meta"], "MCP notification metadata")
        if not method.startswith("notifications/"):
            raise EvolutionError("MCP notification is invalid")
        return None
    method = value.get("method")
    value = {"params": {}, **value}
    request = _exact(value, {"jsonrpc", "id", "method", "params"}, "MCP request")
    request_id = request["id"]
    if (
        not isinstance(request_id, (str, int))
        or isinstance(request_id, bool)
        or len(str(request_id)) > 64
    ):
        raise EvolutionError("MCP request id is invalid")
    params = request["params"]
    if not isinstance(params, dict):
        raise EvolutionError("MCP request params are invalid")
    if "_meta" in params:
        _bounded_mcp_metadata(params["_meta"], "MCP request metadata")
    if method == "ping":
        if not set(params) <= {"_meta"}:
            raise EvolutionError("MCP ping params are invalid")
        result = {}
    elif method == "initialize":
        initialize_keys = {"protocolVersion", "capabilities", "clientInfo"}
        if not initialize_keys.issubset(params) or not set(params) <= (
            initialize_keys | {"_meta"}
        ):
            raise EvolutionError("MCP initialize params is invalid")
        initialize = params
        client = initialize["clientInfo"]
        client_keys = {"name", "version", "title", "icons", "websiteUrl", "description"}
        if (
            not isinstance(client, dict)
            or not {"name", "version"}.issubset(client)
            or not set(client).issubset(client_keys)
        ):
            raise EvolutionError("MCP client info is invalid")
        _nonempty(client["name"], "MCP client name", 128)
        _nonempty(client["version"], "MCP client version", 64)
        for key, label, limit in (
            ("title", "MCP client title", 256),
            ("websiteUrl", "MCP client website URL", 2048),
            ("description", "MCP client description", 2048),
        ):
            if key in client:
                _bounded_string(client[key], label, limit)
        if "icons" in client:
            icons = client["icons"]
            if not isinstance(icons, list) or len(icons) > 16:
                raise EvolutionError("MCP client icons are invalid")
            for icon in icons:
                icon_keys = {"src", "mimeType", "sizes", "theme"}
                if (
                    not isinstance(icon, dict)
                    or "src" not in icon
                    or not set(icon).issubset(icon_keys)
                ):
                    raise EvolutionError("MCP client icon is invalid")
                _bounded_string(icon["src"], "MCP client icon source", 2048)
                if "mimeType" in icon:
                    _bounded_string(
                        icon["mimeType"], "MCP client icon MIME type", 128
                    )
                if "sizes" in icon:
                    sizes = icon["sizes"]
                    if not isinstance(sizes, list) or len(sizes) > 16:
                        raise EvolutionError("MCP client icon sizes are invalid")
                    for size in sizes:
                        _bounded_string(size, "MCP client icon size", 32)
                if "theme" in icon and icon["theme"] not in {"light", "dark"}:
                    raise EvolutionError("MCP client icon theme is invalid")
        requested_protocol = _bounded_string(
            initialize["protocolVersion"], "MCP protocol version", 64
        )
        if not isinstance(initialize["capabilities"], dict):
            raise EvolutionError("MCP initialize params are unsupported")
        protocol_version = (
            requested_protocol
            if requested_protocol in MCP_SUPPORTED_PROTOCOL_VERSIONS
            else MCP_LATEST_PROTOCOL_VERSION
        )
        result = {
            "protocolVersion": protocol_version,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": canonical["name"], "version": canonical["version"]},
        }
    elif method == "tools/list":
        if not set(params) <= {"cursor", "_meta"}:
            raise EvolutionError("MCP tools/list params are invalid")
        if "cursor" in params:
            _bounded_string(params["cursor"], "MCP tools/list cursor", 2048)
        result = {
            "tools": [
                {
                    "name": operation,
                    "description": f"{operation} bounded repository metadata",
                    "inputSchema": {
                        "type": "object",
                        "properties": {},
                        "additionalProperties": False,
                    },
                }
                for operation in canonical["skill"]["interface"]["operations"]
            ]
        }
    elif method == "tools/call":
        if (
            not isinstance(params, dict)
            or "name" not in params
            or not set(params) <= {"name", "arguments", "_meta"}
        ):
            raise EvolutionError("MCP tools/call params are invalid")
        arguments = params.get("arguments", {})
        if arguments != {}:
            raise EvolutionError("MCP tool arguments are invalid")
        operation = _nonempty(params["name"], "MCP tool name", 64)
        if operation not in canonical["skill"]["interface"]["operations"]:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32602, "message": "Invalid params"},
            }
        operation_result = _surface_operation_result(context, canonical, operation)
        result = {
            "content": [{"type": "text", "text": _canonical_text(operation_result)}],
            "structuredContent": operation_result,
            "isError": False,
        }
    else:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32601, "message": "Method not found"},
        }
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def hook_surface_event(
    context: WorktreeContext,
    *,
    name: str,
    adapter: str,
    host: str,
    event: str,
    payload: Any,
) -> dict[str, Any]:
    """Invoke one deployed Hook capability through the shared event seam."""

    from harness.events import HOOK_EVENTS, normalize_hook_event, persist_hook_event

    discovery = discover_surface_capabilities(context, adapter)
    if host not in discovery["hosts"] or event not in HOOK_EVENTS:
        raise EvolutionError("Hook surface invocation is invalid")
    canonical = _surface_canonical(context, name)
    if (
        canonical is None
        or canonical["surface"]["kind"] != "hook"
        or not any(item["name"] == name for item in discovery["capabilities"])
        or not isinstance(payload, dict)
    ):
        raise EvolutionError("Hook surface capability is not deployed")
    normalized = {**normalize_hook_event(host, event, payload), "capability": name}
    ledger = persist_hook_event(context, normalized)
    material = {
        "adapter": adapter,
        "host": host,
        "capability": name,
        "event": normalized,
        "deployment_digest": _digest(canonical),
    }
    return {
        "schema": "harness.hook-surface-result/v1",
        "status": "recorded",
        "adapter": adapter,
        "host": host,
        "capability": name,
        "event": normalized,
        "ledger": ledger.relative_to(context.root).as_posix(),
        "evidence_digest": _digest(material),
    }


def smoke_surface_capability(
    context: WorktreeContext, *, name: str, adapter: str
) -> dict[str, Any]:
    """Run deterministic discovery and policy smoke without candidate code."""

    if not CAPABILITY_RE.fullmatch(name):
        raise EvolutionError("capability name is invalid")
    discovery = discover_surface_capabilities(context, adapter)
    capability = next(
        (item for item in discovery["capabilities"] if item["name"] == name), None
    )
    if capability is None:
        raise EvolutionError("surface capability is not discoverable")
    canonical = _surface_canonical(context, name)
    if canonical is None:
        raise EvolutionError("surface capability is not discoverable")
    surface = _surface(canonical["surface"])
    observations: dict[str, Any] = {}
    results: dict[str, bool] = {}
    if surface["kind"] == "cli":
        calls = {
            operation: call_surface_capability(
                context,
                name=name,
                adapter=adapter,
                value={
                    "schema": "harness.surface-call/v1",
                    "operation": operation,
                    "arguments": {},
                },
            )
            for operation in ("inspect", "report")
        }
        results = {
            "discovery": capability["kind"] == "cli",
            "smoke": all(item["status"] == "pass" for item in calls.values()),
        }
        observations = {
            "calls": {
                operation: item["evidence_digest"] for operation, item in calls.items()
            }
        }
    elif surface["kind"] == "mcp":
        messages = {
            "initialize": {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": MCP_LATEST_PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": "harness-smoke", "version": "1"},
                },
            },
            "tools/list": {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {},
            },
            "tools/call": {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "inspect", "arguments": {}},
            },
        }
        responses = {
            method: mcp_surface_message(
                context, name=name, adapter=adapter, value=message
            )
            for method, message in messages.items()
        }
        listed = responses["tools/list"]
        called = responses["tools/call"]
        results = {
            "discovery": capability["kind"] == "mcp",
            "smoke": (
                responses["initialize"] is not None
                and listed is not None
                and [tool["name"] for tool in listed["result"]["tools"]]
                == canonical["skill"]["interface"]["operations"]
                and called is not None
                and called["result"]["isError"] is False
            ),
        }
        observations = {
            "protocol_version": MCP_LATEST_PROTOCOL_VERSION,
            "methods": {
                method: _digest(response)
                for method, response in responses.items()
                if response is not None
            },
        }
    elif surface["kind"] == "hook":
        from harness.events import normalize_hook_event

        before = _changed_paths(context.root)
        secret = "SYNTHETIC_HOOK_SECRET_VALUE"
        host = discovery["hosts"][0]
        event = "post-tool-use" if host == "codex" else "post-tool-use-failure"
        payload = {
            "session_id": f"{name}-{adapter}-hook-smoke",
            "tool_name": "shell_command" if host == "codex" else "Bash",
            "tool_input": {"command": "npm test", "token": secret},
            **(
                {"tool_response": {"exit_code": 1, "stderr": secret}}
                if host == "codex"
                else {"error": f"Exit code 1\n{secret}"}
            ),
        }
        projected = normalize_hook_event(host, event, payload)
        ledger = context.runtime_root / projected["session_id"] / "events.jsonl"
        hook_configs = (".codex/hooks.json", ".claude/settings.json")
        config_digests: dict[str, str] = {}
        configs_current = True
        protected: dict[Path, bytes | None] = {}
        for relative in hook_configs:
            raw = _read_single_link_file(context, relative)
            head = _git_bytes(context.root, "show", f"HEAD:{relative}")
            configs_current = configs_current and raw is not None and raw == head
            if raw is not None:
                config_digests[relative] = hashlib.sha256(raw).hexdigest()
            protected[context.root / relative] = raw
        surface_manifest = (
            context.root
            / "harness/capability-packages"
            / name
            / "codex"
            / "skills"
            / name
            / "surface.json"
        )
        protected[surface_manifest] = read_bounded_bytes(surface_manifest, 256 * 1024)
        protected[ledger] = read_bounded_bytes(ledger, 256 * 1024)
        canary = context.runtime_root / "hook-canary" / f"{name}-{adapter}.json"
        protected[canary] = read_bounded_bytes(canary, 64 * 1024)
        canary_material = {
            "schema": "harness.hook-canary/v1",
            "capability": name,
            "adapter": adapter,
            "host": host,
            "deployment_digest": _digest(canonical),
            "config_digests": config_digests,
        }
        calls: list[dict[str, Any]] = []
        stored: list[dict[str, Any]] = []
        canary_invoked = False
        try:
            ensure_no_link_components(context.root, canary)
            write_bounded_text(
                canary, _canonical_text(canary_material) + "\n", 64 * 1024
            )
            calls = [
                hook_surface_event(
                    context,
                    name=name,
                    adapter=adapter,
                    host=host,
                    event=event,
                    payload=payload,
                )
                for _ in range(2)
            ]
            ledger_raw = read_bounded_bytes(ledger, 256 * 1024) or b""
            stored = [json.loads(line) for line in ledger_raw.splitlines()[-2:]]
            canary_invoked = (
                len(stored) == 2
                and all(item.get("capability") == name for item in stored)
                and all(call["status"] == "recorded" for call in calls)
            )
            rendered = ledger_raw.decode("utf-8", errors="strict") + _canonical_text(
                calls
            )
        finally:
            for path, snapshot in protected.items():
                ensure_no_link_components(context.root, path)
                if snapshot is None:
                    if path.is_file() and not path.is_symlink():
                        _unlink_nofollow(path)
                else:
                    write_bounded_text(
                        path, snapshot.decode("utf-8", errors="strict"), 256 * 1024
                    )
            for directory in (ledger.parent, canary.parent):
                try:
                    directory.rmdir()
                except OSError:
                    pass
        rollback_restored = all(
            read_bounded_bytes(path, 256 * 1024) == snapshot
            for path, snapshot in protected.items()
        )
        results = {
            "replay": len(stored) == 2
            and stored[0]["semantic"] == stored[1]["semantic"],
            "shadow": _changed_paths(context.root) == before,
            "no-secret": secret not in rendered,
            "multi-worktree": (
                context.git_dir.resolve() != context.common_git_dir.resolve()
            ),
            "canary": configs_current and canary_invoked,
            "rollback": rollback_restored
            and canonical["packaging"]
            == {
                "scope": "repository-local",
                "reversible": True,
                "hosts": ["codex", "claude"],
            },
        }
        observations = {
            "replay_digest": _digest([item["semantic"] for item in stored]),
            "shadow_before": _digest(before),
            "shadow_after": _digest(_changed_paths(context.root)),
            "secret_survived": secret in rendered,
            "worktree_id": context.worktree_id,
            "canary_digests": config_digests,
            "canary_evidence_digest": _digest(calls),
            "rollback_digest": _digest(
                {
                    path.relative_to(context.root).as_posix(): (
                        hashlib.sha256(snapshot).hexdigest()
                        if snapshot is not None
                        else None
                    )
                    for path, snapshot in protected.items()
                }
            ),
        }
    else:
        policy = surface["loop"]
        current = {"fingerprint": "1" * 64, "evidence_digest": "2" * 64}

        def step(
            *,
            attempts: list[dict[str, str]],
            requested_adapter: str = adapter,
            user_input: bool = False,
        ) -> dict[str, Any]:
            return loop_surface_step(
                {
                    "schema": "harness.loop-step/v1",
                    "policy": policy,
                    "frozen_adapter": adapter,
                    "requested_adapter": requested_adapter,
                    "attempts": attempts,
                    "current": current,
                    "user_input": user_input,
                },
                adapter,
            )

        other_adapter = next(item for item in SURFACE_ADAPTERS if item != adapter)
        bounded = step(attempts=[current] * policy["max_attempts"])
        no_progress = step(attempts=[current] * policy["no_progress_limit"])
        yielded = step(attempts=[], user_input=True)
        switched = step(attempts=[], requested_adapter=other_adapter)
        results = {
            "bounded": bounded["reason"] == "attempt-limit",
            "no-progress-stop": no_progress["reason"] == "no-progress",
            "yield-to-user": yielded["action"] == "yield-to-user",
            "no-adapter-switch": switched["reason"] == "adapter-switch-prohibited",
        }
        observations = {
            "bounded": bounded,
            "no-progress-stop": no_progress,
            "yield-to-user": yielded,
            "no-adapter-switch": switched,
        }
    if set(results) != set(_surface_check_names(surface)) or not all(results.values()):
        raise EvolutionError(f"{surface['kind'].title()} surface smoke failed")
    checks = {name: "pass" for name in _surface_check_names(surface)}
    material = {
        "adapter": adapter,
        "hosts": discovery["hosts"],
        "capability": capability,
        "checks": checks,
        "observations": observations,
        "discovery_digest": discovery["evidence_digest"],
    }
    return {
        "schema": "harness.surface-smoke/v1",
        "name": name,
        "kind": surface["kind"],
        "adapter": adapter,
        "hosts": discovery["hosts"],
        "status": "pass",
        "checks": checks,
        "observations": observations,
        "evidence_digest": _digest(material),
    }


def _frontmatter(text: str, label: str) -> tuple[list[str], str]:
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        raise EvolutionError(f"{label} discovery metadata is invalid")
    header, body = text[4:].split("\n---\n", 1)
    lines = header.splitlines()
    if not lines or any(not line or ":" not in line for line in lines):
        raise EvolutionError(f"{label} discovery metadata is invalid")
    return lines, body


def _verify_host_conformance(source: dict[str, Any], host: str, root: Path) -> None:
    name = source["name"]
    skill_path = root / "skills" / name / "SKILL.md"
    raw_skill = read_bounded_bytes(skill_path, 256 * 1024)
    if raw_skill is None:
        raise EvolutionError("Skill discovery failed")
    try:
        skill_text = raw_skill.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise EvolutionError("Skill discovery failed") from exc
    header, _ = _frontmatter(skill_text, "Skill")
    fields = {line.split(":", 1)[0]: line.split(":", 1)[1].strip() for line in header}
    invocation = source["skill"]["invocation"]
    expected_keys = {"name", "description"} | (
        {"disable-model-invocation"}
        if invocation["mode"] == "manual" and host == "claude"
        else set()
    )
    try:
        parsed_description = json.loads(fields.get("description", ""))
    except json.JSONDecodeError as exc:
        raise EvolutionError("Skill discovery failed") from exc
    if (
        set(fields) != expected_keys
        or fields.get("name") != name
        or parsed_description != source["description"]
        or (
            invocation["mode"] == "manual"
            and host == "claude"
            and fields.get("disable-model-invocation") != "true"
        )
    ):
        raise EvolutionError("Skill discovery failed")
    if invocation["mode"] == "manual" and host == "codex":
        metadata = read_bounded_bytes(
            root / "skills" / name / "agents" / "openai.yaml", 64 * 1024
        )
        if metadata != invocation["metadata"]["openai_yaml"].encode("utf-8"):
            raise EvolutionError("manual Skill metadata drift detected")

    if host == "codex":
        raw_agent = read_bounded_bytes(root / "agents" / f"{name}.toml", 64 * 1024)
        try:
            agent = tomllib.loads((raw_agent or b"").decode("utf-8", errors="strict"))
        except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
            raise EvolutionError("Codex Agent discovery failed") from exc
        if agent != {
            "name": name,
            "description": source["agent"]["description"],
            "sandbox_mode": "read-only",
            "developer_instructions": "\n".join(source["agent"]["instructions"]),
            "agents": {"enabled": False},
        }:
            raise EvolutionError("Codex Agent discovery failed")
    else:
        raw_agent = read_bounded_bytes(root / "agents" / f"{name}.md", 64 * 1024)
        try:
            agent_text = (raw_agent or b"").decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise EvolutionError("Claude Agent discovery failed") from exc
        agent_header, agent_body = _frontmatter(agent_text, "Claude Agent")
        fields = {
            line.split(":", 1)[0]: line.split(":", 1)[1].strip()
            for line in agent_header
        }
        try:
            parsed_description = json.loads(fields.get("description", ""))
        except json.JSONDecodeError as exc:
            raise EvolutionError("Claude Agent discovery failed") from exc
        if (
            fields
            != {
                "name": name,
                "description": json.dumps(
                    source["agent"]["description"], ensure_ascii=True
                ),
                "tools": "Read, Grep, Glob",
            }
            or parsed_description != source["agent"]["description"]
            or "Writer lease required for any write: true" not in agent_body
            or "Maximum children: 0" not in agent_body
        ):
            raise EvolutionError("Claude Agent discovery failed")


def _evolution_path(context: WorktreeContext, task_id: str) -> Path:
    return _task_dir(context, task_id) / "evolution.json"


def _verify_gap_gate(
    context: WorktreeContext, task_id: str, gap_state: dict[str, Any]
) -> dict[str, Any]:
    record = next(
        (
            item
            for item in startup_memory(context)["records"]
            if item.get("record_id") == gap_state.get("record_id")
        ),
        None,
    )
    if (
        record is None
        or record.get("type") != "capability-gap"
        or record.get("validation") != "accepted"
        or record.get("validity", {}).get("to") is not None
        or record.get("evidence_digest") != gap_state.get("evidence_digest")
    ):
        raise EvolutionError("accepted current capability gap is unavailable")
    provenance = record.get("provenance")
    expected_origins = [
        {
            "task_id": item["task_id"],
            "commit_sha": item["commit_sha"],
            "evidence_digest": item["evidence_digest"],
        }
        for item in provenance or []
    ]
    if (
        not provenance
        or gap_state.get("origins") != expected_origins
        or any(
            item.get("source") != "accepted-task"
            or item.get("task_id") == task_id
            or item.get("evidence_kind") != "verified-capability-gap"
            for item in provenance
        )
    ):
        raise EvolutionError("capability gap origin is not an accepted terminal task")
    for item in provenance:
        commit = item["commit_sha"]
        receipt = item.get("acceptance_receipt")
        try:
            _git_bytes(context.root, "merge-base", "--is-ancestor", commit, "HEAD")
            message = _git_bytes(
                context.root,
                "log",
                "-1",
                "--encoding=UTF-8",
                "--format=%B",
                commit,
            ).decode("utf-8", errors="strict")
        except (UnicodeDecodeError, ValueError) as exc:
            raise EvolutionError(
                "capability gap origin is not an accepted terminal task"
            ) from exc
        if (
            not isinstance(receipt, dict)
            or receipt.get("task_id") != item["task_id"]
            or receipt.get("terminal_state") != "accepted"
            or receipt.get("commit_sha") != commit
            or receipt.get("evidence_digest") != item["evidence_digest"]
            or _commit_parents(context.root, commit)
            != ([] if receipt.get("base_sha") is None else [receipt["base_sha"]])
            or _commit_paths(context.root, commit) != receipt.get("paths")
            or _commit_tree_snapshot(context.root, commit, receipt["paths"])
            != receipt.get("index_snapshot")
            or message.splitlines().count(f"Harness-Task: {_task_key(item['task_id'])}")
            != 1
        ):
            raise EvolutionError(
                "capability gap origin is not an accepted terminal task"
            )
    return record


def _load_evolution_run(
    context: WorktreeContext,
    task_id: str,
    *,
    expected_mode: str,
    actor: str | None = None,
    verify_fixed: bool = True,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if context.git_dir.resolve() == context.common_git_dir.resolve():
        raise EvolutionError("evolution requires an independent linked worktree")
    path = _evolution_path(context, task_id)
    run = read_bounded_json_object(path, 128 * 1024, max_nodes=8_000, max_depth=16)
    if set(run) != {
        "schema",
        "task_id",
        "mode",
        "writer",
        "state",
        "capability_name",
        "gap",
        "baseline",
        "evaluator",
        "holdout",
        "outputs",
        "canonical_path",
        "report_path",
        "rollback",
        "search",
        "candidate",
        "source_verification",
        "projection_digest",
        "evaluation",
        "outcome",
        "outcome_reason",
        "strategy",
        "canonical",
        "projection",
    }:
        raise EvolutionError("Evolution Run state is invalid")
    _, direct = _load_run(context, task_id, expected_mode=expected_mode)
    contract = direct["contract"]
    mode = contract["execution"]["mode"]
    writer = _expected_writer(mode)
    if actor is not None:
        _require_writer_actor(mode, actor)
        if direct["state"] not in {"executing", "repairing"} or contract[
            "writer_lease"
        ] != {"holder": writer, "state": "active"}:
            raise EvolutionError(
                "Evolution mutation actor does not hold the writer lease"
            )
    if (
        run["schema"] != "harness.evolution-run/v1"
        or run["task_id"] != task_id
        or run["mode"] != mode
        or mode != expected_mode
        or run["writer"] != writer
        or writer is None
        or run["state"]
        not in {
            "search-required",
            "adapt-ready",
            "build-ready",
            "authorization-required",
            "applying",
            "rolling-back",
            "evaluating",
            "promotion-ready",
            "deferred",
            "rejected",
        }
        or not (
            (
                direct["state"] in {"executing", "repairing", "verifying", "reviewing"}
                and contract["writer_lease"] == {"holder": writer, "state": "active"}
            )
            or (
                direct["state"] == "accepted"
                and contract["writer_lease"]
                in (
                    {"holder": writer, "state": "active"},
                    {"holder": writer, "state": "inactive"},
                    {"holder": writer, "state": "released"},
                )
            )
        )
    ):
        raise EvolutionError("Evolution Run state is invalid")
    try:
        evaluator = _fixed_artifact(run["evaluator"], "evaluator", descriptor=True)
        holdout = _fixed_artifact(run["holdout"], "holdout", descriptor=True)
        capability_name = _nonempty(run["capability_name"], "capability name", 64)
        paths = _capability_paths(task_id, capability_name)
        outputs = _output_roots(run["outputs"], (evaluator["path"], holdout["path"]))
        canonical_path = _relative_path(
            run["canonical_path"], "evolution canonical path"
        )
        report_path = _relative_path(run["report_path"], "evolution report path")
    except EvolutionError as exc:
        raise EvolutionError("Evolution Run state is invalid") from exc
    if (
        evaluator["path"].casefold() == holdout["path"].casefold()
        or evaluator["id"].casefold() == holdout["id"].casefold()
        or evaluator["digest"] == holdout["digest"]
        or evaluator["required_cases"] != EVALUATOR_CASES
        or holdout["required_cases"] != HOLDOUT_CASES
        or outputs != {"codex": paths["codex"], "claude": paths["claude"]}
        or canonical_path != paths["canonical"]
        or report_path != paths["report"]
    ):
        raise EvolutionError("Evolution Run state is invalid")
    if verify_fixed:
        _fixed_artifacts_are_current(context, run)
    required_owned = _required_owned_paths(task_id, capability_name)
    if (
        set(contract["plan"]["owned_paths"]) != required_owned
        or any(
            _path_is_owned(item["path"], contract["plan"]["owned_paths"])
            for item in (evaluator, holdout)
        )
        or run["rollback"] != "git-head-snapshot"
    ):
        raise EvolutionError("Evolution Run state is invalid")
    baseline = run["baseline"]
    if (
        not isinstance(baseline, dict)
        or set(baseline)
        != {
            "head_sha",
            "branch",
            "entries",
        }
        or baseline["head_sha"] != contract["execution"]["base_sha"]
        or baseline["branch"] != contract["execution"]["branch"]
        or baseline["entries"]
        != _baseline_entries(
            context,
            baseline["head_sha"],
            [
                paths["package"],
                paths["codex_skill"],
                paths["claude_skill"],
                paths["codex_agent"],
                paths["claude_agent"],
            ],
        )
    ):
        raise EvolutionError("Evolution Run state is invalid")
    gap = run["gap"]
    if (
        not isinstance(gap, dict)
        or set(gap)
        != {
            "record_id",
            "evidence_digest",
            "origins",
        }
        or not isinstance(gap["record_id"], str)
        or not re.fullmatch(r"mem-[0-9a-f]{64}", gap["record_id"])
        or not isinstance(gap["evidence_digest"], str)
        or not DIGEST_RE.fullmatch(gap["evidence_digest"])
        or not isinstance(gap["origins"], list)
        or not gap["origins"]
        or any(
            not isinstance(origin, dict)
            or set(origin) != {"task_id", "commit_sha", "evidence_digest"}
            or not isinstance(origin["task_id"], str)
            or not TASK_RE.fullmatch(origin["task_id"])
            or origin["task_id"] == task_id
            or not isinstance(origin["commit_sha"], str)
            or not re.fullmatch(r"[0-9a-f]{40}", origin["commit_sha"])
            or not isinstance(origin["evidence_digest"], str)
            or not DIGEST_RE.fullmatch(origin["evidence_digest"])
            for origin in gap["origins"]
        )
    ):
        raise EvolutionError("Evolution Run state is invalid")
    _verify_gap_gate(context, task_id, gap)
    projection = run["projection"]
    if projection is not None:
        if (
            not isinstance(projection, dict)
            or set(projection)
            != {
                "source_digest",
                "hosts",
                "deployments",
                "files",
                "digest",
            }
            or not isinstance(projection["source_digest"], str)
            or not DIGEST_RE.fullmatch(projection["source_digest"])
            or not isinstance(projection["digest"], str)
            or not DIGEST_RE.fullmatch(projection["digest"])
            or not isinstance(projection["hosts"], dict)
            or set(projection["hosts"]) != {"codex", "claude"}
        ):
            raise EvolutionError("Evolution Run state is invalid")
        for host in ("codex", "claude"):
            item = projection["hosts"][host]
            if (
                not isinstance(item, dict)
                or set(item)
                != {
                    "root",
                    "files",
                    "digest",
                }
                or item["root"] != outputs[host]
                or not isinstance(item["files"], dict)
                or not 1 <= len(item["files"]) <= 64
                or any(
                    _relative_path(relative, "projection path") != relative
                    or not isinstance(digest, str)
                    or not DIGEST_RE.fullmatch(digest)
                    for relative, digest in item["files"].items()
                )
                or item["digest"] != _digest(item["files"])
            ):
                raise EvolutionError("Evolution Run state is invalid")
        if (
            not isinstance(projection["deployments"], dict)
            or projection["deployments"]
            != _expected_deployments(capability_name, projection["hosts"], paths)
            or not isinstance(projection["files"], dict)
            or not 1 <= len(projection["files"]) <= 130
            or any(
                _relative_path(relative, "projection file") != relative
                or not isinstance(digest, str)
                or not DIGEST_RE.fullmatch(digest)
                for relative, digest in projection["files"].items()
            )
            or projection["digest"] != _digest(projection["files"])
            or run["projection_digest"] != projection["digest"]
        ):
            raise EvolutionError("Evolution Run state is invalid")
        canonical = run["canonical"]
        surface_canonical = isinstance(canonical, dict) and "surface" in canonical
        if (
            not isinstance(canonical, dict)
            or set(canonical)
            != {
                "name",
                "version",
                "license",
                "source_digest",
            }
            | ({"surface"} if surface_canonical else set())
            or not isinstance(canonical["name"], str)
            or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", canonical["name"])
            or not isinstance(canonical["version"], str)
            or not re.fullmatch(r"\d+\.\d+\.\d+", canonical["version"])
            or canonical["license"] not in LICENSES
            or canonical["source_digest"] != projection["source_digest"]
        ):
            raise EvolutionError("Evolution Run state is invalid")
        if surface_canonical:
            try:
                if _surface(canonical["surface"]) != canonical["surface"]:
                    raise EvolutionError("Evolution Run state is invalid")
            except EvolutionError as exc:
                raise EvolutionError("Evolution Run state is invalid") from exc
    elif run["projection_digest"] is not None:
        raise EvolutionError("Evolution Run state is invalid")
    elif run["canonical"] is not None:
        raise EvolutionError("Evolution Run state is invalid")
    search = run["search"]
    if search is None:
        if (
            run["state"] != "search-required"
            or run["candidate"] is not None
            or any(
                run[key] is not None
                for key in (
                    "strategy",
                    "canonical",
                    "projection",
                    "projection_digest",
                    "evaluation",
                    "outcome",
                    "outcome_reason",
                    "source_verification",
                )
            )
        ):
            raise EvolutionError("Evolution Run state is invalid")
    else:
        try:
            normalized_search = _validate_stored_search(search)
        except EvolutionError as exc:
            raise EvolutionError("Evolution Run state is invalid") from exc
        if normalized_search != search or search[
            "installed_catalog"
        ] != _installed_catalog_evidence(run["mode"]):
            raise EvolutionError("Evolution Run state is invalid")
        selected = next(
            (
                candidate
                for candidate in search["candidates"]
                if candidate["id"] == search["selected_candidate"]
            ),
            None,
        )
        if run["candidate"] != selected:
            raise EvolutionError("Evolution Run state is invalid")
        verification = run["source_verification"]
        if verification is not None:
            surface_verification = selected is not None and "surface" in selected
            if (
                not isinstance(verification, dict)
                or set(verification)
                != {
                    "schema",
                    "source",
                    "revision",
                    "observations",
                    "evidence_digest",
                }
                | ({"surface"} if surface_verification else set())
                or verification["schema"] != "harness.evolution-source-verification/v1"
                or selected is None
                or verification["source"] != selected["canonical_source"]
                or verification["revision"] != selected["immutable_revision"]
                or not isinstance(verification["observations"], dict)
                or set(verification["observations"]) != {"artifact", "license"}
                or verification["evidence_digest"]
                != _digest(
                    {
                        "source": verification["source"],
                        "revision": verification["revision"],
                        "observations": verification["observations"],
                    }
                    | (
                        {"surface": verification["surface"]}
                        if surface_verification
                        else {}
                    )
                )
            ):
                raise EvolutionError("Evolution Run state is invalid")
            for item in verification["observations"].values():
                if (
                    not isinstance(item, dict)
                    or set(item) != {"path", "digest", "bytes"}
                    or _relative_path(item["path"], "source verification path")
                    != item["path"]
                    or not DIGEST_RE.fullmatch(str(item["digest"]))
                    or not isinstance(item["bytes"], int)
                    or not 0 <= item["bytes"] <= 256 * 1024
                ):
                    raise EvolutionError("Evolution Run state is invalid")
            manifest = {item["path"]: item for item in selected["manifest"]["files"]}
            expected_observations = {
                label: {
                    "path": selected[path_key],
                    "digest": selected[digest_key],
                    "bytes": manifest[selected[path_key]]["bytes"],
                }
                for label, path_key, digest_key in (
                    ("artifact", "artifact_path", "artifact_digest"),
                    ("license", "license_path", "license_digest"),
                )
            }
            if verification["observations"] != expected_observations:
                raise EvolutionError("Evolution Run state is invalid")
            if surface_verification:
                surface_evidence = verification["surface"]
                if (
                    not isinstance(surface_evidence, dict)
                    or set(surface_evidence)
                    != {
                        "kind",
                        "adapters",
                        "source_digest",
                        "projection_digests",
                        "channels",
                    }
                    or surface_evidence["kind"] != selected["surface"]["kind"]
                    or surface_evidence["adapters"] != SURFACE_ADAPTERS
                    or not DIGEST_RE.fullmatch(str(surface_evidence["source_digest"]))
                    or not isinstance(surface_evidence["projection_digests"], dict)
                    or set(surface_evidence["projection_digests"])
                    != set(SURFACE_ADAPTERS)
                    or any(
                        not DIGEST_RE.fullmatch(str(digest))
                        for digest in surface_evidence["projection_digests"].values()
                    )
                    or not isinstance(surface_evidence["channels"], dict)
                    or set(surface_evidence["channels"]) != set(SEARCH_CHANNELS)
                ):
                    raise EvolutionError("Evolution Run state is invalid")
                for channel, item in surface_evidence["channels"].items():
                    source_record = next(
                        source
                        for source in search["sources_consulted"]
                        if source["channel"] == channel
                    )
                    if (
                        not isinstance(item, dict)
                        or set(item) != {"url", "digest", "bytes", "status", "result"}
                        or item["url"] != source_record["evidence_url"]
                        or item["digest"] != source_record["evidence_digest"]
                        or item["bytes"] != source_record["evidence_bytes"]
                        or item["status"] not in {200, 404}
                        or (item["status"] == 404 and channel != "package-manager")
                        or item["result"] != source_record["result"]
                    ):
                        raise EvolutionError("Evolution Run state is invalid")
        decision = search["decision"]
        zero_candidate_build = (
            decision == "build"
            and not search["candidates"]
            and search["selected_candidate"] is None
        )
        if (
            (run["state"] == "adapt-ready" and decision != "adapt")
            or (run["state"] == "build-ready" and decision != "build")
            or (run["state"] == "deferred" and decision != "deferred")
            or (
                run["state"] == "authorization-required"
                and (
                    decision != "adapt"
                    or selected is None
                    or _auto_safe(selected, verification)
                )
            )
            or (
                run["state"]
                in {
                    "applying",
                    "rolling-back",
                    "evaluating",
                    "promotion-ready",
                    "rejected",
                }
                and run["strategy"] not in {"adapt", "build"}
            )
        ):
            raise EvolutionError("Evolution Run state is invalid")
        if (
            run["state"] == "adapt-ready" or run["strategy"] == "adapt"
        ) and not _auto_safe(selected, verification):
            raise EvolutionError("Evolution Run state is invalid")
        if run["state"] in {"adapt-ready", "build-ready"} and any(
            run[key] is not None
            for key in (
                "strategy",
                "canonical",
                "projection",
                "projection_digest",
                "evaluation",
                "outcome",
                "outcome_reason",
            )
        ):
            raise EvolutionError("Evolution Run state is invalid")
        if verification is None and not zero_candidate_build:
            raise EvolutionError("Evolution Run state is invalid")
        if run["state"] in {"applying", "evaluating"} and any(
            run[key] is not None for key in ("evaluation", "outcome", "outcome_reason")
        ):
            raise EvolutionError("Evolution Run state is invalid")
        if run["state"] in {"applying", "evaluating"} and any(
            run[key] is None
            for key in ("strategy", "canonical", "projection", "projection_digest")
        ):
            raise EvolutionError("Evolution Run state is invalid")
        if run["state"] in {"authorization-required", "deferred"} and (
            run["strategy"] is not None
            or run["canonical"] is not None
            or run["projection"] is not None
            or run["projection_digest"] is not None
            or run["evaluation"] is not None
            or run["outcome"] != "deferred"
            or run["outcome_reason"] is not None
        ):
            raise EvolutionError("Evolution Run state is invalid")
        if run["state"] in {"rolling-back", "promotion-ready", "rejected"}:
            if run["outcome"] not in {"promotable", "rejected"} or not isinstance(
                run["outcome_reason"], str
            ):
                raise EvolutionError("Evolution Run state is invalid")
            if run["evaluation"] is not None:
                try:
                    normalized_evaluation = _validate_stored_evaluation(
                        run, run["evaluation"]
                    )
                except EvolutionError as exc:
                    raise EvolutionError("Evolution Run state is invalid") from exc
                if normalized_evaluation != run["evaluation"]:
                    raise EvolutionError("Evolution Run state is invalid")
            if run["state"] == "promotion-ready" and (
                run["outcome"] != "promotable"
                or run["outcome_reason"] != "independent-evaluation-passed"
                or run["evaluation"] is None
                or any(
                    case["status"] != "pass"
                    for label in ("evaluator", "holdout")
                    for case in run["evaluation"][label]["cases"]
                )
                or run["evaluation"]["smoke"]["status"] != "pass"
            ):
                raise EvolutionError("Evolution Run state is invalid")
            if run["state"] in {"rolling-back", "rejected"} and (
                run["outcome"] != "rejected"
                or run["outcome_reason"]
                not in {
                    "adapt-application-failed",
                    "build-application-failed",
                    "evaluation-or-holdout-failed",
                    "post-build-projection-drift",
                    "active-evaluator-or-holdout-drift",
                    "terminal-revalidation-failed",
                    "interrupted-application",
                }
            ):
                raise EvolutionError("Evolution Run state is invalid")
    if run["state"] == "applying":
        _reject_with_rollback(context, path, run, "interrupted-application")
    elif run["state"] == "rolling-back":
        _restore_or_fail(context, run)
        run["state"] = "rejected"
        _write_report(context, run)
        _write_run(path, run)
    return run, direct


def _write_run(path: Path, run: dict[str, Any]) -> None:
    _write_exact_bounded(path, _canonical_text(run), 128 * 1024)


def _write_exact_bounded(path: Path, content: str, max_bytes: int) -> None:
    encoded = content.encode("utf-8")
    if len(encoded) > max_bytes:
        raise EvolutionError("Evolution state exceeds its byte bound")
    if path.is_symlink():
        raise EvolutionError("Evolution target is a symbolic link")
    write_bounded_text(path, content, max_bytes)
    if read_bounded_bytes(path, max_bytes) != encoded:
        raise EvolutionError("Evolution write was not exact")


def _candidate_audit(candidate: dict[str, Any] | None) -> dict[str, Any] | None:
    if candidate is None:
        return None
    audit = {
        key: candidate[key]
        for key in (
            "id",
            "canonical_source",
            "immutable_revision",
            "artifact_path",
            "artifact_digest",
            "license",
            "license_path",
            "license_digest",
            "permissions",
            "network",
            "data",
            "compatibility",
            "smoke",
            "rollback",
            "manifest",
            "effects",
            "installed",
        )
    } | {
        "invocation": {
            key: candidate["invocation"][key]
            for key in (
                "mode",
                "disable_model_invocation",
                "allow_implicit_invocation",
                "metadata_digest",
            )
        }
    }
    if "surface" in candidate:
        audit.update(
            {
                "surface": candidate["surface"],
                "artifact_format": candidate["artifact_format"],
                "install": candidate["install"],
                "package": candidate["package"],
            }
        )
    return audit


def _evolution_report(run: dict[str, Any]) -> dict[str, Any]:
    search = run["search"]
    paths = _capability_paths(run["task_id"], run["capability_name"])
    report = {
        "schema": "harness.evolution-report/v1",
        "task_id": run["task_id"],
        "gap_id": run["gap"]["record_id"],
        "gap_evidence_digest": run["gap"]["evidence_digest"],
        "capability_name": run["capability_name"],
        "strategy": (
            "Search" if run["outcome"] == "deferred" else search["decision"].title()
        ),
        "search_digest": _digest(search),
        "installed_catalog": search["installed_catalog"],
        "sources_consulted": search["sources_consulted"],
        "candidates": [
            {"id": candidate["id"], "digest": _digest(candidate)}
            for candidate in search["candidates"]
        ],
        "candidate_id": search["selected_candidate"],
        "candidate_digest": (
            _digest(run["candidate"])
            if run["candidate"] is not None
            else (
                run["canonical"]["source_digest"]
                if run["canonical"] is not None
                else None
            )
        ),
        "candidate": _candidate_audit(run["candidate"]),
        "source_verification": run["source_verification"],
        "canonical": (
            {"path": paths["canonical"], **run["canonical"]}
            if run["canonical"] is not None
            else None
        ),
        "evaluator_digest": run["evaluator"]["digest"],
        "holdout_digest": run["holdout"]["digest"],
        "projection_digest": run["projection_digest"],
        "evaluation_digest": (
            _digest(run["evaluation"]) if run["evaluation"] is not None else None
        ),
        "rollback": run["rollback"],
        "outcome": run["outcome"],
        "reason_code": run.get("outcome_reason") or search["reason_code"],
        "authorization": (
            _authorization(run["candidate"], run["source_verification"])
            if run["candidate"] is not None
            and (
                run["state"] == "authorization-required"
                or search["reason_code"] == "authorization-deferred"
            )
            else None
        ),
    }
    surface = (
        run["canonical"].get("surface")
        if isinstance(run.get("canonical"), dict)
        else None
    )
    if surface is None and run["candidate"] is not None:
        surface = run["candidate"].get("surface")
    if surface is not None:
        surface_evaluation = (
            run["evaluation"].get("surface")
            if isinstance(run.get("evaluation"), dict)
            else None
        )
        report["adapter_smoke"] = {
            adapter: (
                surface_evaluation["adapters"][adapter]["status"]
                if surface_evaluation is not None
                else "not-run"
            )
            for adapter in SURFACE_ADAPTERS
        }
        report["surface"] = surface
        report["surface_checks"] = (
            surface_evaluation["checks"] if surface_evaluation is not None else {}
        )
        report["surface_observations"] = (
            surface_evaluation["observations"] if surface_evaluation is not None else {}
        )
        report["origin_acceptance"] = {
            "status": "accepted",
            "origins": list(run["gap"]["origins"]),
        }
    return report


def _write_report(context: WorktreeContext, run: dict[str, Any]) -> dict[str, Any]:
    report = _evolution_report(run)
    path = (
        context.root
        / _capability_paths(run["task_id"], run["capability_name"])["report"]
    )
    ensure_no_link_components(context.root, path)
    _write_exact_bounded(path, _canonical_text(report), 64 * 1024)
    return report


def _baseline_entries(
    context: WorktreeContext, base_sha: str, targets: list[str]
) -> list[dict[str, str]]:
    raw = _git_bytes(
        context.root,
        "ls-tree",
        "-r",
        "-z",
        base_sha,
        "--",
        *sorted(targets),
    )
    entries: list[dict[str, str]] = []
    for row in (item for item in raw.split(b"\0") if item):
        try:
            metadata, raw_path = row.split(b"\t", 1)
            mode, kind, blob = metadata.decode("ascii").split(" ")
            path = raw_path.decode("utf-8", errors="strict")
        except (UnicodeDecodeError, ValueError) as exc:
            raise EvolutionError("capability baseline is invalid") from exc
        if (
            mode not in {"100644", "100755"}
            or kind != "blob"
            or not re.fullmatch(r"[0-9a-f]{40,64}", blob)
            or not any(
                path == target.rstrip("/")
                or _path_is_owned(path, [f"{target.rstrip('/')}/"])
                for target in targets
            )
        ):
            raise EvolutionError("capability baseline contains an unsafe entry")
        entries.append({"path": path, "mode": mode, "blob": blob})
        if len(entries) > 64:
            raise EvolutionError("capability baseline exceeds its bound")
    return entries


def _read_single_link_file(context: WorktreeContext, relative: str) -> bytes | None:
    target = context.root / relative
    ensure_no_link_components(context.root, target)
    raw = read_bounded_bytes(target, 256 * 1024)
    if raw is None or target.stat().st_nlink != 1:
        return None
    return raw


def _fixed_artifacts_are_current(context: WorktreeContext, run: dict[str, Any]) -> None:
    for label, artifact, schema, cases in (
        (
            "evaluator",
            run["evaluator"],
            "harness.evolution-evaluator/v1",
            EVALUATOR_CASES,
        ),
        ("holdout", run["holdout"], "harness.evolution-holdout/v1", HOLDOUT_CASES),
    ):
        raw = _read_single_link_file(context, artifact["path"])
        try:
            descriptor = json.loads(raw) if raw is not None else None
            committed = _git_bytes(context.root, "show", f"HEAD:{artifact['path']}")
        except (CodexDirectAdapterError, UnicodeDecodeError, json.JSONDecodeError):
            descriptor = None
            committed = None
        if (
            raw is None
            or committed != raw
            or hashlib.sha256(raw).hexdigest() != artifact["digest"]
            or not isinstance(descriptor, dict)
            or descriptor
            != {
                "schema": schema,
                "id": artifact["id"],
                "required_cases": cases,
            }
        ):
            raise EvolutionError("active evaluator or holdout drifted")


def _current_files(root: Path, boundary: Path) -> list[Path]:
    if not root.exists():
        return []
    ensure_no_link_components(boundary, root)
    if not root.is_dir() or root.is_symlink():
        raise EvolutionError("capability output boundary is unsafe")
    entries = list(root.rglob("*"))
    if len(entries) > 128:
        raise EvolutionError("capability output exceeds its bound")
    files: list[Path] = []
    for path in entries:
        ensure_no_link_components(boundary, path)
        if path.is_dir():
            continue
        if read_bounded_bytes(path, 256 * 1024) is None:
            raise EvolutionError("capability output contains an unsafe file")
        if path.stat().st_nlink != 1:
            raise EvolutionError("capability output contains a hard-linked file")
        files.append(path)
    return files


def _managed_files(context: WorktreeContext, run: dict[str, Any]) -> list[Path]:
    paths = _capability_paths(run["task_id"], run["capability_name"])
    files: list[Path] = []
    files.extend(_current_files(context.root / paths["package"], context.root))
    files.extend(_current_files(context.root / paths["codex_skill"], context.root))
    files.extend(_current_files(context.root / paths["claude_skill"], context.root))
    for raw_path in (paths["codex_agent"], paths["claude_agent"]):
        target = context.root / raw_path
        if target.exists() or target.is_symlink():
            ensure_no_link_components(context.root, target)
            raw = read_bounded_bytes(target, 256 * 1024)
            if raw is None or target.stat().st_nlink != 1:
                raise EvolutionError("deployed Agent output is unsafe")
            files.append(target)
    return files


def _assert_frozen_baseline(context: WorktreeContext, run: dict[str, Any]) -> None:
    expected = {entry["path"]: entry for entry in run["baseline"]["entries"]}
    actual = {
        path.relative_to(context.root).as_posix(): path
        for path in _managed_files(context, run)
    }
    if set(actual) != set(expected):
        raise EvolutionError(
            "capability baseline contains ignored or untracked content"
        )
    filemode = (
        _git_bytes(context.root, "config", "--bool", "core.filemode").strip() == b"true"
    )
    for relative, path in actual.items():
        entry = expected[relative]
        raw = read_bounded_bytes(path, 256 * 1024)
        baseline = _git_bytes(context.root, "cat-file", "blob", entry["blob"])
        mode = "100755" if path.stat().st_mode & stat.S_IXUSR else "100644"
        if raw != baseline or (filemode and mode != entry["mode"]):
            raise EvolutionError("capability baseline drifted")


def _write_bytes(path: Path, content: bytes, mode: int) -> None:
    _atomic_write_bytes(path, content, mode=mode)


def _clear_managed_files(context: WorktreeContext, run: dict[str, Any]) -> None:
    baseline = {entry["path"]: entry for entry in run["baseline"]["entries"]}
    projected = run.get("projection") or {}
    expected = projected.get("files", {}) if isinstance(projected, dict) else {}
    actual = {
        path.relative_to(context.root).as_posix(): path
        for path in _managed_files(context, run)
    }
    if set(actual) - set(baseline) - set(expected):
        raise EvolutionAdapterError("evolution rollback found unknown capability files")
    for relative, path in actual.items():
        raw = read_bounded_bytes(path, 256 * 1024)
        baseline_raw = (
            _git_bytes(context.root, "cat-file", "blob", baseline[relative]["blob"])
            if relative in baseline
            else None
        )
        expected_digest = expected.get(relative)
        if raw != baseline_raw and (
            raw is None
            or expected_digest is None
            or hashlib.sha256(raw).hexdigest() != expected_digest
        ):
            raise EvolutionAdapterError(
                "evolution rollback found drifted capability files"
            )
    for path in sorted(actual.values(), key=lambda item: len(item.parts), reverse=True):
        _unlink_nofollow(path)
    paths = _capability_paths(run["task_id"], run["capability_name"])
    roots = [
        context.root / paths[key]
        for key in ("package", "codex_skill", "claude_skill")
    ]
    directories = set(roots)
    for path in actual.values():
        for root in roots:
            if path.is_relative_to(root):
                directories.update(path.parents[: len(path.parents) - len(root.parents)])
                break
    protected_directories: set[Path] = set()
    for relative in baseline:
        path = context.root / relative
        for root in roots:
            if path.is_relative_to(root):
                protected_directories.update(
                    path.parents[: len(path.parents) - len(root.parents)]
                )
                break
    directories -= protected_directories
    for directory in sorted(directories, key=lambda item: len(item.parts), reverse=True):
        try:
            _rmdir_nofollow(directory)
        except OSError:
            pass


def _rollback_outputs(context: WorktreeContext, run: dict[str, Any]) -> None:
    _clear_managed_files(context, run)
    for entry in run["baseline"]["entries"]:
        content = _git_bytes(context.root, "cat-file", "blob", entry["blob"])
        target = context.root / entry["path"]
        ensure_no_link_components(context.root, target.parent)
        _write_bytes(target, content, int(entry["mode"], 8) & 0o777)
    _assert_frozen_baseline(context, run)


def _restore_or_fail(context: WorktreeContext, run: dict[str, Any]) -> None:
    try:
        _rollback_outputs(context, run)
    except EvolutionAdapterError:
        raise
    except (OSError, ValueError) as exc:
        raise EvolutionAdapterError("evolution rollback failed") from exc


def _reject_with_rollback(
    context: WorktreeContext,
    path: Path,
    run: dict[str, Any],
    reason: str,
    *,
    evaluation: dict[str, Any] | None = None,
) -> None:
    run["state"] = "rolling-back"
    run["outcome"] = "rejected"
    run["outcome_reason"] = reason
    run["evaluation"] = evaluation
    _write_run(path, run)
    _restore_or_fail(context, run)
    run["state"] = "rejected"
    _write_report(context, run)
    _write_run(path, run)


def _projection_record(
    source: dict[str, Any],
    packages: dict[str, dict[str, str]],
    paths: dict[str, str],
) -> dict[str, Any]:
    hosts: dict[str, Any] = {}
    all_files = {
        paths["canonical"]: hashlib.sha256(
            (_canonical_text(source) + "\n").encode("utf-8")
        ).hexdigest()
    }
    for host, package in packages.items():
        files = {
            path: hashlib.sha256(content.encode("utf-8")).hexdigest()
            for path, content in sorted(package.items())
        }
        hosts[host] = {
            "root": paths[host],
            "files": files,
            "digest": _digest(files),
        }
        all_files.update(
            {f"{paths[host]}/{relative}": digest for relative, digest in files.items()}
        )
    name = source["name"]
    deployments = _expected_deployments(name, hosts, paths)
    if any(digest is None for digest in deployments.values()):
        raise EvolutionError("capability deployment source is incomplete")
    all_files.update(deployments)
    return {
        "source_digest": _digest(source),
        "hosts": hosts,
        "deployments": deployments,
        "files": all_files,
        "digest": _digest(all_files),
    }


def _expected_deployments(
    name: str, hosts: dict[str, Any], paths: dict[str, str]
) -> dict[str, str | None]:
    deployments: dict[str, str | None] = {
        paths["codex_agent"]: hosts["codex"]["files"].get(f"agents/{name}.toml"),
        paths["claude_agent"]: hosts["claude"]["files"].get(f"agents/{name}.md"),
    }
    for host, skill_key in (("codex", "codex_skill"), ("claude", "claude_skill")):
        prefix = f"skills/{name}/"
        deployments.update(
            {
                f"{paths[skill_key]}/{relative[len(prefix):]}": digest
                for relative, digest in hosts[host]["files"].items()
                if relative.startswith(prefix)
            }
        )
    return deployments


def _verify_recorded_projection(
    context: WorktreeContext, projection: dict[str, Any]
) -> None:
    for host in ("codex", "claude"):
        expected = projection["hosts"][host]
        root = context.root / expected["root"]
        actual: dict[str, str] = {}
        for path in _current_files(root, context.root):
            raw = read_bounded_bytes(path, 256 * 1024)
            if raw is None:
                raise EvolutionError("capability projection drift detected")
            actual[path.relative_to(root).as_posix()] = hashlib.sha256(raw).hexdigest()
        if actual != expected["files"] or _digest(actual) != expected["digest"]:
            raise EvolutionError("capability projection drift detected")
    deployment_roots: dict[str, dict[str, str]] = {}
    for relative, digest in projection["deployments"].items():
        parts = PurePosixPath(relative).parts
        if len(parts) >= 4 and parts[:2] in {
            (".agents", "skills"),
            (".claude", "skills"),
        }:
            root = "/".join(parts[:3])
            deployment_roots.setdefault(root, {})["/".join(parts[3:])] = digest
    if len(deployment_roots) != 2:
        raise EvolutionError("capability deployment manifest is invalid")
    for relative_root, expected_files in deployment_roots.items():
        root = context.root / relative_root
        actual_files: dict[str, str] = {}
        for path in _current_files(root, context.root):
            raw = read_bounded_bytes(path, 256 * 1024)
            if raw is None:
                raise EvolutionError("deployed Skill projection is unsafe")
            actual_files[path.relative_to(root).as_posix()] = hashlib.sha256(
                raw
            ).hexdigest()
        if actual_files != expected_files:
            raise EvolutionError("deployed Skill projection drift detected")
    for relative, digest in projection["deployments"].items():
        raw = _read_single_link_file(context, relative)
        if raw is None or hashlib.sha256(raw).hexdigest() != digest:
            raise EvolutionError("deployed Agent projection drift detected")
    actual_files: dict[str, str] = {}
    for relative in projection["files"]:
        raw = _read_single_link_file(context, relative)
        if raw is None:
            raise EvolutionError("capability projection drift detected")
        actual_files[relative] = hashlib.sha256(raw).hexdigest()
    if (
        actual_files != projection["files"]
        or _digest(actual_files) != projection["digest"]
    ):
        raise EvolutionError("capability projection drift detected")


def _verify_canonical_source(
    context: WorktreeContext, run: dict[str, Any]
) -> dict[str, Any]:
    source = _read_canonical_source(context, run)
    paths = _capability_paths(run["task_id"], run["capability_name"])
    for host in ("codex", "claude"):
        package = compile_evolution_capability(source, host)
        files = {
            relative: hashlib.sha256(content.encode("utf-8")).hexdigest()
            for relative, content in package.items()
        }
        if files != run["projection"]["hosts"][host]["files"]:
            raise EvolutionError("canonical capability projection drift detected")
        verify_evolution_projection(source, host, context.root / paths[host])
    return source


def _read_canonical_source(
    context: WorktreeContext, run: dict[str, Any]
) -> dict[str, Any]:
    paths = _capability_paths(run["task_id"], run["capability_name"])
    path = context.root / paths["canonical"]
    source = read_bounded_json_object(path, 256 * 1024, max_nodes=8_000, max_depth=16)
    expected = _canonical_text(source) + "\n"
    if _digest(source) != run["canonical"]["source_digest"] or read_bounded_bytes(
        path, 256 * 1024
    ) != expected.encode("utf-8"):
        raise EvolutionError("canonical capability source drift detected")
    return source


def apply_capability(
    context: WorktreeContext,
    source: dict[str, Any],
    *,
    task_id: str,
    strategy: str,
    expected_mode: str,
    actor: str,
) -> dict[str, Any]:
    if strategy not in {"adapt", "build"}:
        raise EvolutionError("evolution strategy is invalid")
    path = _evolution_path(context, task_id)
    with bounded_file_lock(_task_dir(context, task_id) / "run.lock"):
        run, _ = _load_evolution_run(
            context, task_id, expected_mode=expected_mode, actor=actor
        )
        expected_state = f"{strategy}-ready"
        if (
            run.get("schema") != "harness.evolution-run/v1"
            or run.get("state") != expected_state
        ):
            raise EvolutionError(
                f"Evolution {strategy.title()} is not allowed in this state"
            )
        _fixed_artifacts_are_current(context, run)
        _assert_frozen_baseline(context, run)
        paths = _capability_paths(task_id, run["capability_name"])
        _assert_tracked_targets(context, paths)
        if (
            _git_bytes(
                context.root, "status", "--porcelain=v1", "-z", "--untracked-files=all"
            )
            or context.head_sha != run["baseline"]["head_sha"]
        ):
            raise EvolutionError("evolution canonical worktree baseline is stale")
        if strategy == "build":
            if (
                source.get("schema") == "harness.evolution-capability/v2"
                and run.get("search", {}).get("schema") != "harness.evolution-search/v2"
            ):
                raise EvolutionError("surface Build requires v2 Search evidence")
            if (
                source.get("adapted_from") is not None
                or source.get("trust", {}).get("source") != "repository-local-build"
                or source.get("skill", {}).get("invocation", {}).get("mode") != "manual"
            ):
                raise EvolutionError(
                    "Build requires a manual repository-local canonical source"
                )
        else:
            candidate = run.get("candidate")
            adapted = source.get("adapted_from")
            surface_adapt = candidate is not None and "surface" in candidate
            invalid_adapt = (
                candidate is None
                or not isinstance(adapted, dict)
                or adapted.get("source") != candidate["canonical_source"]
                or adapted.get("revision") != candidate["immutable_revision"]
                or source.get("license") != candidate["license"]
                or source.get("skill", {}).get("invocation") != candidate["invocation"]
                or source.get("trust", {}).get("source") != "pinned-adaptation"
            )
            if surface_adapt:
                invalid_adapt = invalid_adapt or (
                    source.get("schema") != "harness.evolution-capability/v2"
                    or source.get("surface") != candidate["surface"]
                    or hashlib.sha256(
                        (_canonical_text(source) + "\n").encode("utf-8")
                    ).hexdigest()
                    != candidate["artifact_digest"]
                    or set(adapted) != {"source", "revision"}
                )
            else:
                invalid_adapt = invalid_adapt or (
                    adapted.get("candidate_id") != candidate["id"]
                    or adapted.get("candidate_digest") != _digest(candidate)
                    or adapted.get("artifact_digest") != candidate["artifact_digest"]
                )
            if invalid_adapt:
                raise EvolutionError(
                    "Adapt source invocation or provenance is not bound to the selected candidate"
                )
        if source.get("name") != run["capability_name"]:
            raise EvolutionError("canonical capability name does not match the run")
        packages = {
            host: compile_evolution_capability(source, host)
            for host in ("codex", "claude")
        }
        projection = _projection_record(source, packages, paths)
        _assert_projection_tracked(context, projection, paths["report"])
        run["strategy"] = strategy
        run["canonical"] = {
            "name": source["name"],
            "version": source["version"],
            "license": source["license"],
            "source_digest": projection["source_digest"],
        }
        if "surface" in source:
            run["canonical"]["surface"] = _surface(source["surface"])
        run["projection"] = projection
        run["projection_digest"] = projection["digest"]
        run["state"] = "applying"
        _write_run(path, run)
        try:
            _clear_managed_files(context, run)
            _write_exact_bounded(
                context.root / paths["canonical"],
                _canonical_text(source) + "\n",
                256 * 1024,
            )
            for host, package in packages.items():
                root = context.root / paths[host]
                for relative, content in package.items():
                    target = root / relative
                    ensure_no_link_components(context.root, target.parent)
                    _write_exact_bounded(target, content, 256 * 1024)
            name = source["name"]
            for host, skill_key in (
                ("codex", "codex_skill"),
                ("claude", "claude_skill"),
            ):
                prefix = f"skills/{name}/"
                for relative, content in packages[host].items():
                    if relative.startswith(prefix):
                        _write_exact_bounded(
                            context.root / paths[skill_key] / relative[len(prefix) :],
                            content,
                            256 * 1024,
                        )
            for host, relative in (
                ("codex", f"agents/{name}.toml"),
                ("claude", f"agents/{name}.md"),
            ):
                _write_exact_bounded(
                    context.root / paths[f"{host}_agent"],
                    packages[host][relative],
                    256 * 1024,
                )
            _verify_recorded_projection(context, projection)
            _verify_canonical_source(context, run)
            _fixed_artifacts_are_current(context, run)
        except (EvolutionError, OSError, ValueError):
            _reject_with_rollback(context, path, run, f"{strategy}-application-failed")
            return {
                "schema": "harness.evolution-control/v1",
                "task_id": task_id,
                "state": "rejected",
                "outcome": "rejected",
            }
        run["state"] = "evaluating"
        _write_run(path, run)
    return {
        "schema": "harness.evolution-control/v1",
        "task_id": task_id,
        "state": "evaluating",
        "strategy": strategy,
        "candidate_digest": projection["source_digest"],
        "projection_digest": projection["digest"],
    }


def _case_result(case_id: str, check: Any) -> dict[str, str]:
    try:
        material = check()
    except (EvolutionError, OSError, ValueError):
        status = "fail"
        material = {"reason": "conformance-failed"}
    else:
        status = "pass"
    return {
        "id": case_id,
        "status": status,
        "evidence_digest": _digest(
            {"case": case_id, "status": status, "material": material}
        ),
    }


def _run_evaluation(context: WorktreeContext, run: dict[str, Any]) -> dict[str, Any]:
    _fixed_artifacts_are_current(context, run)
    source = _read_canonical_source(context, run)
    paths = _capability_paths(run["task_id"], run["capability_name"])

    def canonical_case() -> dict[str, str]:
        _verify_canonical_source(context, run)
        return {"source_digest": run["canonical"]["source_digest"]}

    def discovery_case(host: str) -> dict[str, Any]:
        result = verify_evolution_projection(source, host, context.root / paths[host])
        deployment = paths[f"{host}_agent"]
        raw = read_bounded_bytes(context.root / deployment, 256 * 1024)
        expected = run["projection"]["deployments"][deployment]
        if raw is None or hashlib.sha256(raw).hexdigest() != expected:
            raise EvolutionError(f"{host} Agent deployment drift detected")
        return result

    def read_only_case() -> dict[str, Any]:
        agent = source["agent"]
        if (
            agent["access"] != "read-only"
            or agent["writer_lease_required"] is not True
            or set(agent["capabilities"]) - {"read", "inspect", "report"}
        ):
            raise EvolutionError("Agent is not read-only")
        return {
            "access": agent["access"],
            "capabilities": agent["capabilities"],
        }

    def no_tree_case() -> dict[str, Any]:
        agent = source["agent"]
        if agent["max_children"] != 0 or any(
            item in {"spawn", "delegate"} for item in agent["capabilities"]
        ):
            raise EvolutionError("Agent tree authority is unsafe")
        return {"max_children": 0}

    evaluator_cases = [
        _case_result("canonical-source", canonical_case),
        _case_result("codex-discovery", lambda: discovery_case("codex")),
        _case_result("claude-discovery", lambda: discovery_case("claude")),
    ]
    holdout_cases = [
        _case_result("read-only-agent", read_only_case),
        _case_result("no-agent-tree", no_tree_case),
    ]
    passed = all(
        case["status"] == "pass" for case in (*evaluator_cases, *holdout_cases)
    )
    result = {
        "schema": "harness.evolution-evaluation/v1",
        "candidate_digest": run["canonical"]["source_digest"],
        "evaluator": {
            "id": run["evaluator"]["id"],
            "digest": run["evaluator"]["digest"],
            "cases": evaluator_cases,
        },
        "holdout": {
            "id": run["holdout"]["id"],
            "digest": run["holdout"]["digest"],
            "cases": holdout_cases,
        },
        "smoke": {
            "status": "pass" if passed else "fail",
            "evidence_digest": _digest(
                {"evaluator": evaluator_cases, "holdout": holdout_cases}
            ),
        },
    }
    if "surface" in source:
        surface = _surface(source["surface"])
        adapter_results = {
            adapter: smoke_surface_capability(
                context, name=source["name"], adapter=adapter
            )
            for adapter in SURFACE_ADAPTERS
        }
        result["surface"] = {
            "kind": surface["kind"],
            "adapters": {
                adapter: {
                    "status": item["status"],
                    "hosts": item["hosts"],
                    "evidence_digest": item["evidence_digest"],
                }
                for adapter, item in adapter_results.items()
            },
            "checks": {
                name: (
                    "pass"
                    if all(
                        item["checks"].get(name) == "pass"
                        for item in adapter_results.values()
                    )
                    else "fail"
                )
                for name in _surface_check_names(surface)
            },
            "observations": {
                adapter: item["observations"]
                for adapter, item in adapter_results.items()
            },
        }
    return result


def _validate_stored_evaluation(run: dict[str, Any], value: Any) -> dict[str, Any]:
    surface_run = (
        isinstance(run.get("canonical"), dict) and "surface" in run["canonical"]
    )
    evaluation = _exact(
        value,
        {"schema", "candidate_digest", "evaluator", "holdout", "smoke"}
        | ({"surface"} if surface_run else set()),
        "stored evolution evaluation",
    )
    if (
        evaluation["schema"] != "harness.evolution-evaluation/v1"
        or evaluation["candidate_digest"] != run["canonical"]["source_digest"]
    ):
        raise EvolutionError("stored evolution evaluation is invalid")
    for label, required in (("evaluator", EVALUATOR_CASES), ("holdout", HOLDOUT_CASES)):
        item = _exact(evaluation[label], {"id", "digest", "cases"}, f"stored {label}")
        if (
            item["id"] != run[label]["id"]
            or item["digest"] != run[label]["digest"]
            or not isinstance(item["cases"], list)
            or [case.get("id") for case in item["cases"]] != required
        ):
            raise EvolutionError("stored evolution evaluation is invalid")
        for case in item["cases"]:
            if (
                not isinstance(case, dict)
                or set(case) != {"id", "status", "evidence_digest"}
                or case["status"] not in {"pass", "fail"}
                or not isinstance(case["evidence_digest"], str)
                or not DIGEST_RE.fullmatch(case["evidence_digest"])
            ):
                raise EvolutionError("stored evolution evaluation is invalid")
    smoke = _exact(evaluation["smoke"], {"status", "evidence_digest"}, "stored smoke")
    expected_smoke = _digest(
        {
            "evaluator": evaluation["evaluator"]["cases"],
            "holdout": evaluation["holdout"]["cases"],
        }
    )
    if (
        smoke["status"] not in {"pass", "fail"}
        or smoke["evidence_digest"] != expected_smoke
        or (smoke["status"] == "pass")
        != all(
            case["status"] == "pass"
            for case in (
                *evaluation["evaluator"]["cases"],
                *evaluation["holdout"]["cases"],
            )
        )
    ):
        raise EvolutionError("stored evolution evaluation is invalid")
    if surface_run:
        surface = _surface(run["canonical"]["surface"])
        surface_evidence = _exact(
            evaluation["surface"],
            {"kind", "adapters", "checks", "observations"},
            "stored surface evaluation",
        )
        if (
            surface_evidence["kind"] != surface["kind"]
            or not isinstance(surface_evidence["checks"], dict)
            or set(surface_evidence["checks"]) != set(_surface_check_names(surface))
            or any(
                status not in {"pass", "fail"}
                for status in surface_evidence["checks"].values()
            )
            or not isinstance(surface_evidence["adapters"], dict)
            or set(surface_evidence["adapters"]) != set(SURFACE_ADAPTERS)
            or not isinstance(surface_evidence["observations"], dict)
            or set(surface_evidence["observations"]) != set(SURFACE_ADAPTERS)
        ):
            raise EvolutionError("stored surface evaluation is invalid")
        expected_hosts = {
            "codex-direct": ["codex"],
            "claude-direct": ["claude"],
            "codex-paseo-claude": ["codex", "claude"],
        }
        for adapter, item in surface_evidence["adapters"].items():
            if (
                not isinstance(item, dict)
                or set(item) != {"status", "hosts", "evidence_digest"}
                or item["status"] not in {"pass", "fail"}
                or item["hosts"] != expected_hosts[adapter]
                or not DIGEST_RE.fullmatch(str(item["evidence_digest"]))
            ):
                raise EvolutionError("stored surface evaluation is invalid")
        _safe_persisted_value(surface_evidence["observations"])
    return evaluation


def evaluate_capability(
    context: WorktreeContext,
    value: dict[str, Any],
    *,
    task_id: str,
    expected_mode: str,
    actor: str,
) -> dict[str, Any]:
    request = _exact(
        value,
        {"schema", "candidate_digest"},
        "evolution evaluation request",
    )
    if request["schema"] != "harness.evolution-evaluation-request/v1":
        raise EvolutionError("evolution evaluation request is invalid")
    path = _evolution_path(context, task_id)
    with bounded_file_lock(_task_dir(context, task_id) / "run.lock"):
        run, _ = _load_evolution_run(
            context,
            task_id,
            expected_mode=expected_mode,
            actor=actor,
            verify_fixed=False,
        )
        if (
            run.get("schema") != "harness.evolution-run/v1"
            or run.get("state") != "evaluating"
        ):
            raise EvolutionError("Evolution evaluation is not allowed in this state")
        if request["candidate_digest"] != run["canonical"]["source_digest"]:
            raise EvolutionError("evaluation is not bound to the active candidate")
        try:
            normalized = _run_evaluation(context, run)
        except (EvolutionError, OSError, ValueError):
            normalized = {
                "schema": "harness.evolution-evaluation/v1",
                "candidate_digest": run["canonical"]["source_digest"],
                "evaluator": {
                    "id": run["evaluator"]["id"],
                    "digest": run["evaluator"]["digest"],
                    "cases": [
                        {
                            "id": case,
                            "status": "fail",
                            "evidence_digest": _digest(
                                {
                                    "case": case,
                                    "status": "fail",
                                    "material": {"reason": "setup-failed"},
                                }
                            ),
                        }
                        for case in EVALUATOR_CASES
                    ],
                },
                "holdout": {
                    "id": run["holdout"]["id"],
                    "digest": run["holdout"]["digest"],
                    "cases": [
                        {
                            "id": case,
                            "status": "fail",
                            "evidence_digest": _digest(
                                {
                                    "case": case,
                                    "status": "fail",
                                    "material": {"reason": "setup-failed"},
                                }
                            ),
                        }
                        for case in HOLDOUT_CASES
                    ],
                },
                "smoke": {"status": "fail", "evidence_digest": ""},
            }
            normalized["smoke"]["evidence_digest"] = _digest(
                {
                    "evaluator": normalized["evaluator"]["cases"],
                    "holdout": normalized["holdout"]["cases"],
                }
            )
            if "surface" in run["canonical"]:
                surface = _surface(run["canonical"]["surface"])
                normalized["surface"] = {
                    "kind": surface["kind"],
                    "adapters": {
                        adapter: {
                            "status": "fail",
                            "hosts": (
                                ["codex", "claude"]
                                if adapter == "codex-paseo-claude"
                                else [
                                    "codex" if adapter == "codex-direct" else "claude"
                                ]
                            ),
                            "evidence_digest": _digest(
                                {
                                    "adapter": adapter,
                                    "status": "fail",
                                    "reason": "setup-failed",
                                }
                            ),
                        }
                        for adapter in SURFACE_ADAPTERS
                    },
                    "checks": {name: "fail" for name in _surface_check_names(surface)},
                    "observations": {
                        adapter: {"reason": "setup-failed"}
                        for adapter in SURFACE_ADAPTERS
                    },
                }
        passed = normalized["smoke"]["status"] == "pass" and (
            "surface" not in normalized
            or (
                all(
                    item["status"] == "pass"
                    for item in normalized["surface"]["adapters"].values()
                )
                and all(
                    status == "pass"
                    for status in normalized["surface"]["checks"].values()
                )
            )
        )
        if passed:
            run["evaluation"] = normalized
            run["state"] = "promotion-ready"
            run["outcome"] = "promotable"
            run["outcome_reason"] = "independent-evaluation-passed"
        else:
            _reject_with_rollback(
                context,
                path,
                run,
                "evaluation-or-holdout-failed",
                evaluation=normalized,
            )
            return {
                "schema": "harness.evolution-control/v1",
                "task_id": task_id,
                "state": "rejected",
                "outcome": "rejected",
                "evaluation_digest": _digest(normalized),
                "rollback_status": "restored",
            }
        _write_report(context, run)
        _write_run(path, run)
    return {
        "schema": "harness.evolution-control/v1",
        "task_id": task_id,
        "state": run["state"],
        "outcome": run["outcome"],
        "evaluation_digest": _digest(normalized),
        "rollback_status": "not-required",
    }


def record_search(
    context: WorktreeContext,
    value: dict[str, Any],
    *,
    task_id: str,
    expected_mode: str,
    actor: str,
) -> dict[str, Any]:
    search = _validate_search(value)
    path = _evolution_path(context, task_id)
    with bounded_file_lock(_task_dir(context, task_id) / "run.lock"):
        run, _ = _load_evolution_run(
            context, task_id, expected_mode=expected_mode, actor=actor
        )
        if search["installed_catalog"] != _installed_catalog_evidence(expected_mode):
            raise EvolutionError("installed capability catalog evidence is not current")
        if (
            run.get("schema") != "harness.evolution-run/v1"
            or run.get("task_id") != task_id
        ):
            raise EvolutionError("Evolution Run is unavailable")
        if run.get("state") == "authorization-required" and run.get("search") == search:
            candidate = run["candidate"]
            if candidate is None:
                raise EvolutionError("Evolution Run state is invalid")
            return {
                "schema": "harness.evolution-control/v1",
                "task_id": task_id,
                "state": "authorization-required",
                "decision": search["decision"],
                "candidate_id": search["selected_candidate"],
                "requires_user": True,
                "outcome": run["outcome"],
                "authorization": _authorization(candidate, run["source_verification"]),
            }
        if run.get("state") != "search-required":
            raise EvolutionError("Evolution Search is not allowed in this state")
        candidate = next(
            (
                item
                for item in search["candidates"]
                if item["id"] == search["selected_candidate"]
            ),
            None,
        )
        run["search"] = search
        run["candidate"] = candidate
        run["source_verification"] = None
        if candidate is None and search["decision"] != "build":
            raise EvolutionError("Evolution Search requires a selected candidate")
        if candidate is not None:
            run["source_verification"] = _verify_pinned_candidate(candidate, search)
        elif search["schema"] == "harness.evolution-search/v2":
            _verify_search_channels(search, None)
        if search["decision"] == "deferred":
            run["state"] = "deferred"
            run["outcome"] = "deferred"
            _write_report(context, run)
        elif search["decision"] == "build":
            if candidate is not None and _auto_safe(
                candidate, run["source_verification"]
            ):
                raise EvolutionError("a safe Adapt candidate is available")
            run["state"] = "build-ready"
        elif candidate is not None:
            if _auto_safe(candidate, run["source_verification"]):
                run["state"] = "adapt-ready"
            else:
                run["state"] = "authorization-required"
                run["outcome"] = "deferred"
                _write_report(context, run)
        _write_run(path, run)
    return {
        "schema": "harness.evolution-control/v1",
        "task_id": task_id,
        "state": run["state"],
        "decision": search["decision"],
        "candidate_id": search["selected_candidate"],
        "requires_user": run["state"] == "authorization-required",
        "outcome": run["outcome"],
        "authorization": (
            _authorization(candidate, run["source_verification"])
            if run["state"] == "authorization-required" and candidate is not None
            else None
        ),
    }


def _evolution_contract_name(task_id: str, contract: dict[str, Any]) -> str | None:
    owned = set(contract["plan"]["owned_paths"])
    folded_owned = {path.casefold() for path in owned}
    names = {
        match.group(1)
        for path in folded_owned
        if (
            match := re.fullmatch(
                r"harness/capability-packages/([a-z0-9][a-z0-9-]{0,63})/", path
            )
        )
    }
    evolution_roots = (
        "harness/capability-packages/",
        "docs/agent-memory/evolution-reports/",
        ".agents/skills/",
        ".claude/skills/",
        ".codex/agents/",
        ".claude/agents/",
    )
    has_evolution_path = any(
        _overlaps(path, root) for path in folded_owned for root in evolution_roots
    )
    if not names:
        if has_evolution_path:
            raise EvolutionError("Evolution contract owned paths are invalid")
        return None
    if len(names) != 1:
        raise EvolutionError("Evolution contract owned paths are invalid")
    name = next(iter(names))
    if owned != _required_owned_paths(task_id, name):
        raise EvolutionError("Evolution contract owned paths are invalid")
    return name


def ensure_evolution_acceptance(
    context: WorktreeContext, *, task_id: str, expected_mode: str
) -> dict[str, Any]:
    """Fail closed before public Direct verification, acceptance, or commit."""

    _, direct = _load_run(context, task_id, expected_mode=expected_mode)
    capability_name = _evolution_contract_name(task_id, direct["contract"])
    path = _evolution_path(context, task_id)
    if capability_name is None:
        if path.exists() or path.is_symlink():
            raise EvolutionError("unexpected Evolution state exists for this task")
        return {"required": False}
    if not path.exists() and not path.is_symlink():
        raise EvolutionError("required Evolution state is missing")
    with bounded_file_lock(_task_dir(context, task_id) / "run.lock"):
        run, _ = _load_evolution_run(
            context, task_id, expected_mode=expected_mode, verify_fixed=False
        )
        if run["capability_name"] != capability_name:
            raise EvolutionError("Evolution state does not match its task contract")
        if run["state"] not in {"promotion-ready", "deferred", "rejected"}:
            raise EvolutionError("Evolution Run is not ready for Direct acceptance")
        zero_candidate_build = (
            run["search"]["decision"] == "build"
            and not run["search"]["candidates"]
            and run["search"]["selected_candidate"] is None
            and run["candidate"] is None
            and run["source_verification"] is None
        )
        if (
            zero_candidate_build
            and run["search"]["schema"] == "harness.evolution-search/v2"
        ):
            _verify_search_channels(run["search"], None)
        elif not zero_candidate_build and (
            run["candidate"] is None
            or _verify_pinned_candidate(run["candidate"], run["search"])
            != run["source_verification"]
        ):
            raise EvolutionError("Evolution Search evidence is stale or unauthentic")
        paths = _capability_paths(task_id, capability_name)
        _assert_tracked_targets(context, paths)
        if run["state"] == "promotion-ready":
            try:
                _assert_projection_tracked(context, run["projection"], paths["report"])
                _fixed_artifacts_are_current(context, run)
                _verify_recorded_projection(context, run["projection"])
                _verify_canonical_source(context, run)
                current_evaluation = _run_evaluation(context, run)
                if current_evaluation != run["evaluation"]:
                    raise EvolutionError("Evolution evaluation is stale or unauthentic")
            except EvolutionAdapterError:
                raise
            except (EvolutionError, OSError, ValueError):
                _reject_with_rollback(
                    context,
                    path,
                    run,
                    "terminal-revalidation-failed",
                    evaluation=run["evaluation"],
                )
        else:
            _assert_frozen_baseline(context, run)
        expected_report = _canonical_text(_evolution_report(run)).encode("utf-8")
        if _read_single_link_file(context, paths["report"]) != expected_report:
            raise EvolutionError("Evolution report is missing or stale")
    return {
        "required": True,
        "state": run["state"],
        "outcome": run["outcome"],
        "report_digest": hashlib.sha256(expected_report).hexdigest(),
        "changed_paths": _changed_paths(context.root),
    }


def start_evolution(
    context: WorktreeContext,
    request: dict[str, Any],
    *,
    task_id: str,
    expected_mode: str,
    actor: str,
) -> dict[str, Any]:
    """Validate the accepted-gap gate before an Evolution Run can start."""

    if not isinstance(task_id, str) or not TASK_RE.fullmatch(task_id):
        raise EvolutionError("evolution task identity is invalid")
    if not isinstance(request, dict) or set(request) != {
        "schema",
        "gap_id",
        "capability_name",
        "evaluator",
        "holdout",
        "rollback",
    }:
        raise EvolutionError("evolution request is invalid")
    if request["schema"] != "harness.evolution-request/v1":
        raise EvolutionError("evolution request schema is unsupported")
    gap_id = request["gap_id"]
    if not isinstance(gap_id, str) or not re.fullmatch(r"mem-[0-9a-f]{64}", gap_id):
        raise EvolutionError("capability gap identity is invalid")
    capability_name = _nonempty(request["capability_name"], "capability name", 64)
    paths = _capability_paths(task_id, capability_name)
    evaluator = _fixed_artifact(request["evaluator"], "evaluator")
    holdout = _fixed_artifact(request["holdout"], "holdout")
    if (
        evaluator["path"].casefold() == holdout["path"].casefold()
        or evaluator["digest"] == holdout["digest"]
    ):
        raise EvolutionError("evaluator and holdout must be independent")
    if any(
        _path_is_owned(
            artifact["path"], list(_required_owned_paths(task_id, capability_name))
        )
        for artifact in (evaluator, holdout)
    ):
        raise EvolutionError("evaluator and holdout must be outside Evolution outputs")
    if request["rollback"] != "git-head-snapshot":
        raise EvolutionError("evolution rollback plan is unsupported")

    try:
        records = startup_memory(context)["records"]
    except MemoryProjectionError as exc:
        raise EvolutionError("accepted current capability gap is unavailable") from exc
    gap = next(
        (
            record
            for record in records
            if record.get("record_id") == gap_id
            and record.get("type") == "capability-gap"
            and record.get("validation") == "accepted"
            and record.get("validity", {}).get("to") is None
        ),
        None,
    )
    if gap is None:
        raise EvolutionError("accepted current capability gap is unavailable")

    task_dir = _task_dir(context, task_id)
    ensure_no_link_components(context.root, task_dir)
    with bounded_file_lock(task_dir / "run.lock"):
        _, direct = _load_run(context, task_id, expected_mode=expected_mode)
        contract = direct["contract"]
        mode = contract["execution"]["mode"]
        writer = _require_writer_actor(mode, actor)
        owned = contract["plan"]["owned_paths"]
        required_owned = _required_owned_paths(task_id, capability_name)
        if (
            context.git_dir.resolve() == context.common_git_dir.resolve()
            or direct["state"] not in {"executing", "repairing"}
            or writer is None
            or contract["writer_lease"] != {"holder": writer, "state": "active"}
            or set(owned) != required_owned
            or any(_path_is_owned(item["path"], owned) for item in (evaluator, holdout))
        ):
            raise EvolutionError(
                "evolution requires an active independent Direct writer with exact owned paths"
            )
        _assert_tracked_targets(context, paths)
        report_target = context.root / paths["report"]
        if report_target.exists() or report_target.is_symlink():
            raise EvolutionError("Evolution report already exists for this task")
        if context.head_sha != contract["execution"]["base_sha"] or _git_bytes(
            context.root, "status", "--porcelain=v1", "-z", "--untracked-files=all"
        ):
            raise EvolutionError("evolution canonical worktree baseline is stale")

        for artifact in (evaluator, holdout):
            raw = _read_single_link_file(context, artifact["path"])
            tracked = _git_bytes(context.root, "ls-files", "-z", "--", artifact["path"])
            if (
                raw is None
                or tracked != artifact["path"].encode("utf-8") + b"\0"
                or hashlib.sha256(raw).hexdigest() != artifact["digest"]
            ):
                raise EvolutionError("active evaluator or holdout is not fixed in HEAD")
        evaluator_descriptor = read_bounded_json_object(
            context.root / evaluator["path"], 64 * 1024, max_nodes=256, max_depth=6
        )
        holdout_descriptor = read_bounded_json_object(
            context.root / holdout["path"], 64 * 1024, max_nodes=256, max_depth=6
        )
        for label, descriptor, expected_schema in (
            ("evaluator", evaluator_descriptor, "harness.evolution-evaluator/v1"),
            ("holdout", holdout_descriptor, "harness.evolution-holdout/v1"),
        ):
            if (
                set(descriptor) != {"schema", "id", "required_cases"}
                or descriptor["schema"] != expected_schema
                or not isinstance(descriptor["id"], str)
                or not re.fullmatch(r"[A-Za-z0-9_.-]{1,96}", descriptor["id"])
            ):
                raise EvolutionError(f"active {label} descriptor is invalid")
            _string_list(descriptor["required_cases"], f"{label} required cases")
        if evaluator_descriptor["id"] == holdout_descriptor["id"]:
            raise EvolutionError("evaluator and holdout must be independent")
        if (
            evaluator_descriptor["required_cases"] != EVALUATOR_CASES
            or holdout_descriptor["required_cases"] != HOLDOUT_CASES
            or evaluator_descriptor["id"].casefold()
            == holdout_descriptor["id"].casefold()
        ):
            raise EvolutionError("active evaluator or holdout cases are unsupported")
        evaluator = {
            **evaluator,
            "id": evaluator_descriptor["id"],
            "required_cases": evaluator_descriptor["required_cases"],
        }
        holdout = {
            **holdout,
            "id": holdout_descriptor["id"],
            "required_cases": holdout_descriptor["required_cases"],
        }

        provenance = gap.get("provenance")
        gap_state = {
            "record_id": gap_id,
            "evidence_digest": gap["evidence_digest"],
            "origins": [
                {
                    "task_id": item["task_id"],
                    "commit_sha": item["commit_sha"],
                    "evidence_digest": item["evidence_digest"],
                }
                for item in provenance or []
            ],
        }
        _verify_gap_gate(context, task_id, gap_state)

        evolution_path = task_dir / "evolution.json"
        if evolution_path.exists() or evolution_path.is_symlink():
            raise EvolutionError("Evolution Run already exists for this task")
        run = {
            "schema": "harness.evolution-run/v1",
            "task_id": task_id,
            "mode": mode,
            "writer": writer,
            "state": "search-required",
            "capability_name": capability_name,
            "gap": gap_state,
            "baseline": {
                "head_sha": context.head_sha,
                "branch": contract["execution"]["branch"],
            },
            "evaluator": evaluator,
            "holdout": holdout,
            "outputs": {"codex": paths["codex"], "claude": paths["claude"]},
            "canonical_path": paths["canonical"],
            "report_path": paths["report"],
            "rollback": "git-head-snapshot",
            "search": None,
            "candidate": None,
            "source_verification": None,
            "projection_digest": None,
            "evaluation": None,
            "outcome": None,
            "outcome_reason": None,
            "strategy": None,
            "canonical": None,
            "projection": None,
        }
        run["baseline"]["entries"] = _baseline_entries(
            context,
            context.head_sha,
            [
                paths["package"],
                paths["codex_skill"],
                paths["claude_skill"],
                paths["codex_agent"],
                paths["claude_agent"],
            ],
        )
        _assert_frozen_baseline(context, run)
        _write_run(evolution_path, run)
    return {
        "schema": "harness.evolution-control/v1",
        "task_id": task_id,
        "state": "search-required",
        "gap_id": gap_id,
        "evaluator": evaluator,
        "holdout": holdout,
        "capability_name": capability_name,
        "outputs": {"codex": paths["codex"], "claude": paths["claude"]},
        "canonical_path": paths["canonical"],
        "report_path": paths["report"],
        "rollback": "git-head-snapshot",
    }
