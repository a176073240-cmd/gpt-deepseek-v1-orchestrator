from __future__ import annotations

import subprocess

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QCoreApplication, QTimer

from launcher.runner import OrchestratorRunner, build_orchestrator_command


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
