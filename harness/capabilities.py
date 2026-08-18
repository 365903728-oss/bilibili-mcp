"""Adapter diagnostics and native-manual-skill gates."""

from __future__ import annotations

import hashlib
import itertools
import json
import re
import shutil
import tomllib
from pathlib import Path
from typing import Any

from harness.contracts import EXECUTION_MODES
from harness.safe_io import (
    bounded_file_lock,
    ensure_no_link_components,
    read_bounded_json_object,
    safe_label,
    write_bounded_text,
)


MAX_MANUAL_SKILL_REMINDERS = 512


def _skill_names(root: Path) -> list[str]:
    if not root.is_dir():
        return []
    return sorted(
        path.parent.name
        for path in root.glob("*/SKILL.md")
        if path.is_file() and not path.is_symlink()
    )[:512]


def _manual_skill_names(root: Path) -> list[str]:
    names: list[str] = []
    if not root.is_dir():
        return names
    for skill_file in sorted(root.glob("*/SKILL.md"))[:512]:
        if not skill_file.is_file() or skill_file.is_symlink() or skill_file.stat().st_size > 256 * 1024:
            continue
        try:
            body = skill_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        openai_meta = skill_file.parent / "agents" / "openai.yaml"
        openai_body = ""
        if openai_meta.is_file() and not openai_meta.is_symlink() and openai_meta.stat().st_size <= 64 * 1024:
            try:
                openai_body = openai_meta.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                pass
        if re.search(r"(?m)^disable-model-invocation:\s*true\s*$", body) or re.search(
            r"(?m)^\s*allow_implicit_invocation:\s*false\s*$", openai_body
        ):
            names.append(skill_file.parent.name)
    return sorted(set(names))


def _agent_names(root: Path, suffix: str) -> list[str]:
    if not root.is_dir():
        return []
    return sorted(path.stem for path in root.glob(f"*{suffix}") if path.is_file())[:128]


def _hook_profile_from_mapping(hooks: Any) -> dict[str, int]:
    if not isinstance(hooks, dict):
        return {}
    profile: dict[str, int] = {}
    for event, entries in list(hooks.items())[:128]:
        if not isinstance(event, str):
            continue
        if not isinstance(entries, list):
            continue
        count = 0
        for entry in entries[:128]:
            if not isinstance(entry, dict):
                continue
            commands = entry.get("hooks")
            if not isinstance(commands, list):
                continue
            count += sum(
                1
                for command in commands[:128]
                if isinstance(command, dict) and command.get("type") == "command"
            )
        if count:
            profile[event] = count
    return profile


def _json_hook_profile(path: Path) -> dict[str, int]:
    return _hook_profile_from_mapping(
        read_bounded_json_object(path, 256 * 1024).get("hooks")
    )


def _toml_hook_profile(path: Path) -> dict[str, int]:
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 256 * 1024:
        return {}
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return {}
    return _hook_profile_from_mapping(data.get("hooks"))


def _merged_hook_profile(*profiles: dict[str, int]) -> dict[str, int]:
    merged: dict[str, int] = {}
    for profile in profiles:
        for event, count in profile.items():
            merged[event] = merged.get(event, 0) + count
    return merged


def doctor_report(
    repo_root: Path,
    *,
    home: Path | None = None,
    common_git_dir: Path | None = None,
) -> dict[str, Any]:
    home = home or Path.home()
    shared_skills_root = home / ".agents" / "skills"
    codex_native_skills_root = home / ".codex" / "skills"
    claude_skills_root = home / ".claude" / "skills"
    shared_skills = _skill_names(shared_skills_root)
    codex_native_skills = _skill_names(codex_native_skills_root)
    codex_skills = sorted(set(shared_skills + codex_native_skills))
    manual = sorted(
        set(
            _manual_skill_names(shared_skills_root)
            + _manual_skill_names(codex_native_skills_root)
            + _manual_skill_names(claude_skills_root)
        )
    )
    tracked_claude_profile = _json_hook_profile(repo_root / ".claude" / "settings.json")
    local_claude_profile = _json_hook_profile(repo_root / ".claude" / "settings.local.json")
    tracked_claude_hooks = sum(tracked_claude_profile.values())
    local_claude_hooks = sum(local_claude_profile.values())
    claude_local_conflict = tracked_claude_hooks > 0 and local_claude_hooks > 0

    tracked_codex_profile = _json_hook_profile(repo_root / ".codex" / "hooks.json")
    primary_codex_profile: dict[str, int] = {}
    if common_git_dir is not None:
        resolved_common = common_git_dir.resolve()
        primary_root = resolved_common.parent if resolved_common.name.lower() == ".git" else repo_root
        if primary_root.resolve() != repo_root.resolve():
            primary_codex_profile = _json_hook_profile(primary_root / ".codex" / "hooks.json")
    user_codex_profile = _merged_hook_profile(
        _json_hook_profile(home / ".codex" / "hooks.json"),
        _toml_hook_profile(home / ".codex" / "config.toml"),
    )
    external_codex_profile = _merged_hook_profile(
        primary_codex_profile, user_codex_profile
    )
    codex_external_conflict = bool(
        set(tracked_codex_profile).intersection(external_codex_profile)
    )
    return {
        "schema": "harness.doctor/v1",
        "status": (
            "action-required"
            if claude_local_conflict or codex_external_conflict
            else "ready"
        ),
        "adapters": [
            {
                "mode": mode,
                "contract_status": "declared",
                "entrypoint": "claude" if mode == "claude-direct" else "codex",
            }
            for mode in EXECUTION_MODES
        ],
        "clients": {
            "codex_cli": shutil.which("codex") is not None,
            "claude_cli": shutil.which("claude") is not None,
            "paseo_cli": shutil.which("paseo") is not None,
        },
        "capabilities": {
            "codex_skills": codex_skills,
            "shared_agent_skills": shared_skills,
            "codex_native_skills": codex_native_skills,
            "claude_skills": _skill_names(claude_skills_root),
            "manual_skills": manual,
            "codex_agents": _agent_names(repo_root / ".codex" / "agents", ".toml"),
            "claude_agents": _agent_names(repo_root / ".claude" / "agents", ".md"),
        },
        "rules": {
            "shared": (repo_root / "RULES.md").is_file(),
            "codex_adapter": (repo_root / "AGENTS.md").is_file(),
            "claude_adapter": (repo_root / "CLAUDE.md").is_file(),
        },
        "hooks": {
            "tracked_codex_commands": sum(tracked_codex_profile.values()),
            "primary_codex_commands": sum(primary_codex_profile.values()),
            "user_codex_commands": sum(user_codex_profile.values()),
            "codex_external_conflict": codex_external_conflict,
            "tracked_claude_commands": tracked_claude_hooks,
            "local_claude_commands": local_claude_hooks,
            "claude_local_conflict": claude_local_conflict,
            "migration": (
                "Review or migrate overlapping external hooks before enabling the tracked adapters."
                if claude_local_conflict or codex_external_conflict
                else None
            ),
        },
    }


