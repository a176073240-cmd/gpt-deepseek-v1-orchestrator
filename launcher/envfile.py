"""Small, dependency-free .env handling for the desktop launcher.

The launcher deliberately owns only the local desktop configuration file.  It
never prints values from this file and the repository's .gitignore excludes
``.env`` and ``.env.*`` (apart from the checked-in example).
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path


CONFIG_KEYS = (
    "GPT_API_KEY",
    "GPT_API_BASE",
    "GPT_MODEL",
    "DEEPSEEK_API_KEY",
    "DEEPSEEK_API_BASE",
    "DEEPSEEK_MODEL",
    "DEEPSEEK_HARNESS_PATH",
)
_KEY_RE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$")


def environment_file_path(*, application_root: Path | None = None) -> Path:
    """Return the per-installation .env path used by the launcher."""
    override = os.getenv("GPTDS_ENV_PATH", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    if application_root is None:
        project_root = Path(__file__).resolve().parent.parent
        application_root = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else project_root
    return Path(application_root) / ".env"


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    if " #" in value:
        value = value.split(" #", 1)[0].rstrip()
    return value


def read_env_file(path: Path | None = None) -> dict[str, str]:
    path = path or environment_file_path()
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}
    values: dict[str, str] = {}
    for line in lines:
        match = _KEY_RE.match(line)
        if match:
            values[match.group(1)] = _unquote(match.group(2))
    return values


def load_environment(path: Path | None = None, *, overwrite: bool = False) -> dict[str, str]:
    """Load supported values into ``os.environ`` and return the loaded map."""
    values = read_env_file(path)
    for key, value in values.items():
        if overwrite or not os.getenv(key, "").strip():
            os.environ[key] = value
    return values


def save_environment(values: dict[str, str], path: Path | None = None) -> Path:
    """Persist supported values atomically, retaining comments/unknown keys."""
    path = path or environment_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    existing: list[str] = []
    try:
        existing = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        pass
    normalized = {key: str(values.get(key, "")).strip() for key in CONFIG_KEYS}
    seen: set[str] = set()
    output: list[str] = []
    for line in existing:
        match = _KEY_RE.match(line)
        if not match or match.group(1) not in normalized:
            output.append(line)
            continue
        key = match.group(1)
        seen.add(key)
        output.append(f"{key}={normalized[key]}")
    if output and output[-1].strip():
        output.append("")
    for key in CONFIG_KEYS:
        if key not in seen:
            output.append(f"{key}={normalized[key]}")
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text("\n".join(output).rstrip() + "\n", encoding="utf-8")
    temporary.replace(path)
    for key, value in normalized.items():
        os.environ[key] = value
    return path


def first_run_marker_path() -> Path:
    base = os.getenv("LOCALAPPDATA", "").strip()
    if base:
        return Path(base) / "GPT-DeepSeek" / "first-run-complete"
    return environment_file_path().parent / ".orchestrator" / "first-run-complete"



