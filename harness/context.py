"""Git worktree discovery without machine-specific paths."""

from __future__ import annotations

import hashlib
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path


class WorktreeError(ValueError):
    """Raised when a path is not inside a usable Git worktree."""


@dataclass(frozen=True)
class WorktreeContext:
    root: Path
    git_dir: Path
    common_git_dir: Path
    head_sha: str
    worktree_id: str
    repository_id: str

    @property
    def runtime_root(self) -> Path:
        return self.root / ".harness" / "runtime" / self.worktree_id


def _git(cwd: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(cwd), *args],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="strict",
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise WorktreeError("unable to inspect Git worktree") from exc
    if result.returncode != 0:
        raise WorktreeError("path is not inside a Git worktree")
    return result.stdout.strip()


def _absolute_git_path(root: Path, raw: str) -> Path:
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = root / candidate
    return candidate.resolve()


def _opaque_id(prefix: str, path: Path) -> str:
    normalized = os.path.normcase(str(path.resolve())).replace("\\", "/")
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


def discover_worktree(cwd: str | Path) -> WorktreeContext:
    start = Path(cwd).resolve()
    root = Path(_git(start, "rev-parse", "--show-toplevel")).resolve()
    git_dir = _absolute_git_path(root, _git(start, "rev-parse", "--git-dir"))
    common_git_dir = _absolute_git_path(root, _git(start, "rev-parse", "--git-common-dir"))
    head = _git(start, "rev-parse", "HEAD")
    if len(head) != 40 or any(char not in "0123456789abcdef" for char in head.lower()):
        raise WorktreeError("Git HEAD is not a full SHA")
    return WorktreeContext(
        root=root,
        git_dir=git_dir,
        common_git_dir=common_git_dir,
        head_sha=head.lower(),
        worktree_id=_opaque_id("wt", root),
        repository_id=_opaque_id("repo", common_git_dir),
    )
