"""First-run and workspace checks for the GUI launcher."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping

from PySide6 import __version__ as PYSIDE_VERSION


@dataclass(frozen=True)
class CheckResult:
    """A user-facing readiness check without exposing secret values."""

    key: str
    label: str
    ok: bool
    message: str
    remediation: str = ""


def _configured(environment: Mapping[str, str], *names: str) -> bool:
    return any(str(environment.get(name, "")).strip() for name in names)


def check_python_environment() -> CheckResult:
    version = sys.version_info
    ok = version >= (3, 10)
    message = f"Python {version.major}.{version.minor}.{version.micro} / PySide6 {PYSIDE_VERSION}"
    remediation = "请安装 Python 3.10 或更高版本。" if not ok else ""
    return CheckResult("python", "Python 环境", ok, message, remediation)


def check_api_configuration(environment: Mapping[str, str] | None = None) -> CheckResult:
    environment = os.environ if environment is None else environment
    requirements = (
        ("GPT_API_KEY", ("GPT_API_KEY", "GPT_KEY")),
        ("GPT_API_BASE", ("GPT_API_BASE", "GPT_BASE")),
        ("GPT_MODEL", ("GPT_MODEL",)),
    )
    missing = [display for display, aliases in requirements if not _configured(environment, *aliases)]
    if missing:
        return CheckResult(
            "api",
            "GPT API",
            False,
            "不可用：缺少 " + ", ".join(missing),
            "请设置 GPT_API_KEY、GPT_API_BASE 和 GPT_MODEL，然后重启启动器。",
        )
    return CheckResult(
        "api",
        "GPT API",
        True,
        "配置已就绪（实际连接将在执行任务时验证）",
    )


def check_harness_configuration(
    environment: Mapping[str, str] | None = None,
    *,
    which: Callable[[str], str | None] = shutil.which,
) -> CheckResult:
    environment = os.environ if environment is None else environment
    requirements = (
        ("DEEPSEEK_API_KEY", ("DEEPSEEK_API_KEY",)),
        ("DEEPSEEK_API_BASE", ("DEEPSEEK_API_BASE", "DEEPSEEK_BASE_URL")),
        ("DEEPSEEK_MODEL", ("DEEPSEEK_MODEL",)),
    )
    missing = [display for display, aliases in requirements if not _configured(environment, *aliases)]
    executable = which("dsh")
    if not executable:
        missing.append("dsh (PATH)")
    if missing:
        return CheckResult(
            "harness",
            "DeepSeek Harness",
            False,
            "不可用：缺少 " + ", ".join(missing),
            "请配置 DeepSeek 环境变量，并确保 dsh 命令已加入 PATH。",
        )
    return CheckResult(
        "harness",
        "DeepSeek Harness",
        True,
        f"配置已就绪：{executable}",
    )


def configuration_checks(
    environment: Mapping[str, str] | None = None,
    *,
    which: Callable[[str], str | None] = shutil.which,
) -> tuple[CheckResult, ...]:
    return (
        check_python_environment(),
        check_api_configuration(environment),
        check_harness_configuration(environment, which=which),
    )


def check_workspace(
    workspace: str | Path,
    *,
    which: Callable[[str], str | None] = shutil.which,
) -> CheckResult:
    value = str(workspace).strip()
    if not value:
        return CheckResult("workspace", "Workspace", False, "尚未选择项目目录")
    path = Path(value).expanduser().resolve()
    if not path.is_dir():
        return CheckResult(
            "workspace",
            "Workspace",
            False,
            "无效：目录不存在",
            "请选择一个已有的项目目录。",
        )
    if not (path / ".git").exists():
        return CheckResult(
            "workspace",
            "Workspace",
            False,
            "无效：不是 Git 仓库",
            "请选择包含 .git 的项目目录。",
        )
    git = which("git")
    if not git:
        return CheckResult(
            "workspace",
            "Workspace",
            False,
            "无效：未找到 Git",
            "请安装 Git for Windows 并重启启动器。",
        )
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    try:
        result = subprocess.run(
            [git, "-C", str(path), "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
            creationflags=creationflags,
        )
    except (OSError, subprocess.TimeoutExpired):
        result = None
    if result is None or result.returncode != 0 or result.stdout.strip() != "true":
        return CheckResult(
            "workspace",
            "Workspace",
            False,
            "无效：Git 无法读取该仓库",
            "请检查目录权限和 Git 仓库状态。",
        )
    return CheckResult("workspace", "Workspace", True, f"有效 Git 仓库：{path}")
