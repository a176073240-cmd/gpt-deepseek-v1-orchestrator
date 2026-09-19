"""Resolve the DeepSeek Harness executable for a desktop installation."""
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping


@dataclass(frozen=True)
class HarnessResolution:
    path: Path | None
    source: str
    message: str

    @property
    def available(self) -> bool:
        return self.path is not None


def _valid(path: Path | str | None) -> Path | None:
    if not path:
        return None
    candidate = Path(path).expanduser()
    try:
        candidate = candidate.resolve()
    except OSError:
        return None
    return candidate if candidate.is_file() else None


def bundled_candidates(application_root: Path | None = None) -> tuple[Path, ...]:
    root = application_root or Path(__file__).resolve().parent.parent
    names = ("dsh.exe", "dsh.cmd", "dsh", "harness.exe", "harness.cmd")
    return tuple(root / name for name in names) + tuple(root / "harness" / name for name in names) + tuple(root / "bin" / name for name in names)


def resolve_harness(
    environment: Mapping[str, str] | None = None,
    *,
    application_root: Path | None = None,
    which: Callable[[str], str | None] = shutil.which,
) -> HarnessResolution:
    env = os.environ if environment is None else environment
    for candidate in bundled_candidates(application_root):
        path = _valid(candidate)
        if path:
            return HarnessResolution(path, "bundled", f"Bundled harness: {path}")

    for key in ("DEEPSEEK_HARNESS_PATH", "DSH_PATH", "GPTDS_HARNESS_PATH"):
        path = _valid(str(env.get(key, "")).strip())
        if path:
            return HarnessResolution(path, "configured", f"Configured harness: {path}")

    path_value = which("dsh")
    if path_value:
        # shutil.which already guarantees existence; custom resolvers may return a command path.
        path = Path(path_value).expanduser()
        return HarnessResolution(path, "PATH", f"PATH harness: {path}")

    return HarnessResolution(
        None,
        "missing",
        "未找到 DeepSeek Harness。请安装 dsh，或在设置中填写 dsh.exe/dsh.cmd 的完整路径。",
    )


