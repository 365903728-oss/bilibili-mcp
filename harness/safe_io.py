"""Bounded, metadata-only persistence shared by all Harness adapters."""

from __future__ import annotations

import json
import os
import re
import secrets
import stat
import sys
import tempfile
import time
from collections import deque
from contextlib import contextmanager
from pathlib import Path
from typing import Any, BinaryIO, Iterator


MAX_STDIN_BYTES = 256 * 1024
MAX_JSON_DEPTH = 8
MAX_JSON_NODES = 2_000
MAX_JSONL_BYTES = 1 * 1024 * 1024
MAX_JSONL_ROWS = 512
MAX_RECORD_BYTES = 16 * 1024
SAFE_LABEL_RE = re.compile(r"[^A-Za-z0-9_.:-]+")
SAFE_PATH_COMPONENT_RE = re.compile(r"[^A-Za-z0-9_.-]+")
SAFE_CATEGORIES = {"build", "test", "lint", "package", "git", "shell"}
SAFE_AGENTS = {"codex", "claude"}


def _validate_shape(
    value: Any,
    depth: int = 0,
    budget: list[int] | None = None,
    max_depth: int = MAX_JSON_DEPTH,
) -> None:
    if budget is None:
        budget = [MAX_JSON_NODES]
    budget[0] -= 1
    if budget[0] < 0 or depth > max_depth:
        raise ValueError("hook JSON exceeds structural limits")
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str) or len(key) > 256:
                raise ValueError("hook JSON contains an invalid key")
            _validate_shape(item, depth + 1, budget, max_depth)
    elif isinstance(value, list):
        for item in value:
            _validate_shape(item, depth + 1, budget, max_depth)
    elif isinstance(value, str) and len(value.encode("utf-8")) > MAX_STDIN_BYTES:
        raise ValueError("hook JSON contains an oversized string")


def validate_json_shape(
    value: Any,
    *,
    max_nodes: int = MAX_JSON_NODES,
    max_depth: int = MAX_JSON_DEPTH,
) -> None:
    if max_nodes <= 0 or max_depth < 0:
        raise ValueError("JSON structural limits must be positive")
    _validate_shape(value, budget=[max_nodes], max_depth=max_depth)


