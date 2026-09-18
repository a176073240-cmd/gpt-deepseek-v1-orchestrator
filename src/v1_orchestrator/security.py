"""Workspace and secret handling helpers used by all adapters."""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Iterable, Mapping, Sequence


SECRET_PATTERNS = (
    re.compile(r"(?i)(\b(?:api[_-]?key|authorization|token|password|secret)\b\s*[:=]\s*)([^\s,;]+)"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"\b(?:ds|deepseek)[_-][A-Za-z0-9_-]{12,}\b", re.IGNORECASE),
)


def redact(text: object, secrets: Iterable[str] = ()) -> str:
    value = "" if text is None else str(text)
    for secret in secrets:
        secret = str(secret)
        if secret:
            value = value.replace(secret, "[REDACTED]")
    for pattern in SECRET_PATTERNS:
        if pattern.groups:
            value = pattern.sub(lambda match: match.group(1) + "[REDACTED]", value)
        else:
            value = pattern.sub("[REDACTED]", value)
    return value


def secret_values_from_env(env: Mapping[str, str] | None = None) -> list[str]:
    values = env if env is not None else os.environ
    result: list[str] = []
    for key, value in values.items():
        if any(token in key.upper() for token in ("KEY", "TOKEN", "SECRET", "PASSWORD")) and value:
            result.append(value)
    return result


def safe_workspace(workspace: str | os.PathLike[str], allowed_root: str | os.PathLike[str] | None = None) -> Path:
    root = Path(workspace).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"workspace is not a directory: {workspace}")
    if allowed_root is not None:
        boundary = Path(allowed_root).expanduser().resolve()
        try:
            root.relative_to(boundary)
        except ValueError as exc:
            raise PermissionError("workspace is outside allowed root") from exc
    if not (root / ".git").exists():
        raise ValueError("executor workspace must be a Git repository")
    return root


def safe_path(path: str | os.PathLike[str], workspace: str | os.PathLike[str]) -> Path:
    root = safe_workspace(workspace)
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = root / candidate
    candidate = candidate.resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise PermissionError(f"path escapes workspace: {path}") from exc
    return candidate


def git_snapshot(workspace: str | os.PathLike[str]) -> dict:
    root = safe_workspace(workspace)
    def run(args: Sequence[str]) -> str:
        result = subprocess.run(["git", "-C", str(root), *args], text=True, capture_output=True, check=False)
        return redact(result.stdout.strip())
    return {
        "commit": run(("rev-parse", "HEAD")),
        "branch": run(("branch", "--show-current")),
        "status": run(("status", "--short")),
        "diff": run(("diff", "--no-ext-diff", "--binary")),
    }


def git_diff(workspace: str | os.PathLike[str], baseline: str | None = None) -> str:
    root = safe_workspace(workspace)
    args = ("diff", "--no-ext-diff", "--binary") if not baseline else ("diff", "--no-ext-diff", "--binary", baseline, "--")
    result = subprocess.run(["git", "-C", str(root), *args], text=True, capture_output=True, check=False)
    return redact(result.stdout)

