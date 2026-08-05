"""Deterministic offline checks for bounded, metadata-only hook persistence."""

from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import generate_learning_proposals
import post_tool_use
from hook_safety import (
    MAX_JSONL_BYTES,
    MAX_JSONL_ROWS,
    MAX_STDIN_BYTES,
    append_bounded_jsonl,
    read_bounded_json_object,
    read_bounded_jsonl,
)


@contextlib.contextmanager
def hook_invocation(payload: bytes, argv: list[str]):
    old_stdin = sys.stdin
    old_argv = sys.argv
    stream = io.TextIOWrapper(io.BytesIO(payload), encoding="utf-8")
    output = io.StringIO()
    try:
        sys.stdin = stream
        sys.argv = argv
        with contextlib.redirect_stdout(output):
            yield output
    finally:
        sys.stdin = old_stdin
        sys.argv = old_argv
        stream.close()


def test_post_tool_persists_only_fixed_metadata():
    secret = "SESSDATA_SYNTHETIC_DO_NOT_RETAIN"
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        original_agent_base = post_tool_use.agent_base
        post_tool_use.agent_base = lambda _agent: root
        try:
            payload = json.dumps(
                {
                    "tool_name": f"shell_command_{secret}",
                    "command": f"npm test -- --token={secret}",
                    "exit_code": 1,
                    "stderr": f"failure {secret}",
                    "message": f"error {secret}",
                }
            ).encode("utf-8")
            with hook_invocation(
                payload,
                ["post_tool_use.py", "--agent", "codex"],
            ) as output:
                assert post_tool_use.main() == 0
            assert json.loads(output.getvalue()) == {"suppressOutput": True}
        finally:
            post_tool_use.agent_base = original_agent_base

        persisted = "\n".join(
            path.read_text(encoding="utf-8")
            for path in root.rglob("*")
            if path.is_file()
        )
        assert secret not in persisted
        observations = read_bounded_jsonl(root / "memory" / "observations.jsonl")
        assert observations[-1]["tool"] == "shell"
        assert observations[-1]["category"] == "test"


def test_oversized_hook_input_is_suppressed_without_state():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        original_agent_base = post_tool_use.agent_base
        post_tool_use.agent_base = lambda _agent: root
        try:
            payload = b'{"stderr":"' + b"x" * MAX_STDIN_BYTES + b'"}'
            with hook_invocation(
                payload,
                ["post_tool_use.py", "--agent", "codex"],
            ) as output:
                assert post_tool_use.main() == 0
            assert json.loads(output.getvalue()) == {"suppressOutput": True}
        finally:
            post_tool_use.agent_base = original_agent_base
        assert not list(root.rglob("*.jsonl"))


def test_jsonl_rotation_and_symlink_refusal():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        state = root / "state.jsonl"
        for index in range(MAX_JSONL_ROWS + 25):
            append_bounded_jsonl(
                state,
                {"index": index, "value": "x" * 2048},
            )
        rows = read_bounded_jsonl(state)
        assert len(rows) <= MAX_JSONL_ROWS
        assert state.stat().st_size <= MAX_JSONL_BYTES
        assert rows[-1]["index"] == MAX_JSONL_ROWS + 24

        target = root / "target.jsonl"
        target.write_text("sentinel\n", encoding="utf-8")
        link = root / "link.jsonl"
        try:
            link.symlink_to(target)
        except OSError:
            return
        append_bounded_jsonl(link, {"secret": "must-not-write"})
        assert target.read_text(encoding="utf-8") == "sentinel\n"


def test_bounded_json_object_rejects_oversize_and_deep_state():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        state = root / "state.json"
        state.write_text(json.dumps({"value": "x" * 200}), encoding="utf-8")
        assert read_bounded_json_object(state, 64) == {}

        deep: object = "leaf"
        for _ in range(12):
            deep = {"child": deep}
        state.write_text(json.dumps(deep), encoding="utf-8")
        assert read_bounded_json_object(state, 4096) == {}


def test_learning_proposals_sanitize_historical_metadata():
    secret = "SYNTHETIC_SECRET_IN_METADATA"
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        codex = root / "codex"
        claude = root / "claude"
        codex.mkdir()
        claude.mkdir()
        row = {
            "candidate_id": "0123456789ab",
            "agent": secret,
            "category": secret,
            "tool": secret,
            "evidence_count": 2,
            "confidence": 0.8,
        }
        (codex / "candidates.jsonl").write_text(
            json.dumps(row) + "\n",
            encoding="utf-8",
        )
        original_codex = generate_learning_proposals.codex_memory
        original_claude = generate_learning_proposals.claude_memory
        generate_learning_proposals.codex_memory = lambda: codex
        generate_learning_proposals.claude_memory = lambda: claude
        try:
            proposals = generate_learning_proposals.stable_candidates()
        finally:
            generate_learning_proposals.codex_memory = original_codex
            generate_learning_proposals.claude_memory = original_claude

        rendered = generate_learning_proposals.render(proposals)
        assert secret not in rendered
        assert proposals[0]["agents"] == ["unknown"]
        assert proposals[0]["category"] == "shell"
        assert proposals[0]["tool"] == "other"


def test_session_start_does_not_preview_learning_candidates():
    content = (SCRIPT_DIR / "session-start.ps1").read_text(encoding="utf-8")
    assert "pending-learning-proposals.md" not in content
    assert "candidates.jsonl" not in content
    assert "observations.jsonl" not in content


if __name__ == "__main__":
    tests = [
        (name, value)
        for name, value in globals().items()
        if name.startswith("test_") and callable(value)
    ]
    failures = 0
    for name, test in tests:
        try:
            test()
            print(f"PASS {name}")
        except Exception:
            failures += 1
            print(f"FAIL {name}")
            import traceback

            traceback.print_exc()
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    raise SystemExit(1 if failures else 0)
