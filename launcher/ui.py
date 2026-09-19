"""Qt widgets for the Windows launcher."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

try:
    from .runner import OrchestratorRunner
except ImportError:  # Direct execution through ``python launcher/main.py``.
    from runner import OrchestratorRunner


class LauncherWindow(QMainWindow):
    """Small GUI shell around the existing orchestrator CLI."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("GPT-DeepSeek Assistant")
        self.resize(820, 620)

        self._runner = OrchestratorRunner(self)
        self._runner.log_line.connect(self._append_log)
        self._runner.status_changed.connect(self._set_status)
        self._runner.finished.connect(self._run_finished)

        self.task_input = QTextEdit()
        self.task_input.setPlaceholderText('Describe the goal, for example: "优化这个项目的错误处理"')
        self.task_input.setMinimumHeight(110)

        self.workspace_input = QLineEdit()
        self.workspace_input.setReadOnly(True)
        self.workspace_input.setPlaceholderText("Select a project directory")
        self.workspace_button = QPushButton("选择项目目录")
        self.workspace_button.clicked.connect(self._choose_workspace)

        self.start_button = QPushButton("开始执行")
        self.start_button.setMinimumHeight(38)
        self.start_button.clicked.connect(self._start)

        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setMinimumWidth(110)
        self.status_label.setStyleSheet(self._status_style("Ready"))

        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setPlaceholderText("Planner, Executor, Reviewer, and verdict updates appear here.")

        workspace_row = QHBoxLayout()
        workspace_row.addWidget(self.workspace_input, 1)
        workspace_row.addWidget(self.workspace_button)

        action_row = QHBoxLayout()
        action_row.addWidget(self.start_button, 1)
        action_row.addWidget(QLabel("Status:"))
        action_row.addWidget(self.status_label)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Task"))
        layout.addWidget(self.task_input)
        layout.addWidget(QLabel("Workspace"))
        layout.addLayout(workspace_row)
        layout.addLayout(action_row)
        layout.addWidget(QLabel("Logs"))
        layout.addWidget(self.log_output, 1)

        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)

    def _choose_workspace(self) -> None:
        start = self.workspace_input.text() or str(Path.cwd())
        selected = QFileDialog.getExistingDirectory(self, "选择项目目录", start)
        if selected:
            self.workspace_input.setText(str(Path(selected).resolve()))

    def _start(self) -> None:
        try:
            self._runner.start(self.task_input.toPlainText(), self.workspace_input.text())
        except (ValueError, RuntimeError) as exc:
            QMessageBox.warning(self, "Cannot start", str(exc))
            return
        self.start_button.setEnabled(False)
        self.workspace_button.setEnabled(False)
        self.task_input.setEnabled(False)

    def _append_log(self, text: str) -> None:
        self.log_output.appendPlainText(text)
        scrollbar = self.log_output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _set_status(self, status: str) -> None:
        self.status_label.setText(status)
        self.status_label.setStyleSheet(self._status_style(status))

    def _run_finished(self, _succeeded: bool) -> None:
        self.start_button.setEnabled(True)
        self.workspace_button.setEnabled(True)
        self.task_input.setEnabled(True)

    @staticmethod
    def _status_style(status: str) -> str:
        colors = {
            "Running": ("#fff7d6", "#7a5b00"),
            "Completed": ("#dcfce7", "#166534"),
            "Failed": ("#fee2e2", "#991b1b"),
        }
        background, foreground = colors.get(status, ("#e5e7eb", "#374151"))
        return (
            f"background: {background}; color: {foreground}; "
            "border-radius: 5px; padding: 6px 10px; font-weight: 600;"
        )

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 - Qt API name
        if not self._runner.is_running:
            event.accept()
            return
        choice = QMessageBox.question(
            self,
            "Task is running",
            "Stop the CLI process and close the launcher? The saved task can be resumed later.",
        )
        if choice == QMessageBox.StandardButton.Yes:
            self._runner.stop()
            event.accept()
        else:
            event.ignore()
