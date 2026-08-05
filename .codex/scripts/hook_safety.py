"""Shared fail-closed bounds for project-local hook state."""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import time
from collections import deque
from pathlib import Path
from typing import Any


MAX_STDIN_BYTES = 256 * 1024
MAX_JSON_DEPTH = 8
MAX_JSON_NODES = 2_000
MAX_JSONL_BYTES = 1 * 1024 * 1024
MAX_JSONL_ROWS = 512
SAFE_LABEL_RE = re.compile(r"[^A-Za-z0-9_.:-]+")
SAFE_CATEGORIES = {"build", "test", "lint", "package", "git", "shell"}
SAFE_AGENTS = {"codex", "claude"}


def _validate_shape(value: Any, depth: int = 0, budget: list[int] | None = None) -> None:
    if budget is None:
        budget = [MAX_JSON_NODES]
    budget[0] -= 1
    if budget[0] < 0 or depth > MAX_JSON_DEPTH:
        raise ValueError("hook JSON exceeds structural limits")
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str) or len(key) > 256:
                raise ValueError("hook JSON contains an invalid key")
            _validate_shape(item, depth + 1, budget)
    elif isinstance(value, list):
        for item in value:
            _validate_shape(item, depth + 1, budget)
    elif isinstance(value, str) and len(value) > MAX_STDIN_BYTES:
        raise ValueError("hook JSON contains an oversized string")


def read_bounded_stdin_object() -> dict[str, Any]:
    raw = sys.stdin.buffer.read(MAX_STDIN_BYTES + 1)
    if len(raw) > MAX_STDIN_BYTES:
        raise ValueError("hook input exceeds byte limit")
    if not raw.strip():
        return {}
    payload = json.loads(raw.decode("utf-8", errors="strict"))
    if not isinstance(payload, dict):
        raise ValueError("hook input must be a JSON object")
    _validate_shape(payload)
    return payload


def find_key(data: Any, names: set[str], depth: int = 0) -> Any:
    if depth > MAX_JSON_DEPTH:
        return None
    if isinstance(data, dict):
        for key, value in data.items():
            if key in names:
                return value
        for value in data.values():
            found = find_key(value, names, depth + 1)
            if found is not None:
                return found
    elif isinstance(data, list):
        for item in data:
            found = find_key(item, names, depth + 1)
            if found is not None:
                return found
    return None


def safe_label(value: Any, fallback: str = "unknown", max_chars: int = 64) -> str:
    text = value if isinstance(value, str) else fallback
    cleaned = SAFE_LABEL_RE.sub("_", text)[:max_chars]
    return cleaned or fallback


def safe_agent(value: Any) -> str:
    return value if isinstance(value, str) and value in SAFE_AGENTS else "unknown"


def safe_category(value: Any) -> str:
    return (
        value
        if isinstance(value, str) and value in SAFE_CATEGORIES
        else "shell"
    )


def safe_tool_class(value: Any) -> str:
    if not isinstance(value, str):
        return "other"
    normalized = value[:256].lower()
    for marker, tool_class in (
        ("shell", "shell"),
        ("command", "shell"),
        ("exec", "shell"),
        ("patch", "edit"),
        ("edit", "edit"),
        ("write", "edit"),
        ("read", "read"),
        ("search", "search"),
        ("mcp", "mcp"),
        ("browser", "browser"),
        ("agent", "agent"),
    ):
        if marker in normalized:
            return tool_class
    return "other"


def read_bounded_jsonl(
    path: Path,
    max_rows: int = MAX_JSONL_ROWS,
    max_bytes: int = MAX_JSONL_BYTES,
) -> list[dict[str, Any]]:
    if not path.exists() or path.is_symlink() or not path.is_file():
        return []
    size = path.stat().st_size
    with path.open("rb") as handle:
        if size > max_bytes:
            handle.seek(size - max_bytes)
            handle.readline()
        raw_lines = deque(handle, maxlen=max_rows)
    rows: list[dict[str, Any]] = []
    for raw_line in raw_lines:
        if len(raw_line) > 16 * 1024:
            continue
        try:
            parsed = json.loads(raw_line.decode("utf-8", errors="strict"))
            _validate_shape(parsed)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
            continue
        if isinstance(parsed, dict):
            rows.append(parsed)
    return rows


def read_bounded_json_object(path: Path, max_bytes: int) -> dict[str, Any]:
    if (
        max_bytes <= 0
        or not path.exists()
        or path.is_symlink()
        or not path.is_file()
        or path.stat().st_size > max_bytes
    ):
        return {}
    try:
        raw = path.read_bytes()
        if len(raw) > max_bytes:
            return {}
        parsed = json.loads(raw.decode("utf-8", errors="strict"))
        _validate_shape(parsed)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _acquire_lock(lock_path: Path) -> int | None:
    for _ in range(20):
        try:
            return os.open(
                lock_path,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                0o600,
            )
        except FileExistsError:
            time.sleep(0.05)
    return None


def append_bounded_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.is_symlink():
        return
    encoded = json.dumps(
        row,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    if len(encoded) > 16 * 1024:
        raise ValueError("hook record exceeds byte limit")

    lock_path = path.with_suffix(path.suffix + ".lock")
    lock_fd = _acquire_lock(lock_path)
    if lock_fd is None:
        return
    try:
        os.close(lock_fd)
        rows = read_bounded_jsonl(path, MAX_JSONL_ROWS - 1, MAX_JSONL_BYTES)
        lines = [
            json.dumps(
                item,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            for item in rows
        ]
        lines.append(encoded)
        while (
            len(lines) > MAX_JSONL_ROWS
            or sum(len(line) + 1 for line in lines) > MAX_JSONL_BYTES
        ):
            lines.pop(0)

        fd, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
        )
        try:
            with os.fdopen(fd, "wb") as handle:
                for line in lines:
                    handle.write(line + b"\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, path)
        finally:
            if os.path.exists(temporary_name):
                os.unlink(temporary_name)
    finally:
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


def write_bounded_text(path: Path, content: str, max_bytes: int) -> None:
    encoded = content.encode("utf-8")
    if len(encoded) > max_bytes:
        encoded = encoded[:max_bytes]
        encoded = encoded.decode("utf-8", errors="ignore").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.is_symlink():
        return
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)
