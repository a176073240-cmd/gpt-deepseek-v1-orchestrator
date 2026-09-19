"""Asynchronous adapter between the launcher and the existing CLI."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from PySide6.QtCore import QObject, QProcess, QTimer, Signal


PROJECT_ROOT = Path(__file__).resolve().parent.parent
IS_FROZEN = bool(getattr(sys, "frozen", False))
APPLICATION_ROOT = Path(sys.executable).resolve().parent if IS_FROZEN else PROJECT_ROOT


def default_state_dir() -> Path:
    if not IS_FROZEN:
        return PROJECT_ROOT / ".orchestrator"
    local_app_data = os.getenv("LOCALAPPDATA")
    base = Path(local_app_data) if local_app_data else APPLICATION_ROOT
    return base / "GPT-DeepSeek" / "state"


def build_orchestrator_command(
    goal: str,
    workspace: str | Path,
    *,
    state_dir: str | Path,
    fake: bool = False,
) -> tuple[str, list[str]]:
    """Build the source-checkout equivalent of ``orchestrator run``."""
    cli_arguments = [
        "run",
        goal,
        "--workspace",
        str(Path(workspace).resolve()),
        "--state-dir",
        str(Path(state_dir).resolve()),
    ]
    if fake:
        cli_arguments.append("--fake")
    if IS_FROZEN:
        return str(APPLICATION_ROOT / "GPT-DeepSeek-CLI.exe"), cli_arguments
    return sys.executable, [str(PROJECT_ROOT / "orchestrator.py"), *cli_arguments]


class OrchestratorRunner(QObject):
    """Run the CLI without blocking Qt and surface persisted phase changes."""

    log_line = Signal(str)
    status_changed = Signal(str)
    finished = Signal(bool)

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        state_dir: str | Path | None = None,
    ) -> None:
        super().__init__(parent)
        self._process = QProcess(self)
        self._process.setWorkingDirectory(str(APPLICATION_ROOT))
        self._process.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)
        self._process.readyReadStandardOutput.connect(self._read_stdout)
        self._process.readyReadStandardError.connect(self._read_stderr)
        self._process.errorOccurred.connect(self._process_error)
        self._process.finished.connect(self._process_finished)

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(300)
        self._poll_timer.timeout.connect(self._poll_state)

        self._state_dir = Path(state_dir).resolve() if state_dir else default_state_dir()
        self._known_state_files: set[str] = set()
        self._task_file: Path | None = None
        self._last_signature: tuple[object, ...] | None = None
        self._last_state: dict[str, object] | None = None
        self._planning_complete_logged = False
        self._logged_execution_count = 0
        self._logged_validation_count = 0
        self._logged_review_count = 0
        self._stdout_buffer = ""
        self._stderr_buffer = ""
        self._error_reported = False
        self._last_error = "任务未完成。请查看日志了解详情。"

    @property
    def is_running(self) -> bool:
        return self._process.state() != QProcess.ProcessState.NotRunning

    @property
    def last_error(self) -> str:
        return self._last_error

    def start(self, goal: str, workspace: str | Path, *, fake: bool = False) -> None:
        if self.is_running:
            raise RuntimeError("an orchestrator task is already running")

        goal = goal.strip()
        workspace_text = str(workspace).strip()
        if not goal:
            raise ValueError("Task is required")
        if not workspace_text:
            raise ValueError("Workspace is required")
        workspace_path = Path(workspace_text).expanduser().resolve()
        if not workspace_path.is_dir():
            raise ValueError("Workspace must be an existing directory")

        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._known_state_files = {path.name for path in self._state_dir.glob("*.json")}
        self._task_file = None
        self._last_signature = None
        self._last_state = None
        self._planning_complete_logged = False
        self._logged_execution_count = 0
        self._logged_validation_count = 0
        self._logged_review_count = 0
        self._stdout_buffer = ""
        self._stderr_buffer = ""
        self._error_reported = False
        self._last_error = "任务未完成。请查看日志了解详情。"

        program, arguments = build_orchestrator_command(
            goal,
            workspace_path,
            state_dir=self._state_dir,
            fake=fake,
        )
        self.status_changed.emit("Running")
        self.log_line.emit("[Launcher] Starting orchestrator run")
        self.log_line.emit("[Planner] Waiting for PLANNING state")
        self._poll_timer.start()
        self._process.start(program, arguments)

    def stop(self) -> None:
        """Request termination; persisted CLI state remains resumable."""
        if self.is_running:
            self.log_line.emit("[Launcher] Stopping the CLI process")
            self._process.terminate()

    def _read_stdout(self) -> None:
        chunk = bytes(self._process.readAllStandardOutput()).decode("utf-8", errors="replace")
        self._stdout_buffer += chunk
        self._emit_complete_lines("stdout")

    def _read_stderr(self) -> None:
        chunk = bytes(self._process.readAllStandardError()).decode("utf-8", errors="replace")
        self._stderr_buffer += chunk
        self._emit_complete_lines("stderr")

    def _emit_complete_lines(self, channel: str, *, flush: bool = False) -> None:
        attribute = "_stdout_buffer" if channel == "stdout" else "_stderr_buffer"
        buffer = getattr(self, attribute)
        parts = buffer.splitlines(keepends=True)
        remainder = ""
        if parts and not parts[-1].endswith(("\n", "\r")) and not flush:
            remainder = parts.pop()
        for part in parts:
            line = part.rstrip("\r\n")
            if line:
                prefix = "[CLI]" if channel == "stdout" else "[CLI error]"
                self.log_line.emit(f"{prefix} {line}")
                if channel == "stderr" or line.lower().startswith("error:"):
                    self._last_error = line.removeprefix("error:").strip() or self._last_error
        if flush and remainder:
            prefix = "[CLI]" if channel == "stdout" else "[CLI error]"
            self.log_line.emit(f"{prefix} {remainder}")
            remainder = ""
        setattr(self, attribute, remainder)

    def _poll_state(self) -> None:
        if self._task_file is None:
            candidates = [
                path
                for path in self._state_dir.glob("*.json")
                if path.name not in self._known_state_files
            ]
            if candidates:
                self._task_file = max(candidates, key=lambda path: path.stat().st_mtime_ns)
        if self._task_file is None:
            return

        try:
            payload = json.loads(self._task_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        if not isinstance(payload, dict):
            return

        reports = payload.get("execution_reports") or []
        reviews = payload.get("reviewer_feedback") or []
        signature = (
            payload.get("phase"),
            payload.get("iteration"),
            len(reports),
            len(reviews),
        )
        self._last_state = payload
        if signature == self._last_signature:
            return
        self._last_signature = signature
        self._log_state(payload)

    def _log_state(self, state: dict[str, object]) -> None:
        phase = str(state.get("phase") or "")
        iteration = int(state.get("iteration") or 0)
        reports = state.get("execution_reports") or []
        validations = state.get("test_results") or []
        reviews = state.get("reviewer_feedback") or []

        if state.get("task_contract") and not self._planning_complete_logged:
            self.log_line.emit("[Planner] completed")
            self._planning_complete_logged = True
        if isinstance(reports, list) and len(reports) > self._logged_execution_count:
            for report_number in range(self._logged_execution_count + 1, len(reports) + 1):
                self.log_line.emit(f"[Executor] finished (iteration {report_number})")
            self._logged_execution_count = len(reports)
        if isinstance(validations, list) and len(validations) > self._logged_validation_count:
            self.log_line.emit("[Validation] completed")
            self._logged_validation_count = len(validations)
        if isinstance(reviews, list) and len(reviews) > self._logged_review_count:
            for review in reviews[self._logged_review_count :]:
                review = review if isinstance(review, dict) else {}
                verdict = str(review.get("verdict") or "")
                notes = str(review.get("notes") or "").strip()
                if verdict:
                    suffix = f": {notes}" if notes else ""
                    self.log_line.emit(f"[Reviewer] {verdict}{suffix}")
            self._logged_review_count = len(reviews)

        if phase == "PLANNING":
            self.log_line.emit("[Planner] PLANNING")
        elif phase == "EXECUTING":
            self.log_line.emit(f"[Executor] EXECUTING (iteration {iteration + 1})")
        elif phase == "VALIDATING":
            self.log_line.emit("[Executor] finished; validation is running")
        elif phase == "REVIEWING":
            self.log_line.emit("[Reviewer] REVIEWING")
        elif phase == "COMPLETED":
            self.log_line.emit("[Workflow] COMPLETED")
        elif phase == "BLOCKED":
            reason = str(state.get("block_reason") or "no reason supplied")
            self._last_error = f"工作流已阻止：{reason}"
            self.log_line.emit(f"[Workflow] BLOCKED: {reason}")

    def _process_error(self, error: QProcess.ProcessError) -> None:
        if error == QProcess.ProcessError.Crashed:
            return
        self._error_reported = True
        self._last_error = f"无法启动 CLI：{self._process.errorString()}"
        self.log_line.emit(f"[Launcher] Failed to start CLI: {self._process.errorString()}")
        if error == QProcess.ProcessError.FailedToStart:
            self._poll_timer.stop()
            self.status_changed.emit("Failed")
            self.finished.emit(False)

    def _process_finished(self, exit_code: int, _exit_status: QProcess.ExitStatus) -> None:
        self._poll_state()
        self._poll_timer.stop()
        self._emit_complete_lines("stdout", flush=True)
        self._emit_complete_lines("stderr", flush=True)

        phase = str((self._last_state or {}).get("phase") or "")
        succeeded = exit_code == 0 and phase == "COMPLETED"
        if succeeded:
            self.status_changed.emit("Completed")
        else:
            self.status_changed.emit("Failed")
            if not self._error_reported and not phase:
                self._last_error = f"CLI 异常退出（代码 {exit_code}）。"
                self.log_line.emit(f"[Launcher] CLI exited with code {exit_code}")
        self.finished.emit(succeeded)