def read_bounded_json_stream(stream: BinaryIO) -> dict[str, Any]:
    raw = stream.read(MAX_STDIN_BYTES + 1)
    if len(raw) > MAX_STDIN_BYTES:
        raise ValueError("hook input exceeds byte limit")
    if not raw.strip():
        return {}
    try:
        payload = json.loads(raw.decode("utf-8", errors="strict"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("hook input is not valid UTF-8 JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("hook input must be a JSON object")
    _validate_shape(payload)
    return payload


def read_bounded_stdin_object() -> dict[str, Any]:
    return read_bounded_json_stream(sys.stdin.buffer)


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


def safe_path_component(value: Any, fallback: str = "unknown", max_chars: int = 64) -> str:
    text = value if isinstance(value, str) else fallback
    cleaned = SAFE_PATH_COMPONENT_RE.sub("_", text)[:max_chars].strip(".")
    cleaned = re.sub(r"\.{2,}", "_", cleaned)
    return cleaned or fallback


def _is_link_like(path: Path) -> bool:
    if path.is_symlink():
        return True
    is_junction = getattr(path, "is_junction", None)
    return bool(is_junction and is_junction())


def ensure_no_link_components(boundary: Path, target: Path) -> None:
    """Reject a target that escapes a boundary or traverses a link/junction."""
    boundary_abs = Path(os.path.abspath(boundary))
    target_abs = Path(os.path.abspath(target))
    try:
        relative = target_abs.relative_to(boundary_abs)
    except ValueError as exc:
        raise ValueError("runtime path escapes its worktree boundary") from exc
    current = boundary_abs
    if _is_link_like(current):
        raise ValueError("runtime boundary cannot be a link")
    for part in relative.parts:
        current = current / part
        if _is_link_like(current):
            raise ValueError("runtime path cannot traverse a link")


def safe_agent(value: Any) -> str:
    return value if isinstance(value, str) and value in SAFE_AGENTS else "unknown"


def safe_category(value: Any) -> str:
    return value if isinstance(value, str) and value in SAFE_CATEGORIES else "shell"


def safe_tool_class(value: Any) -> str:
    if not isinstance(value, str):
        return "other"
    normalized = value[:256].lower()
    for marker, tool_class in (
        ("bash", "shell"),
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
    if max_rows <= 0 or max_bytes <= 0:
        return []
    descriptor: int | None = None
    try:
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
        opened = os.fstat(descriptor)
        visible = os.stat(path, follow_symlinks=False)
        if (
            not stat.S_ISREG(opened.st_mode)
            or _is_link_like(path)
            or (opened.st_dev, opened.st_ino) != (visible.st_dev, visible.st_ino)
        ):
            return []
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = None
            if opened.st_size > max_bytes:
                handle.seek(opened.st_size - max_bytes)
            raw = handle.read(max_bytes)
            closed = os.fstat(handle.fileno())
            visible_after = os.stat(path, follow_symlinks=False)
        if (
            len(raw) != min(opened.st_size, max_bytes)
            or (closed.st_dev, closed.st_ino, closed.st_size)
            != (opened.st_dev, opened.st_ino, opened.st_size)
            or (visible_after.st_dev, visible_after.st_ino, visible_after.st_size)
            != (opened.st_dev, opened.st_ino, opened.st_size)
            or _is_link_like(path)
        ):
            return []
        if opened.st_size > max_bytes:
            _, separator, raw = raw.partition(b"\n")
            if not separator:
                return []
        raw_lines = deque(raw.splitlines(), maxlen=max_rows)
    except OSError:
        return []
    finally:
        if descriptor is not None:
            os.close(descriptor)
    rows: list[dict[str, Any]] = []
    for raw_line in raw_lines:
        if len(raw_line) > MAX_RECORD_BYTES:
            continue
        try:
            parsed = json.loads(raw_line.decode("utf-8", errors="strict"))
            _validate_shape(parsed)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
            continue
        if isinstance(parsed, dict):
            rows.append(parsed)
    return rows


def read_bounded_bytes(path: Path, max_bytes: int) -> bytes | None:
    if max_bytes <= 0:
        return None
    descriptor: int | None = None
    try:
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
        opened = os.fstat(descriptor)
        visible = os.stat(path, follow_symlinks=False)
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_size > max_bytes
            or _is_link_like(path)
            or (opened.st_dev, opened.st_ino) != (visible.st_dev, visible.st_ino)
        ):
            return None
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = None
            raw = handle.read(max_bytes + 1)
        if len(raw) > max_bytes:
            return None
        return raw
    except OSError:
        return None
    finally:
        if descriptor is not None:
            os.close(descriptor)


def read_bounded_json_object(
    path: Path,
    max_bytes: int,
    *,
    max_nodes: int = MAX_JSON_NODES,
    max_depth: int = MAX_JSON_DEPTH,
) -> dict[str, Any]:
    raw = read_bounded_bytes(path, max_bytes)
    if raw is None:
        return {}
    try:
        parsed = json.loads(raw.decode("utf-8", errors="strict"))
        validate_json_shape(parsed, max_nodes=max_nodes, max_depth=max_depth)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _lock_descriptor(descriptor: int) -> None:
    os.lseek(descriptor, 0, os.SEEK_SET)
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
    else:
        import fcntl

        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)


def _unlock_descriptor(descriptor: int) -> None:
    os.lseek(descriptor, 0, os.SEEK_SET)
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(descriptor, fcntl.LOCK_UN)


def _acquire_lock(lock_path: Path, *, create: bool = True) -> int | None:
    for _ in range(200):
        if _is_link_like(lock_path):
            return None
        flags = os.O_RDWR | (os.O_CREAT if create else 0)
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            descriptor = os.open(lock_path, flags, 0o600)
        except OSError:
            return None
        try:
            opened = os.fstat(descriptor)
            current = os.stat(lock_path, follow_symlinks=False)
            if (
                not stat.S_ISREG(opened.st_mode)
                or opened.st_nlink != 1
                or _is_link_like(lock_path)
                or (opened.st_dev, opened.st_ino) != (current.st_dev, current.st_ino)
            ):
                os.close(descriptor)
                return None
            if opened.st_size == 0:
                if not create:
                    os.close(descriptor)
                    return None
                os.write(descriptor, b"0")
                os.fsync(descriptor)
            _lock_descriptor(descriptor)
            return descriptor
        except OSError:
            os.close(descriptor)
            time.sleep(0.025)
    return None


@contextmanager
def bounded_file_lock(lock_path: Path, *, create: bool = True) -> Iterator[None]:
    """Serialize one bounded runtime-state transaction."""
    if create:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
    elif not lock_path.is_file():
        raise ValueError("existing lock file is unavailable")
    if _is_link_like(lock_path):
        raise ValueError("runtime lock path cannot be a link")
    descriptor = _acquire_lock(lock_path, create=create)
    if descriptor is None:
        raise ValueError("runtime lock is unavailable")
    try:
        yield
    finally:
        try:
            _unlock_descriptor(descriptor)
        finally:
            os.close(descriptor)


def _open_directory_nofollow(path: Path) -> int:
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    anchor = path.anchor or "."
    parts = path.parts[1:] if path.anchor else path.parts
    descriptor = os.open(anchor, flags)
    try:
        for component in parts:
            if component in ("", "."):
                continue
            if component == "..":
                raise ValueError("atomic write parent cannot traverse upward")
            next_descriptor = os.open(component, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = next_descriptor
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _atomic_write_bytes(path: Path, content: bytes) -> None:
    if os.name == "nt":
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
        )
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, path)
        finally:
            if os.path.exists(temporary_name):
                os.unlink(temporary_name)
        return

    temporary_name = f".{path.name}.{secrets.token_hex(8)}.tmp"
    parent_descriptor = _open_directory_nofollow(path.parent)
    temporary_created = False
    try:
        opened_parent = os.fstat(parent_descriptor)

        def parent_is_current() -> bool:
            try:
                current_descriptor = _open_directory_nofollow(path.parent)
            except (OSError, ValueError):
                return False
            try:
                current_parent = os.fstat(current_descriptor)
                return (opened_parent.st_dev, opened_parent.st_ino) == (
                    current_parent.st_dev,
                    current_parent.st_ino,
                )
            finally:
                os.close(current_descriptor)

        if not stat.S_ISDIR(opened_parent.st_mode) or not parent_is_current():
            raise ValueError("atomic write parent is unavailable")
        temporary_flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
        if hasattr(os, "O_CLOEXEC"):
            temporary_flags |= os.O_CLOEXEC
        descriptor = os.open(
            temporary_name,
            temporary_flags,
            0o600,
            dir_fd=parent_descriptor,
        )
        temporary_created = True
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        if not parent_is_current():
            raise ValueError("atomic write parent changed during write")
        os.replace(
            temporary_name,
            path.name,
            src_dir_fd=parent_descriptor,
            dst_dir_fd=parent_descriptor,
        )
        temporary_created = False
    finally:
        try:
            if temporary_created:
                try:
                    os.unlink(temporary_name, dir_fd=parent_descriptor)
                except FileNotFoundError:
                    pass
        finally:
            os.close(parent_descriptor)


def append_bounded_jsonl(
    path: Path,
    row: dict[str, Any],
    *,
    unique_field: str | None = None,
) -> bool | None:
    """Append under one lock; return None when the unique value already exists."""
    _validate_shape(row)
    path.parent.mkdir(parents=True, exist_ok=True)
    if _is_link_like(path):
        return False
    encoded = json.dumps(
        row, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    if len(encoded) > MAX_RECORD_BYTES:
        raise ValueError("hook record exceeds byte limit")

    lock_path = path.with_suffix(path.suffix + ".lock")
    lock_fd = _acquire_lock(lock_path)
    if lock_fd is None:
        return False
    try:
        rows = read_bounded_jsonl(path, MAX_JSONL_ROWS - 1, MAX_JSONL_BYTES)
        if unique_field is not None and any(
            item.get(unique_field) == row.get(unique_field) for item in rows
        ):
            return None
        lines = [
            json.dumps(item, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
            for item in rows
        ]
        lines.append(encoded)
        while len(lines) > MAX_JSONL_ROWS or sum(len(line) + 1 for line in lines) > MAX_JSONL_BYTES:
            lines.pop(0)

        _atomic_write_bytes(path, b"".join(line + b"\n" for line in lines))
        return True
    finally:
        try:
            _unlock_descriptor(lock_fd)
        finally:
            os.close(lock_fd)


def write_bounded_text(path: Path, content: str, max_bytes: int) -> None:
    encoded = content.encode("utf-8")
    if len(encoded) > max_bytes:
        encoded = encoded[:max_bytes].decode("utf-8", errors="ignore").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.is_symlink():
        return
    _atomic_write_bytes(path, encoded)
