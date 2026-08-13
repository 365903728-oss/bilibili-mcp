"""Governed Skill and Agent evolution from accepted typed capability gaps."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import tempfile
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
    bounded_file_lock,
    ensure_no_link_components,
    read_bounded_bytes,
    read_bounded_json_object,
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
        _ignored_path(context, path)
        for path in (*projection["files"], report_path)
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


def _validate_candidate(value: Any) -> dict[str, Any]:
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
        },
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
        compatibility["hosts"] != ["codex", "claude"]
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
    effects = _exact(
        candidate["effects"],
        {"credentials", "elevation", "daemon", "open_port", "global_policy"},
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
    _safe_persisted_value(normalized)
    return normalized


def _auto_safety_blocks(candidate: dict[str, Any]) -> list[str]:
    blocks: list[str] = []
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
        for effect, required in candidate["effects"].items()
        if required
    )
    if candidate["network"] == "read-only-https" and candidate["data"] != "none":
        blocks.append("network-data-boundary")
    if set(candidate["permissions"]) - {"none", "read-repository"}:
        blocks.append("runtime-write-permission")
    # Candidate compatibility, smoke, and installed provenance arrive as
    # untrusted Search data until a separate trusted evidence provider exists.
    blocks.append("trusted-machine-evidence-unavailable")
    return blocks


def _auto_safe(candidate: dict[str, Any]) -> bool:
    return not _auto_safety_blocks(candidate)


def _verify_pinned_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    repository = candidate["canonical_source"].removeprefix("https://github.com/")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    observations: dict[str, Any] = {}
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
        request = urllib.request.Request(
            url, headers={"User-Agent": "bilibili-mcp-harness-evolution/1"}
        )
        try:
            with opener.open(request, timeout=20) as response:
                raw = response.read(256 * 1024 + 1)
                if response.status != 200 or response.geturl() != url:
                    raise EvolutionError("pinned candidate source redirected or failed")
        except (OSError, urllib.error.URLError) as exc:
            raise EvolutionError(
                "pinned candidate source could not be verified"
            ) from exc
        observed = hashlib.sha256(raw).hexdigest()
        if (
            len(raw) > 256 * 1024
            or observed != candidate[digest_key]
            or manifest[relative]["digest"] != observed
            or manifest[relative]["bytes"] != len(raw)
        ):
            raise EvolutionError("pinned candidate source does not match its record")
        observations[label] = {
            "path": relative,
            "digest": observed,
            "bytes": len(raw),
        }
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
    material = {
        "source": candidate["canonical_source"],
        "revision": candidate["immutable_revision"],
        "observations": observations,
    }
    return {
        "schema": "harness.evolution-source-verification/v1",
        **material,
        "evidence_digest": _digest(material),
    }


def _authorization(candidate: dict[str, Any]) -> dict[str, Any]:
    candidate_digest = _digest(candidate)
    return {
        "schema": "harness.evolution-authorization/v1",
        "request_id": f"evolution-auth-{candidate_digest[:24]}",
        "candidate_id": candidate["id"],
        "candidate_digest": candidate_digest,
        "blocks": _auto_safety_blocks(candidate),
        "alternatives": ["defer", "build-repository-local"],
    }


def _validate_search(value: Any) -> dict[str, Any]:
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
        },
        "evolution search",
    )
    if search["schema"] != "harness.evolution-search/v1":
        raise EvolutionError("evolution search schema is unsupported")
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
    raw_sources = search["sources_consulted"]
    if not isinstance(raw_sources, list) or not 1 <= len(raw_sources) <= 32:
        raise EvolutionError(
            "Evolution Search requires official or live GitHub evidence"
        )
    sources: list[dict[str, Any]] = []
    for raw_source in raw_sources:
        item = _exact(
            raw_source,
            {
                "canonical_source",
                "immutable_revision",
                "artifact_path",
                "artifact_digest",
                "license_path",
                "license_digest",
                "result",
            },
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
        if (
            not re.fullmatch(
                r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+",
                source["canonical_source"],
            )
            or not re.fullmatch(r"[0-9a-f]{40}", str(source["immutable_revision"]))
            or not DIGEST_RE.fullmatch(str(source["artifact_digest"]))
            or not DIGEST_RE.fullmatch(str(source["license_digest"]))
            or source["result"] not in {"candidate", "no-match", "rejected"}
        ):
            raise EvolutionError("evolution source evidence is invalid")
        sources.append(source)
    if len({_digest(item) for item in sources}) != len(sources):
        raise EvolutionError("evolution source evidence is duplicated")
    for candidate in candidates:
        if not any(
            source["result"] == "candidate"
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
    if not candidates or selected not in candidate_ids:
        raise EvolutionError("evolution selected candidate is invalid")
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
    _safe_persisted_value(normalized)
    return normalized


def _validate_stored_search(value: Any) -> dict[str, Any]:
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
        },
        "stored evolution search",
    )
    if (
        search["schema"] != "harness.evolution-search/v1"
        or not isinstance(search["query_digest"], str)
        or not DIGEST_RE.fullmatch(search["query_digest"])
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
    if decision not in {"adapt", "build", "deferred"} or not candidates or selected not in candidate_ids:
        raise EvolutionError("stored evolution decision is invalid")
    if not isinstance(search["reason_code"], str) or not re.fullmatch(
        r"[a-z0-9-]{1,96}", search["reason_code"]
    ):
        raise EvolutionError("stored evolution reason is invalid")
    query_probe = {
        "schema": search["schema"],
        "query": "stored-search",
        "installed_catalog": installed,
        "sources_consulted": search["sources_consulted"],
        "candidates": candidates,
        "decision": decision,
        "selected_candidate": selected,
        "reason_code": search["reason_code"],
    }
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
    if any(pattern.search(value) for value in values for pattern in FORBIDDEN_TEXT) or any(
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
        },
        "canonical evolution capability",
    )
    if canonical["schema"] != "harness.evolution-capability/v1":
        raise EvolutionError("canonical capability schema is unsupported")
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
        adapted = _exact(
            canonical["adapted_from"],
            {
                "candidate_id",
                "candidate_digest",
                "source",
                "revision",
                "artifact_digest",
            },
            "adapted capability source",
        )
        if (
            not re.fullmatch(r"[A-Za-z0-9_.-]{1,96}", str(adapted["candidate_id"]))
            or not re.fullmatch(r"[0-9a-f]{64}", str(adapted["candidate_digest"]))
            or not re.fullmatch(
                r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+",
                str(adapted["source"]),
            )
            or not re.fullmatch(r"[0-9a-f]{40}", str(adapted["revision"]))
            or not re.fullmatch(r"[0-9a-f]{64}", str(adapted["artifact_digest"]))
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
    _string_list(interface["operations"], "capability operations")

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
            or message.splitlines().count(
                f"Harness-Task: {_task_key(item['task_id'])}"
            )
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
        if (
            direct["state"] not in {"executing", "repairing"}
            or contract["writer_lease"] != {"holder": writer, "state": "active"}
        ):
            raise EvolutionError("Evolution mutation actor does not hold the writer lease")
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
        if (
            not isinstance(canonical, dict)
            or set(canonical)
            != {
                "name",
                "version",
                "license",
                "source_digest",
            }
            or not isinstance(canonical["name"], str)
            or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", canonical["name"])
            or not isinstance(canonical["version"], str)
            or not re.fullmatch(r"\d+\.\d+\.\d+", canonical["version"])
            or canonical["license"] not in LICENSES
            or canonical["source_digest"] != projection["source_digest"]
        ):
            raise EvolutionError("Evolution Run state is invalid")
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
        if (
            normalized_search != search
            or search["installed_catalog"] != _installed_catalog_evidence(run["mode"])
        ):
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
        decision = search["decision"]
        if (
            (run["state"] == "adapt-ready" and decision != "adapt")
            or (run["state"] == "build-ready" and decision != "build")
            or (run["state"] == "deferred" and decision != "deferred")
            or (
                run["state"] == "authorization-required"
                and (decision != "adapt" or selected is None or _auto_safe(selected))
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
        ) and not _auto_safe(selected):
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
        if verification is None:
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
    return {
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


def _evolution_report(run: dict[str, Any]) -> dict[str, Any]:
    search = run["search"]
    paths = _capability_paths(run["task_id"], run["capability_name"])
    return {
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
            _authorization(run["candidate"])
            if run["candidate"] is not None
            and (
                run["state"] == "authorization-required"
                or search["reason_code"] == "authorization-deferred"
            )
            else None
        ),
    }


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
        ("evaluator", run["evaluator"], "harness.evolution-evaluator/v1", EVALUATOR_CASES),
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
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


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
        path.unlink()
    paths = _capability_paths(run["task_id"], run["capability_name"])
    for raw_root in (paths["package"], paths["codex_skill"], paths["claude_skill"]):
        root = context.root / raw_root
        if root.exists():
            directories = sorted(
                (path for path in root.rglob("*") if path.is_dir()),
                key=lambda item: len(item.parts),
                reverse=True,
            )
            for directory in directories:
                try:
                    directory.rmdir()
                except OSError:
                    pass
            try:
                root.rmdir()
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
                source.get("adapted_from") is not None
                or source.get("trust", {}).get("source") != "repository-local-build"
                or source.get("skill", {}).get("invocation", {}).get("mode")
                != "manual"
            ):
                raise EvolutionError(
                    "Build requires a manual repository-local canonical source"
                )
        else:
            candidate = run.get("candidate")
            adapted = source.get("adapted_from")
            if (
                candidate is None
                or not isinstance(adapted, dict)
                or adapted.get("candidate_id") != candidate["id"]
                or adapted.get("candidate_digest") != _digest(candidate)
                or adapted.get("source") != candidate["canonical_source"]
                or adapted.get("revision") != candidate["immutable_revision"]
                or adapted.get("artifact_digest") != candidate["artifact_digest"]
                or source.get("license") != candidate["license"]
                or source.get("skill", {}).get("invocation") != candidate["invocation"]
                or source.get("trust", {}).get("source") != "pinned-adaptation"
            ):
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
    return result


def _validate_stored_evaluation(run: dict[str, Any], value: Any) -> dict[str, Any]:
    evaluation = _exact(
        value,
        {"schema", "candidate_digest", "evaluator", "holdout", "smoke"},
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
        passed = normalized["smoke"]["status"] == "pass"
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
                "authorization": _authorization(candidate),
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
        if candidate is None:
            raise EvolutionError("Evolution Search requires a selected candidate")
        run["source_verification"] = _verify_pinned_candidate(candidate)
        if search["decision"] == "deferred":
            run["state"] = "deferred"
            run["outcome"] = "deferred"
            _write_report(context, run)
        elif search["decision"] == "build":
            if any(_auto_safe(item) for item in search["candidates"]):
                raise EvolutionError("a safe Adapt candidate is available")
            run["state"] = "build-ready"
        elif candidate is not None:
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
            _authorization(candidate)
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
        if (
            run["candidate"] is None
            or _verify_pinned_candidate(run["candidate"])
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
                    raise EvolutionError(
                        "Evolution evaluation is stale or unauthentic"
                    )
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