def check_manual_skill(
    *,
    runtime_root: Path,
    task_id: str,
    adapter: str,
    host: str | None = None,
    skill: str,
    invoked: bool,
    worktree_root: Path | None = None,
) -> dict[str, Any]:
    if adapter not in EXECUTION_MODES:
        raise ValueError("unsupported execution adapter")
    expected_host = {
        "codex-direct": "codex",
        "claude-direct": "claude",
    }.get(adapter)
    if expected_host is not None:
        host = host or expected_host
        if host != expected_host:
            raise ValueError("manual skill host does not match the direct adapter")
    elif host not in {"codex", "claude"}:
        raise ValueError("collaboration manual skill requires an explicit host")
    reminder_id = manual_skill_reminder_id(
        task_id=task_id,
        adapter=adapter,
        host=host,
        skill=skill,
    )
    prefix = "/" if host == "claude" else "$"
    native = f"{prefix}{skill}"
    base = {
        "schema": "harness.manual-skill-gate/v1",
        "task_id": task_id,
        "adapter": adapter,
        "host": host,
        "skill": skill,
        "native_invocation": native,
    }
    if invoked:
        return {**base, "status": "invoked", "message": None}

    marker_dir = runtime_root / "manual-skill-reminders"
    marker = marker_dir / f"{reminder_id}.json"
    ensure_no_link_components(worktree_root or runtime_root, marker_dir)
    row = {"schema": "harness.manual-skill-reminder/v1", "reminder_id": reminder_id}
    with bounded_file_lock(marker_dir / ".markers.lock"):
        existing = read_bounded_json_object(marker, 1024)
        if existing == row:
            return {**base, "status": "already-reminded", "message": None}
        if marker.exists() or marker.is_symlink():
            raise ValueError("manual skill reminder marker is invalid")
        markers = list(
            itertools.islice(marker_dir.glob("*.json"), MAX_MANUAL_SKILL_REMINDERS + 1)
        )
        if len(markers) >= MAX_MANUAL_SKILL_REMINDERS:
            raise ValueError("manual skill reminder capacity is exhausted")
        write_bounded_text(
            marker,
            json.dumps(row, ensure_ascii=True, sort_keys=True, separators=(",", ":")),
            1024,
        )
        if read_bounded_json_object(marker, 1024) != row:
            raise ValueError("manual skill reminder marker was not durable")
    return {
        **base,
        "status": "reminder-emitted",
        "message": (
            f"Manual skill required: invoke {native} manually before implementation writes. "
            "The Harness will not imitate or invoke the skill."
        ),
    }


def manual_skill_reminder_id(
    *, task_id: str, adapter: str, host: str, skill: str
) -> str:
    values = ((task_id, 128), (adapter, 64), (host, 16), (skill, 64))
    if any(not isinstance(value, str) or not 1 <= len(value) <= limit for value, limit in values):
        raise ValueError("manual skill reminder identity is invalid")
    if safe_label(skill, "skill", 64) != skill:
        raise ValueError("manual skill name is not a native invocation identifier")
    digest = hashlib.sha256(b"manual-skill-reminder-v2")
    for value, _ in values:
        encoded = value.encode("utf-8")
        digest.update(len(encoded).to_bytes(4, "big"))
        digest.update(encoded)
    return digest.hexdigest()[:24]
