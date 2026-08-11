"""Typed task-contract invariants for the three execution adapters."""

from __future__ import annotations

import copy
import re
from pathlib import PurePath
from typing import Any


EXECUTION_MODES = ("codex-direct", "codex-paseo-claude", "claude-direct")
WRITERS = {
    "codex-direct": "codex",
    "codex-paseo-claude": "claude",
    "claude-direct": "claude",
}
ACCEPTANCE_OWNERS = {
    "codex-direct": "codex",
    "codex-paseo-claude": "codex",
    "claude-direct": "claude",
}
ACTIVE_STATES = (
    "draft",
    "ready",
    "mode-frozen",
    "baselined",
    "executing",
    "verifying",
    "reviewing",
    "repairing",
)
TERMINAL_STATES = ("accepted", "blocked", "cancelled", "recovery-required")
LEASE_STATES = ("inactive", "active", "released")
MANUAL_SKILL_STATES = ("required", "reminded", "invoked")
MANUAL_SKILL_HOSTS = ("codex", "claude")
MODE_MANUAL_SKILL_HOSTS = {
    "codex-direct": {"codex"},
    "codex-paseo-claude": {"codex", "claude"},
    "claude-direct": {"claude"},
}
SHA_RE = re.compile(r"^[0-9a-f]{40}$")

REQUIRED_AUTHORITY = {
    "local_read_write_test": "allowed",
    "local_commit": "after-acceptance",
    "push_pr_tag_release_publish": "user-approval-required",
    "credentials_ssh_broad_delete_history_rewrite": "blocked",
}


class ContractError(ValueError):
    """A task contract violates the Harness constitutional contract."""


def _exact_keys(value: dict[str, Any], allowed: set[str], name: str) -> None:
    unexpected = sorted(set(value) - allowed)
    if unexpected:
        raise ContractError(f"{name} contains unexpected fields")


def _required_keys(value: dict[str, Any], required: set[str], name: str) -> None:
    if required - set(value):
        raise ContractError(f"{name} is missing required fields")


def _mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{name} must be an object")
    return value


def _nonempty(value: Any, name: str, limit: int = 512) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ContractError(f"{name} must be a bounded non-empty string")
    return value.strip()


def validate_task_contract(value: Any) -> dict[str, Any]:
    contract = copy.deepcopy(_mapping(value, "contract"))
    _required_keys(
        contract,
        {
            "schema",
            "task",
            "execution",
            "writer_lease",
            "acceptance_owner",
            "authority",
            "state",
            "terminal_states",
            "required_manual_skills",
        },
        "contract",
    )
    _exact_keys(
        contract,
        {
            "schema",
            "task",
            "execution",
            "writer_lease",
            "acceptance_owner",
            "authority",
            "state",
            "terminal_states",
            "required_manual_skills",
        },
        "contract",
    )
    if contract.get("schema") != "harness.task-contract/v1":
        raise ContractError("unsupported task contract schema")

    task = _mapping(contract.get("task"), "task")
    _required_keys(task, {"id", "source"}, "task")
    _exact_keys(task, {"id", "source"}, "task")
    _nonempty(task.get("id"), "task.id", 128)
    _nonempty(task.get("source"), "task.source", 2048)

    execution = _mapping(contract.get("execution"), "execution")
    _required_keys(
        execution,
        {"mode", "canonical_worktree", "base_sha", "adapter_switch_policy"},
        "execution",
    )
    _exact_keys(
        execution,
        {"mode", "canonical_worktree", "base_sha", "adapter_switch_policy"},
        "execution",
    )
    mode = execution.get("mode")
    if mode not in EXECUTION_MODES:
        raise ContractError("execution mode is invalid")
    worktree = _nonempty(execution.get("canonical_worktree"), "canonical worktree", 2048)
    if not PurePath(worktree).is_absolute():
        raise ContractError("canonical worktree must be absolute")
    base_sha = execution.get("base_sha")
    if not isinstance(base_sha, str) or not SHA_RE.fullmatch(base_sha.lower()):
        raise ContractError("base SHA must contain 40 hexadecimal characters")
    if execution.get("adapter_switch_policy") != "stop-and-report":
        raise ContractError("adapter switch policy must be stop-and-report")

    lease = _mapping(contract.get("writer_lease"), "writer lease")
    _required_keys(lease, {"holder", "state"}, "writer lease")
    _exact_keys(lease, {"holder", "state"}, "writer lease")
    if lease.get("state") not in LEASE_STATES:
        raise ContractError("writer lease state is invalid")
    holder = lease.get("holder")
    if lease.get("state") == "active" and holder != WRITERS[mode]:
        raise ContractError("active writer does not match the selected mode")
    if lease.get("state") != "active" and holder not in (None, WRITERS[mode]):
        raise ContractError("writer lease holder is invalid")

    if contract.get("acceptance_owner") != ACCEPTANCE_OWNERS[mode]:
        raise ContractError("acceptance owner does not match the selected mode")

    authority = _mapping(contract.get("authority"), "authority")
    if authority != REQUIRED_AUTHORITY:
        raise ContractError("authority boundaries do not match the constitutional kernel")

    state = contract.get("state")
    if state not in ACTIVE_STATES + TERMINAL_STATES:
        raise ContractError("task state is invalid")
    terminal_states = contract.get("terminal_states")
    if terminal_states != list(TERMINAL_STATES):
        raise ContractError("terminal states must match the shared contract")

    skills = contract.get("required_manual_skills", [])
    if not isinstance(skills, list) or len(skills) > 32:
        raise ContractError("required manual skills must be a bounded list")
    seen: set[str] = set()
    for index, item_value in enumerate(skills):
        item = _mapping(item_value, f"required_manual_skills[{index}]")
        _required_keys(item, {"name", "host", "status"}, "manual skill")
        _exact_keys(item, {"name", "host", "status", "invocation"}, "manual skill")
        name = _nonempty(item.get("name"), "manual skill name", 64)
        if name in seen:
            raise ContractError("manual skill names must be unique")
        seen.add(name)
        status = item.get("status")
        if status not in MANUAL_SKILL_STATES:
            raise ContractError("manual skill status is invalid")
        host = item.get("host")
        if host not in MANUAL_SKILL_HOSTS or host not in MODE_MANUAL_SKILL_HOSTS[mode]:
            raise ContractError("manual skill host does not match the selected mode")
        invocation = item.get("invocation")
        if status == "invoked":
            expected = f"${name}" if host == "codex" else f"/{name}"
            if invocation != expected:
                raise ContractError("invoked manual skill must record its native invocation")
        elif invocation is not None:
            raise ContractError("uninvoked manual skill cannot claim a native invocation")
    return contract
