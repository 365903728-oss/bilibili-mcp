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
from contextvars import ContextVar
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
_ACTIVE_LOCK_PARENTS: ContextVar[
    tuple[tuple[str, int | None, int, int, str | None, int | None, int | None], ...]
] = ContextVar(
    "harness_active_lock_parents", default=()
)


def _active_lock_parent(
    path: Path,
) -> tuple[str, int | None, int, int, str | None, int | None, int | None] | None:
    normalized = os.path.normcase(os.path.abspath(path))
    for active in reversed(_ACTIVE_LOCK_PARENTS.get()):
        if normalized == active[0]:
            return active
    return None


def _verify_active_lock_parent(path: Path) -> None:
    active = _active_lock_parent(path)
    if active is None:
        return
    try:
        current = os.stat(path, follow_symlinks=False)
    except OSError as exc:
        raise ValueError("runtime lock directory changed") from exc
    if not stat.S_ISDIR(current.st_mode) or (current.st_dev, current.st_ino) != (
        active[2],
        active[3],
    ):
        raise ValueError("runtime lock directory changed")
    if active[1] is not None and active[4] is not None:
        try:
            visible_lock = os.stat(
                active[4], dir_fd=active[1], follow_symlinks=False
            )
        except OSError as exc:
            raise ValueError("runtime lock file changed") from exc
        if (
            not stat.S_ISREG(visible_lock.st_mode)
            or visible_lock.st_nlink != 1
            or (visible_lock.st_dev, visible_lock.st_ino) != (active[5], active[6])
        ):
            raise ValueError("runtime lock file changed")


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


def _windows_long_path(path: Path) -> Path:
    """Expand an existing Windows 8.3 prefix without resolving reparse points."""
    if os.name != "nt":
        return path

    import ctypes
    from ctypes import wintypes

    existing = path
    missing: list[str] = []
    while not os.path.lexists(existing):
        if existing.parent == existing:
            return path
        missing.append(existing.name)
        existing = existing.parent

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    get_long_path_name = kernel32.GetLongPathNameW
    get_long_path_name.argtypes = [
        wintypes.LPCWSTR,
        wintypes.LPWSTR,
        wintypes.DWORD,
    ]
    get_long_path_name.restype = wintypes.DWORD
    required = get_long_path_name(str(existing), None, 0)
    if required == 0:
        return path
    buffer = ctypes.create_unicode_buffer(required)
    if get_long_path_name(str(existing), buffer, required) == 0:
        return path
    expanded = Path(buffer.value)
    for component in reversed(missing):
        expanded /= component
    return expanded


