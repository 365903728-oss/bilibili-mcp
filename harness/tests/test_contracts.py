from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from harness.contracts import (
    ACCEPTANCE_OWNERS,
    EXECUTION_MODES,
    WRITERS,
    ContractError,
    validate_codex_direct_contract,
    validate_task_contract,
)


def valid_contract() -> dict[str, object]:
    return {
        "schema": "harness.task-contract/v1",
        "task": {"id": "github:#29", "source": "https://github.com/example/repo/issues/29"},
        "execution": {
            "mode": "codex-direct",
            "canonical_worktree": "C:/worktrees/ticket-29/repo",
            "base_sha": "a" * 40,
            "adapter_switch_policy": "stop-and-report",
        },
        "writer_lease": {"holder": "codex", "state": "active"},
        "acceptance_owner": "codex",
        "authority": {
            "local_read_write_test": "allowed",
            "local_commit": "after-acceptance",
            "push_pr_tag_release_publish": "user-approval-required",
            "credentials_ssh_broad_delete_history_rewrite": "blocked",
        },
        "state": "executing",
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


class TaskContractTests(unittest.TestCase):
    def test_contract_declares_exactly_three_modes_and_owners(self) -> None:
        self.assertEqual(
            EXECUTION_MODES,
            ("codex-direct", "codex-paseo-claude", "claude-direct"),
        )
        self.assertEqual(WRITERS["codex-direct"], "codex")
        self.assertEqual(WRITERS["codex-paseo-claude"], "claude")
        self.assertEqual(WRITERS["claude-direct"], "claude")
        self.assertEqual(ACCEPTANCE_OWNERS["codex-paseo-claude"], "codex")
        self.assertEqual(ACCEPTANCE_OWNERS["claude-direct"], "claude")

        schema_path = Path(__file__).resolve().parents[1] / "contracts" / "task-contract-v1.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        self.assertEqual(
            tuple(schema["properties"]["execution"]["properties"]["mode"]["enum"]),
            EXECUTION_MODES,
        )

    def test_valid_contract_round_trips_as_typed_contract(self) -> None:
        normalized = validate_task_contract(valid_contract())
        self.assertEqual(normalized["schema"], "harness.task-contract/v1")
        self.assertEqual(normalized["execution"]["mode"], "codex-direct")
        self.assertEqual(normalized["writer_lease"]["holder"], "codex")

    def test_codex_direct_execution_requires_frozen_plan_and_owned_paths(self) -> None:
        contract = valid_contract()
        contract["execution"]["branch"] = "codex/issue-30"  # type: ignore[index]
        contract["writer_lease"] = {"holder": "codex", "state": "inactive"}
        contract["state"] = "ready"
        contract["plan"] = {
            "objective": "Complete one approved ticket.",
            "owned_paths": ["harness/"],
            "acceptance_criteria": [
                {"id": "criterion", "description": "The ticket is accepted."}
            ],
            "verification_plan": [
                {"id": "tests", "command": "python -m unittest", "required": True}
            ],
            "repair_policy": {"max_attempts": 2},
            "stop_conditions": ["adapter-failure"],
        }
        normalized = validate_codex_direct_contract(contract)
        self.assertEqual(normalized["plan"]["owned_paths"], ["harness/"])

        contract["plan"]["owned_paths"] = ["../README.md"]  # type: ignore[index]
        with self.assertRaisesRegex(ContractError, "repository-relative"):
            validate_codex_direct_contract(contract)

    def test_typed_identifiers_reject_noncanonical_whitespace(self) -> None:
        contract = valid_contract()
        contract["task"]["id"] = " pilot-30 "  # type: ignore[index]
        with self.assertRaisesRegex(ContractError, "unsafe characters"):
            validate_task_contract(contract)

    def test_contract_rejects_wrong_writer_or_acceptance_owner(self) -> None:
        wrong_writer = valid_contract()
        wrong_writer["writer_lease"]["holder"] = "claude"  # type: ignore[index]
        with self.assertRaisesRegex(ContractError, "writer"):
            validate_task_contract(wrong_writer)

        wrong_owner = valid_contract()
        wrong_owner["acceptance_owner"] = "claude"
        with self.assertRaisesRegex(ContractError, "acceptance"):
            validate_task_contract(wrong_owner)

    def test_contract_rejects_silent_switch_or_unbounded_authority(self) -> None:
        switched = valid_contract()
        switched["execution"]["adapter_switch_policy"] = "automatic"  # type: ignore[index]
        with self.assertRaisesRegex(ContractError, "switch"):
            validate_task_contract(switched)

        unsafe = valid_contract()
        unsafe["authority"]["push_pr_tag_release_publish"] = "allowed"  # type: ignore[index]
        with self.assertRaisesRegex(ContractError, "authority"):
            validate_task_contract(unsafe)

    def test_contract_rejects_fields_outside_the_versioned_schema(self) -> None:
        extra = valid_contract()
        extra["implicit_fallback"] = "claude-direct"
        with self.assertRaisesRegex(ContractError, "unexpected"):
            validate_task_contract(extra)

        nested = valid_contract()
        nested["writer_lease"]["second_holder"] = "claude"  # type: ignore[index]
        with self.assertRaisesRegex(ContractError, "unexpected"):
            validate_task_contract(nested)

        missing = valid_contract()
        missing.pop("required_manual_skills")
        with self.assertRaisesRegex(ContractError, "missing"):
            validate_task_contract(missing)

    def test_manual_skill_records_native_invocation(self) -> None:
        missing = copy.deepcopy(valid_contract())
        missing["required_manual_skills"][0]["status"] = "required"  # type: ignore[index]
        missing["required_manual_skills"][0].pop("invocation")  # type: ignore[index]
        normalized = validate_task_contract(missing)
        self.assertEqual(normalized["required_manual_skills"][0]["status"], "required")

        imitated = copy.deepcopy(valid_contract())
        imitated["required_manual_skills"][0]["invocation"] = "implicit-router"  # type: ignore[index]
        with self.assertRaisesRegex(ContractError, "native"):
            validate_task_contract(imitated)

        wrong_host = copy.deepcopy(valid_contract())
        wrong_host["required_manual_skills"][0]["host"] = "claude"  # type: ignore[index]
        with self.assertRaisesRegex(ContractError, "host"):
            validate_task_contract(wrong_host)

        invalid_name = copy.deepcopy(valid_contract())
        invalid_name["required_manual_skills"][0]["name"] = "bad#skill"  # type: ignore[index]
        invalid_name["required_manual_skills"][0]["invocation"] = "$bad#skill"  # type: ignore[index]
        with self.assertRaisesRegex(ContractError, "native"):
            validate_task_contract(invalid_name)

        collaboration = copy.deepcopy(valid_contract())
        collaboration["execution"]["mode"] = "codex-paseo-claude"  # type: ignore[index]
        collaboration["writer_lease"]["holder"] = "claude"  # type: ignore[index]
        collaboration["required_manual_skills"][0] = {  # type: ignore[index]
            "name": "implement",
            "host": "claude",
            "status": "invoked",
            "invocation": "/implement",
        }
        self.assertEqual(
            validate_task_contract(collaboration)["required_manual_skills"][0]["host"],
            "claude",
        )
        collaboration["required_manual_skills"][0]["invocation"] = "$implement"  # type: ignore[index]
        with self.assertRaisesRegex(ContractError, "native"):
            validate_task_contract(collaboration)


if __name__ == "__main__":
    unittest.main()
