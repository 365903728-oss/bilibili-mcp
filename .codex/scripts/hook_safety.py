"""Compatibility import for legacy hook scripts.

Harness v2 keeps the hardened implementation in ``harness.safe_io`` so Codex,
Claude Code, the CLI, and the existing scripts share one safety boundary.
"""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from harness.safe_io import (  # noqa: E402,F401
    MAX_JSONL_BYTES,
    MAX_JSONL_ROWS,
    MAX_STDIN_BYTES,
    append_bounded_jsonl,
    ensure_no_link_components,
    find_key,
    read_bounded_json_object,
    read_bounded_jsonl,
    read_bounded_stdin_object,
    safe_agent,
    safe_category,
    safe_label,
    safe_path_component,
    safe_tool_class,
    write_bounded_text,
)


__all__ = [
    "MAX_JSONL_BYTES",
    "MAX_JSONL_ROWS",
    "MAX_STDIN_BYTES",
    "append_bounded_jsonl",
    "ensure_no_link_components",
    "find_key",
    "read_bounded_json_object",
    "read_bounded_jsonl",
    "read_bounded_stdin_object",
    "safe_agent",
    "safe_category",
    "safe_label",
    "safe_path_component",
    "safe_tool_class",
    "write_bounded_text",
]
