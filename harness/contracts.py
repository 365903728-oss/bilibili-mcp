"""Typed task-contract invariants for the three execution adapters."""

from __future__ import annotations

import copy
import re
from pathlib import PurePath, PurePosixPath
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
ID_RE = re.compile(r"^[A-Za-z0-9_.:#-]+$")

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
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value) > limit
        or any(
            ord(char) < 32
            or ord(char) == 127
            or 0xD800 <= ord(char) <= 0xDFFF
            for char in value
        )
    ):
        raise ContractError(f"{name} must be a bounded non-empty string")
    return value.strip()


def _identifier(value: Any, name: str, limit: int = 96) -> str:
    identifier = _nonempty(value, name, limit)
    if value != identifier or not ID_RE.fullmatch(identifier):
        raise ContractError(f"{name} contains unsafe characters")
    return identifier


def _bounded_list(value: Any, name: str, limit: int = 64) -> list[Any]:
    if not isinstance(value, list) or not value or len(value) > limit:
        raise ContractError(f"{name} must be a bounded non-empty list")
    return value


def _validate_plan(value: Any) -> dict[str, Any]:
    plan = _mapping(value, "plan")
    fields = {
        "objective",
        "owned_paths",
        "acceptance_criteria",
        "verification_plan",
        "repair_policy",
        "stop_conditions",
    }
    _required_keys(plan, fields, "plan")
    _exact_keys(plan, fields, "plan")
    _nonempty(plan.get("objective"), "plan objective", 2048)

    owned_paths = _bounded_list(plan.get("owned_paths"), "owned paths", 32)
    normalized_owned_paths: list[str] = []
    for raw_path in owned_paths:
        path = _nonempty(raw_path, "owned path", 128).replace("\\", "/")
        directory = path.endswith("/")
        parsed = PurePosixPath(path.rstrip("/"))
        if (
            path.startswith("/")
            or not parsed.parts
            or parsed.is_absolute()
            or any(part in {"", ".", ".."} for part in parsed.parts)
        ):
            raise ContractError("owned paths must be repository-relative")
        if parsed.parts and parsed.parts[0].lower() == ".git":
            raise ContractError("owned paths cannot include Git metadata")
        normalized_owned_paths.append(parsed.as_posix() + ("/" if directory else ""))
    if len(normalized_owned_paths) != len(set(normalized_owned_paths)):
        raise ContractError("owned paths must be unique")
    plan["owned_paths"] = normalized_owned_paths

    criteria = _bounded_list(
        plan.get("acceptance_criteria"), "acceptance criteria", 32
    )
    criterion_ids: set[str] = set()
    for raw_item in criteria:
        item = _mapping(raw_item, "acceptance criterion")
        _required_keys(item, {"id", "description"}, "acceptance criterion")
        _exact_keys(item, {"id", "description"}, "acceptance criterion")
        criterion_id = _identifier(item.get("id"), "criterion id", 96)
        if criterion_id in criterion_ids:
            raise ContractError("acceptance criterion IDs must be unique")
        criterion_ids.add(criterion_id)
        _nonempty(item.get("description"), "criterion description", 256)

    verification = _bounded_list(
        plan.get("verification_plan"), "verification plan", 32
    )
    check_ids: set[str] = set()
    for raw_item in verification:
        item = _mapping(raw_item, "verification check")
        _required_keys(item, {"id", "command", "required"}, "verification check")
        _exact_keys(item, {"id", "command", "required"}, "verification check")
        check_id = _identifier(item.get("id"), "verification check id", 96)
        if check_id in check_ids:
            raise ContractError("verification check IDs must be unique")
        check_ids.add(check_id)
        _nonempty(item.get("command"), "verification command", 512)
        if not isinstance(item.get("required"), bool):
            raise ContractError("verification required flag must be boolean")

    repair = _mapping(plan.get("repair_policy"), "repair policy")
    _required_keys(repair, {"max_attempts"}, "repair policy")
    _exact_keys(repair, {"max_attempts"}, "repair policy")
    attempts = repair.get("max_attempts")
    if not isinstance(attempts, int) or isinstance(attempts, bool) or not 1 <= attempts <= 10:
        raise ContractError("repair attempts must be between 1 and 10")

    stop_conditions = _bounded_list(
        plan.get("stop_conditions"), "stop conditions", 16
    )
    normalized_conditions = [
        _nonempty(item, "stop condition", 96) for item in stop_conditions
    ]
    if len(normalized_conditions) != len(set(normalized_conditions)):
        raise ContractError("stop conditions must be unique")
    return plan


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
            "plan",
        },
        "contract",
    )
    if contract.get("schema") != "harness.task-contract/v1":
        raise ContractError("unsupported task contract schema")

    task = _mapping(contract.get("task"), "task")
    _required_keys(task, {"id", "source"}, "task")
    _exact_keys(task, {"id", "source"}, "task")
    _identifier(task.get("id"), "task.id", 128)
    _nonempty(task.get("source"), "task.source", 1024)

    execution = _mapping(contract.get("execution"), "execution")
    _required_keys(
        execution,
        {"mode", "canonical_worktree", "base_sha", "adapter_switch_policy"},
        "execution",
    )
    _exact_keys(
        execution,
        {"mode", "canonical_worktree", "base_sha", "branch", "adapter_switch_policy"},
        "execution",
    )
    mode = execution.get("mode")
    if mode not in EXECUTION_MODES:
        raise ContractError("execution mode is invalid")
    worktree = _nonempty(execution.get("canonical_worktree"), "canonical worktree", 1024)
    if not PurePath(worktree).is_absolute():
        raise ContractError("canonical worktree must be absolute")
    base_sha = execution.get("base_sha")
    if not isinstance(base_sha, str) or not SHA_RE.fullmatch(base_sha.lower()):
        raise ContractError("base SHA must contain 40 hexadecimal characters")
    execution["base_sha"] = base_sha.lower()
    if execution.get("adapter_switch_policy") != "stop-and-report":
        raise ContractError("adapter switch policy must be stop-and-report")
    if "branch" in execution:
        execution["branch"] = _nonempty(
            execution.get("branch"), "execution branch", 256
        )

    if "plan" in contract:
        _validate_plan(contract["plan"])

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
        name = _identifier(item.get("name"), "manual skill name", 64)
        if "#" in name:
            raise ContractError("manual skill name must be a native invocation identifier")
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


def validate_codex_direct_contract(value: Any) -> dict[str, Any]:
    contract = validate_task_contract(value)
    if contract["execution"]["mode"] != "codex-direct":
        raise ContractError("Codex Direct control requires codex-direct mode")
    if "branch" not in contract["execution"]:
        raise ContractError("Codex Direct control requires a frozen branch")
    if "plan" not in contract:
        raise ContractError("Codex Direct control requires a complete plan")
    if contract["state"] != "ready":
        raise ContractError("Codex Direct control must start from ready")
    if contract["writer_lease"] != {"holder": "codex", "state": "inactive"}:
        raise ContractError("Codex Direct control requires an inactive Codex lease")
    return contract