def ensure_no_link_components(boundary: Path, target: Path) -> None:
    """Reject a target that escapes a boundary or traverses a link/junction."""
    boundary_abs = _windows_long_path(Path(os.path.abspath(boundary)))
    target_abs = _windows_long_path(Path(os.path.abspath(target)))
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
    parent_descriptor: int | None = None
    windows_guard: Iterator[None] | None = None
    windows_guard_entered = False
    try:
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        if os.name == "nt":
            windows_guard = _hold_windows_directory_chain(path.parent)
            windows_guard.__enter__()
            windows_guard_entered = True
            _verify_active_lock_parent(path.parent)
            candidate: Path | str = path
        else:
            parent_descriptor = _open_directory_nofollow(path.parent)
            candidate = path.name
        if parent_descriptor is None:
            descriptor = os.open(candidate, flags)
            visible = os.stat(candidate, follow_symlinks=False)
        else:
            descriptor = os.open(candidate, flags, dir_fd=parent_descriptor)
            visible = os.stat(
                candidate, dir_fd=parent_descriptor, follow_symlinks=False
            )
        opened = os.fstat(descriptor)
        if (
            not stat.S_ISREG(opened.st_mode)
            or not stat.S_ISREG(visible.st_mode)
            or (parent_descriptor is None and _is_link_like(path))
            or (opened.st_dev, opened.st_ino) != (visible.st_dev, visible.st_ino)
        ):
            return []
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = None
            if opened.st_size > max_bytes:
                handle.seek(opened.st_size - max_bytes)
            raw = handle.read(max_bytes)
            closed = os.fstat(handle.fileno())
            if parent_descriptor is None:
                visible_after = os.stat(candidate, follow_symlinks=False)
            else:
                visible_after = os.stat(
                    candidate, dir_fd=parent_descriptor, follow_symlinks=False
                )
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
    except (OSError, ValueError):
        return []
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if parent_descriptor is not None:
            os.close(parent_descriptor)
        if windows_guard_entered and windows_guard is not None:
            windows_guard.__exit__(None, None, None)
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
    parent_descriptor: int | None = None
    windows_guard: Iterator[None] | None = None
    windows_guard_entered = False
    try:
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        if os.name == "nt":
            windows_guard = _hold_windows_directory_chain(path.parent)
            windows_guard.__enter__()
            windows_guard_entered = True
            _verify_active_lock_parent(path.parent)
            candidate: Path | str = path
        else:
            parent_descriptor = _open_directory_nofollow(path.parent)
            candidate = path.name
        if parent_descriptor is None:
            descriptor = os.open(candidate, flags)
            visible = os.stat(candidate, follow_symlinks=False)
        else:
            descriptor = os.open(candidate, flags, dir_fd=parent_descriptor)
            visible = os.stat(
                candidate, dir_fd=parent_descriptor, follow_symlinks=False
            )
        opened = os.fstat(descriptor)
        if (
            not stat.S_ISREG(opened.st_mode)
            or not stat.S_ISREG(visible.st_mode)
            or opened.st_size > max_bytes
            or (parent_descriptor is None and _is_link_like(path))
            or (opened.st_dev, opened.st_ino) != (visible.st_dev, visible.st_ino)
        ):
            return None
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = None
            raw = handle.read(max_bytes + 1)
        if len(raw) > max_bytes:
            return None
        return raw
    except (OSError, ValueError):
        return None
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if parent_descriptor is not None:
            os.close(parent_descriptor)
        if windows_guard_entered and windows_guard is not None:
            windows_guard.__exit__(None, None, None)


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


def _lock_directory_descriptor(descriptor: int) -> None:
    import fcntl

    for _ in range(200):
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return
        except BlockingIOError:
            time.sleep(0.025)
    raise OSError("runtime lock directory is busy")


def _unlock_directory_descriptor(descriptor: int) -> None:
    import fcntl

    fcntl.flock(descriptor, fcntl.LOCK_UN)


