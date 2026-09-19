from __future__ import annotations

import subprocess

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QCoreApplication, QTimer

from launcher.checks import (
    check_api_configuration,
    check_harness_configuration,
    check_workspace,
    configuration_checks,
)
from launcher import runner as runner_module
from launcher.runner import OrchestratorRunner, build_orchestrator_command
from launcher.version import APP_VERSION, DISPLAY_NAME


def _git_workspace(path):
    path.mkdir()
    (path / "README.md").write_text("fixture\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "add", "."], cwd=path, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.email=test@example.com",
            "-c",
            "user.name=test",
            "commit",
            "-qm",
            "baseline",
        ],
        cwd=path,
        check=True,
    )
    return path


def test_build_command_wraps_existing_run_cli(tmp_path):
    program, arguments = build_orchestrator_command(
        "improve errors",
        tmp_path,
        state_dir=tmp_path / "state",
    )

    assert program
    assert arguments[0].endswith("orchestrator.py")
    assert arguments[1:3] == ["run", "improve errors"]
    assert "--workspace" in arguments
    assert "--state-dir" in arguments


def test_frozen_build_uses_bundled_cli_helper(monkeypatch, tmp_path):
    monkeypatch.setattr(runner_module, "IS_FROZEN", True)
    monkeypatch.setattr(runner_module, "APPLICATION_ROOT", tmp_path)

    program, arguments = build_orchestrator_command(
        "improve errors",
        tmp_path,
        state_dir=tmp_path / "state",
    )

    assert program == str(tmp_path / "GPT-DeepSeek-CLI.exe")
    assert arguments[:2] == ["run", "improve errors"]


def test_desktop_version_is_v1_2_0():
    assert APP_VERSION == "1.2.0"
    assert DISPLAY_NAME == "GPT-DeepSeek v1.2.0"


def test_first_run_checks_report_missing_configuration():
    results = configuration_checks({}, which=lambda _command: None)

    assert results[0].key == "python" and results[0].ok
    assert not results[1].ok
    assert "GPT_API_KEY" in results[1].message
    assert not results[2].ok
    assert "dsh (PATH)" in results[2].message


def test_first_run_checks_accept_complete_configuration():
    environment = {
        "GPT_API_KEY": "gpt-secret",
        "GPT_API_BASE": "https://gpt.example/v1",
        "GPT_MODEL": "gpt-model",
        "DEEPSEEK_API_KEY": "deepseek-secret",
        "DEEPSEEK_API_BASE": "https://deepseek.example/v1",
        "DEEPSEEK_MODEL": "deepseek-model",
    }

    assert check_api_configuration(environment).ok
    assert check_harness_configuration(environment, which=lambda _command: "C:/bin/dsh.cmd").ok


def test_workspace_check_matches_git_repository_requirement(tmp_path):
    ordinary_directory = tmp_path / "ordinary"
    ordinary_directory.mkdir()
    invalid = check_workspace(ordinary_directory)
    valid = check_workspace(_git_workspace(tmp_path / "repository"))

    assert not invalid.ok
    assert "Git" in invalid.message
    assert valid.ok


def test_runner_invokes_cli_and_reports_completed(tmp_path):
    app = QCoreApplication.instance() or QCoreApplication([])
    workspace = _git_workspace(tmp_path / "workspace")
    runner = OrchestratorRunner(state_dir=tmp_path / "state")
    logs = []
    statuses = []
    results = []
    runner.log_line.connect(logs.append)
    runner.status_changed.connect(statuses.append)
    runner.finished.connect(lambda succeeded: (results.append(succeeded), app.quit()))
    QTimer.singleShot(15_000, app.quit)

    runner.start("inspect this fixture", workspace, fake=True)
    app.exec()

    assert results == [True]
    assert statuses[0] == "Running"
    assert statuses[-1] == "Completed"
    assert any("[Planner]" in line for line in logs)
    assert any("[Executor]" in line for line in logs)
    assert any("[Reviewer] PASS" in line for line in logs)