def _acquire_lock_at(
    lock_path: Path, parent_descriptor: int | None, *, create: bool
) -> int | None:
    candidate: Path | str = lock_path if parent_descriptor is None else lock_path.name

    def current() -> os.stat_result:
        if parent_descriptor is None:
            return os.stat(candidate, follow_symlinks=False)
        return os.stat(candidate, dir_fd=parent_descriptor, follow_symlinks=False)

    for _ in range(200):
        if parent_descriptor is None and _is_link_like(lock_path):
            return None
        flags = os.O_RDWR | (os.O_CREAT if create else 0)
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            if parent_descriptor is None:
                descriptor = os.open(candidate, flags, 0o600)
            else:
                descriptor = os.open(
                    candidate, flags, 0o600, dir_fd=parent_descriptor
                )
        except OSError:
            return None
        try:
            opened = os.fstat(descriptor)
            visible = current()
            if (
                not stat.S_ISREG(opened.st_mode)
                or opened.st_nlink != 1
                or (opened.st_dev, opened.st_ino)
                != (visible.st_dev, visible.st_ino)
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
            visible = current()
            if (opened.st_dev, opened.st_ino) != (
                visible.st_dev,
                visible.st_ino,
            ):
                os.close(descriptor)
                return None
            return descriptor
        except OSError:
            os.close(descriptor)
            time.sleep(0.025)
    return None


def _acquire_lock(lock_path: Path, *, create: bool = True) -> int | None:

    if os.name == "nt":
        try:
            with _hold_windows_directory_chain(lock_path.parent):
                return _acquire_lock_at(lock_path, None, create=create)
        except (OSError, ValueError):
            return None
    try:
        parent_descriptor = _open_directory_nofollow(lock_path.parent)
    except (OSError, ValueError):
        return None
    try:
        opened_parent = os.fstat(parent_descriptor)
        descriptor = _acquire_lock_at(
            lock_path, parent_descriptor, create=create
        )
        try:
            visible_parent = os.stat(lock_path.parent, follow_symlinks=False)
        except OSError:
            visible_parent = None
        if visible_parent is None or (opened_parent.st_dev, opened_parent.st_ino) != (
            visible_parent.st_dev,
            visible_parent.st_ino,
        ):
            if descriptor is not None:
                os.close(descriptor)
            return None
        return descriptor
    finally:
        os.close(parent_descriptor)


@contextmanager
def bounded_file_lock(lock_path: Path, *, create: bool = True) -> Iterator[None]:
    """Serialize one bounded runtime-state transaction."""
    if create:
        if (
            _active_lock_parent(lock_path.parent) is None
            and not _directory_exists_nofollow(lock_path.parent)
        ):
            try:
                _ensure_directory_nofollow(lock_path.parent)
            except (OSError, ValueError) as exc:
                raise ValueError("runtime lock is unavailable") from exc
    elif not lock_path.is_file():
        raise ValueError("existing lock file is unavailable")
    if _is_link_like(lock_path):
        raise ValueError("runtime lock path cannot be a link")
    if os.name == "nt":
        guard = _hold_windows_directory_chain(lock_path.parent)
        guard_entered = False
        try:
            guard.__enter__()
            guard_entered = True
            parent = os.stat(lock_path.parent, follow_symlinks=False)
            descriptor = _acquire_lock_at(lock_path, None, create=create)
        except (OSError, ValueError) as exc:
            if guard_entered:
                guard.__exit__(None, None, None)
            raise ValueError("runtime lock is unavailable") from exc
        guard.__exit__(None, None, None)
        if descriptor is None:
            raise ValueError("runtime lock is unavailable")
        token = _ACTIVE_LOCK_PARENTS.set(
            (
                *_ACTIVE_LOCK_PARENTS.get(),
                (
                    os.path.normcase(os.path.abspath(lock_path.parent)),
                    None,
                    parent.st_dev,
                    parent.st_ino,
                    None,
                    None,
                    None,
                ),
            )
        )
        try:
            yield
            with _hold_windows_directory_chain(lock_path.parent):
                _verify_active_lock_parent(lock_path.parent)
        finally:
            try:
                _ACTIVE_LOCK_PARENTS.reset(token)
                _unlock_descriptor(descriptor)
            finally:
                os.close(descriptor)
        return

    try:
        parent_descriptor = _open_directory_nofollow(lock_path.parent)
    except (OSError, ValueError) as exc:
        raise ValueError("runtime lock is unavailable") from exc
    parent = os.fstat(parent_descriptor)
    owns_parent_lock = _active_lock_parent(lock_path.parent) is None
    try:
        if owns_parent_lock:
            _lock_directory_descriptor(parent_descriptor)
        descriptor = _acquire_lock_at(lock_path, parent_descriptor, create=create)
    except OSError as exc:
        os.close(parent_descriptor)
        raise ValueError("runtime lock is unavailable") from exc
    if descriptor is None:
        if owns_parent_lock:
            _unlock_directory_descriptor(parent_descriptor)
        os.close(parent_descriptor)
        raise ValueError("runtime lock is unavailable")
    opened_lock = os.fstat(descriptor)
    token = _ACTIVE_LOCK_PARENTS.set(
        (
            *_ACTIVE_LOCK_PARENTS.get(),
            (
                os.path.normcase(os.path.abspath(lock_path.parent)),
                parent_descriptor,
                parent.st_dev,
                parent.st_ino,
                lock_path.name,
                opened_lock.st_dev,
                opened_lock.st_ino,
            ),
        )
    )
    try:
        _verify_active_lock_parent(lock_path.parent)
        yield
        _verify_active_lock_parent(lock_path.parent)
        try:
            current_descriptor = _open_directory_nofollow(
                lock_path.parent, bind_transaction=False
            )
        except (OSError, ValueError) as exc:
            raise ValueError("runtime lock directory changed") from exc
        try:
            current = os.fstat(current_descriptor)
        finally:
            os.close(current_descriptor)
        if (parent.st_dev, parent.st_ino) != (current.st_dev, current.st_ino):
            raise ValueError("runtime lock directory changed")
    finally:
        try:
            _ACTIVE_LOCK_PARENTS.reset(token)
            _unlock_descriptor(descriptor)
        finally:
            try:
                os.close(descriptor)
                if owns_parent_lock:
                    _unlock_directory_descriptor(parent_descriptor)
            finally:
                os.close(parent_descriptor)


def _open_directory_nofollow(
    path: Path, *, bind_transaction: bool = True, create: bool = False
) -> int:
    active = _active_lock_parent(path) if bind_transaction else None
    if active is not None:
        assert active[1] is not None
        _verify_active_lock_parent(path)
        try:
            current_descriptor = _open_directory_nofollow(
                path, bind_transaction=False
            )
        except (OSError, ValueError) as exc:
            raise ValueError("runtime lock directory changed") from exc
        try:
            current = os.fstat(current_descriptor)
        finally:
            os.close(current_descriptor)
        if (current.st_dev, current.st_ino) != (active[2], active[3]):
            raise ValueError("runtime lock directory changed")
        descriptor = os.dup(active[1])
        opened = os.fstat(descriptor)
        if (opened.st_dev, opened.st_ino) != (active[2], active[3]):
            os.close(descriptor)
            raise OSError("runtime lock directory is unavailable")
        return descriptor
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
            try:
                next_descriptor = os.open(component, flags, dir_fd=descriptor)
            except FileNotFoundError:
                if not create:
                    raise
                try:
                    os.mkdir(component, 0o700, dir_fd=descriptor)
                except FileExistsError:
                    pass
                next_descriptor = os.open(component, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = next_descriptor
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


@contextmanager
def _hold_windows_directory_chain(
    path: Path, *, create: bool = False
) -> Iterator[None]:
    if os.name != "nt":
        yield
        return

    import ctypes
    from ctypes import wintypes

    class ByHandleFileInformation(ctypes.Structure):
        _fields_ = [
            ("file_attributes", wintypes.DWORD),
            ("creation_time", wintypes.FILETIME),
            ("last_access_time", wintypes.FILETIME),
            ("last_write_time", wintypes.FILETIME),
            ("volume_serial_number", wintypes.DWORD),
            ("file_size_high", wintypes.DWORD),
            ("file_size_low", wintypes.DWORD),
            ("number_of_links", wintypes.DWORD),
            ("file_index_high", wintypes.DWORD),
            ("file_index_low", wintypes.DWORD),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create_file = kernel32.CreateFileW
    create_file.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    create_file.restype = wintypes.HANDLE
    file_information = kernel32.GetFileInformationByHandle
    file_information.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(ByHandleFileInformation),
    ]
    file_information.restype = wintypes.BOOL
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = [wintypes.HANDLE]
    close_handle.restype = wintypes.BOOL
    create_directory = kernel32.CreateDirectoryW
    create_directory.argtypes = [wintypes.LPCWSTR, wintypes.LPVOID]
    create_directory.restype = wintypes.BOOL

    absolute = Path(os.path.abspath(path))
    current = Path(absolute.anchor)
    candidates = [current]
    for component in absolute.parts[1:]:
        current = current / component
        candidates.append(current)
    handles: list[int] = []
    invalid_handle = ctypes.c_void_p(-1).value

    def open_directory(candidate: Path) -> int:
        for access in (0x00010080, 0x00000080):
            handle = create_file(
                str(candidate),
                access,
                0x00000001 | 0x00000002,
                None,
                3,
                0x02000000 | 0x00200000,
                None,
            )
            if handle != invalid_handle:
                return handle
            error = ctypes.get_last_error()
            if error not in (5, 32) or access == 0x00000080:
                raise ctypes.WinError(error)
        raise OSError("atomic directory is unavailable")

    try:
        for candidate in candidates:
            try:
                handle = open_directory(candidate)
            except OSError as exc:
                if not create or getattr(exc, "winerror", None) not in (2, 3):
                    raise
                if not create_directory(str(candidate), None):
                    error = ctypes.get_last_error()
                    if error != 183:
                        raise ctypes.WinError(error)
                handle = open_directory(candidate)
            info = ByHandleFileInformation()
            if not file_information(handle, ctypes.byref(info)):
                error = ctypes.get_last_error()
                close_handle(handle)
                raise ctypes.WinError(error)
            if not info.file_attributes & 0x00000010 or info.file_attributes & 0x00000400:
                close_handle(handle)
                raise ValueError("atomic path cannot traverse a reparse point")
            handles.append(handle)
        yield
    finally:
        for handle in reversed(handles):
            close_handle(handle)


def _ensure_directory_nofollow(path: Path) -> None:
    if os.name == "nt":
        with _hold_windows_directory_chain(path, create=True):
            return
    descriptor = _open_directory_nofollow(
        path, bind_transaction=False, create=True
    )
    try:
        opened = os.fstat(descriptor)
        current_descriptor = _open_directory_nofollow(
            path, bind_transaction=False
        )
        try:
            current = os.fstat(current_descriptor)
        finally:
            os.close(current_descriptor)
        if (opened.st_dev, opened.st_ino) != (current.st_dev, current.st_ino):
            raise ValueError("runtime directory changed during creation")
    finally:
        os.close(descriptor)


def _directory_exists_nofollow(path: Path) -> bool:
    try:
        return stat.S_ISDIR(os.stat(path, follow_symlinks=False).st_mode)
    except OSError:
        return False


def _unlink_nofollow(path: Path, *, missing_ok: bool = False) -> None:
    if os.name == "nt":
        with _hold_windows_directory_chain(path.parent):
            _verify_active_lock_parent(path.parent)
            path.unlink(missing_ok=missing_ok)
        return
    parent_descriptor = _open_directory_nofollow(path.parent)
    try:
        try:
            os.unlink(path.name, dir_fd=parent_descriptor)
        except FileNotFoundError:
            if not missing_ok:
                raise
    finally:
        os.close(parent_descriptor)


def _rmdir_nofollow(path: Path) -> None:
    if os.name == "nt":
        with _hold_windows_directory_chain(path.parent):
            _verify_active_lock_parent(path.parent)
            os.rmdir(path)
        return
    parent_descriptor = _open_directory_nofollow(path.parent)
    try:
        os.rmdir(path.name, dir_fd=parent_descriptor)
    finally:
        os.close(parent_descriptor)


def _atomic_write_bytes(path: Path, content: bytes, *, mode: int = 0o600) -> None:
    if os.name == "nt":
        with _hold_windows_directory_chain(path.parent):
            _verify_active_lock_parent(path.parent)
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
                current_descriptor = _open_directory_nofollow(
                    path.parent, bind_transaction=False
                )
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
            mode,
            dir_fd=parent_descriptor,
        )
        temporary_created = True
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fchmod(handle.fileno(), mode)
            os.fsync(handle.fileno())
        if not parent_is_current():
            raise ValueError("atomic write parent changed during write")
        os.replace(
            temporary_name,
            path.name,
            src_dir_fd=parent_descriptor,
            dst_dir_fd=parent_descriptor,
        )
        os.fsync(parent_descriptor)
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
    if (
        _active_lock_parent(path.parent) is None
        and not _directory_exists_nofollow(path.parent)
    ):
        try:
            _ensure_directory_nofollow(path.parent)
        except (OSError, ValueError):
            return False
    if _is_link_like(path):
        return False
    encoded = json.dumps(
        row, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    if len(encoded) > MAX_RECORD_BYTES:
        raise ValueError("hook record exceeds byte limit")

    lock_path = path.with_suffix(path.suffix + ".lock")
    try:
        with bounded_file_lock(lock_path):
            rows = read_bounded_jsonl(path, MAX_JSONL_ROWS - 1, MAX_JSONL_BYTES)
            if unique_field is not None and any(
                item.get(unique_field) == row.get(unique_field) for item in rows
            ):
                return None
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
            while len(lines) > MAX_JSONL_ROWS or sum(
                len(line) + 1 for line in lines
            ) > MAX_JSONL_BYTES:
                lines.pop(0)

            _atomic_write_bytes(path, b"".join(line + b"\n" for line in lines))
            return True
    except ValueError:
        return False


def write_bounded_text(path: Path, content: str, max_bytes: int) -> None:
    encoded = content.encode("utf-8")
    if len(encoded) > max_bytes:
        encoded = encoded[:max_bytes].decode("utf-8", errors="ignore").encode("utf-8")
    if (
        _active_lock_parent(path.parent) is None
        and not _directory_exists_nofollow(path.parent)
    ):
        _ensure_directory_nofollow(path.parent)
    if path.exists() and path.is_symlink():
        return
    _atomic_write_bytes(path, encoded)
