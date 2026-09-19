"""Qt widgets for the Windows launcher."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QGridLayout,
    QGroupBox,
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
    from .checks import CheckResult, check_workspace, configuration_checks
    from .runner import OrchestratorRunner
    from .version import APP_VERSION
except ImportError:  # Direct execution through ``python launcher/main.py``.
    from checks import CheckResult, check_workspace, configuration_checks
    from runner import OrchestratorRunner
    from version import APP_VERSION


class LauncherWindow(QMainWindow):
    """Small GUI shell around the existing orchestrator CLI."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"GPT-DeepSeek Assistant — v{APP_VERSION}")
        self.resize(860, 760)

        self._runner = OrchestratorRunner(self)
        self._runner.log_line.connect(self._append_log)
        self._runner.status_changed.connect(self._set_status)
        self._runner.finished.connect(self._run_finished)
        self._configuration_results: tuple[CheckResult, ...] = ()
        self._closing = False

        self.configuration_group = QGroupBox("首次启动检查 / 当前配置状态")
        configuration_layout = QGridLayout()
        self.configuration_summary = QLabel()
        self.configuration_labels: dict[str, QLabel] = {}
        for row, (key, title) in enumerate(
            (("python", "Python 环境"), ("api", "GPT API"), ("harness", "DeepSeek Harness")),
            start=1,
        ):
            configuration_layout.addWidget(QLabel(f"{title}:"), row, 0)
            value = QLabel("检查中…")
            value.setWordWrap(True)
            self.configuration_labels[key] = value
            configuration_layout.addWidget(value, row, 1)
        self.refresh_button = QPushButton("重新检查配置")
        self.refresh_button.clicked.connect(self._refresh_configuration)
        configuration_layout.addWidget(self.configuration_summary, 0, 0, 1, 2)
        configuration_layout.addWidget(self.refresh_button, 4, 1, Qt.AlignmentFlag.AlignRight)
        self.configuration_group.setLayout(configuration_layout)

        self.task_input = QTextEdit()
        self.task_input.setPlaceholderText('Describe the goal, for example: "优化这个项目的错误处理"')
        self.task_input.setMinimumHeight(110)

        self.workspace_input = QLineEdit()
        self.workspace_input.setReadOnly(True)
        self.workspace_input.setPlaceholderText("Select a project directory")
        self.workspace_button = QPushButton("选择项目目录")
        self.workspace_button.clicked.connect(self._choose_workspace)
        self.workspace_status = QLabel("尚未选择项目目录")
        self.workspace_status.setWordWrap(True)

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
        layout.addWidget(self.configuration_group)
        layout.addWidget(QLabel("Task"))
        layout.addWidget(self.task_input)
        layout.addWidget(QLabel("Workspace"))
        layout.addLayout(workspace_row)
        layout.addWidget(self.workspace_status)
        layout.addLayout(action_row)
        layout.addWidget(QLabel("Logs"))
        layout.addWidget(self.log_output, 1)

        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)
        self._refresh_configuration()
        self._update_workspace_status()

    def _choose_workspace(self) -> None:
        start = self.workspace_input.text() or str(Path.cwd())
        selected = QFileDialog.getExistingDirectory(self, "选择项目目录", start)
        if selected:
            self.workspace_input.setText(str(Path(selected).resolve()))
            self._update_workspace_status()

    def _start(self) -> None:
        self._refresh_configuration()
        workspace_result = self._update_workspace_status()
        issues = [result for result in self._configuration_results if not result.ok]
        if not workspace_result.ok:
            issues.append(workspace_result)
        task = self.task_input.toPlainText().strip()
        if not task:
            issues.insert(0, CheckResult("task", "Task", False, "请输入要完成的任务目标"))
        if issues:
            details = []
            for issue in issues:
                line = f"• {issue.label}：{issue.message}"
                if issue.remediation:
                    line += f"\n  {issue.remediation}"
                details.append(line)
            QMessageBox.warning(
                self,
                "暂时无法开始",
                "请先完成以下设置：\n\n" + "\n".join(details),
            )
            return
        try:
            self._runner.start(task, self.workspace_input.text())
        except (ValueError, RuntimeError) as exc:
            QMessageBox.warning(self, "暂时无法开始", f"启动失败：{exc}\n\n请检查配置和日志后重试。")
            return
        self.start_button.setEnabled(False)
        self.workspace_button.setEnabled(False)
        self.refresh_button.setEnabled(False)
        self.task_input.setEnabled(False)

    def _refresh_configuration(self) -> None:
        self._configuration_results = configuration_checks()
        ready = all(result.ok for result in self._configuration_results)
        self.configuration_summary.setText(
            "配置已就绪，可以开始任务。" if ready else "配置尚未完成，请处理下面标红的项目。"
        )
        self.configuration_summary.setStyleSheet(
            "color: #166534; font-weight: 600;" if ready else "color: #991b1b; font-weight: 600;"
        )
        for result in self._configuration_results:
            label = self.configuration_labels[result.key]
            label.setText(("可用 — " if result.ok else "需要设置 — ") + result.message)
            label.setStyleSheet("color: #166534;" if result.ok else "color: #991b1b;")
            label.setToolTip(result.remediation or result.message)

    def _update_workspace_status(self) -> CheckResult:
        result = check_workspace(self.workspace_input.text())
        self.workspace_status.setText(("Workspace 可用 — " if result.ok else "Workspace 需要设置 — ") + result.message)
        self.workspace_status.setStyleSheet("color: #166534;" if result.ok else "color: #991b1b;")
        self.workspace_status.setToolTip(result.remediation or result.message)
        return result

    def _append_log(self, text: str) -> None:
        self.log_output.appendPlainText(text)
        scrollbar = self.log_output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _set_status(self, status: str) -> None:
        self.status_label.setText(status)
        self.status_label.setStyleSheet(self._status_style(status))

    def _run_finished(self, succeeded: bool) -> None:
        self.start_button.setEnabled(True)
        self.workspace_button.setEnabled(True)
        self.refresh_button.setEnabled(True)
        self.task_input.setEnabled(True)
        if not succeeded and not self._closing:
            QMessageBox.warning(
                self,
                "任务执行失败",
                f"{self._runner.last_error}\n\n请查看日志中的详细信息，修正配置后重试。",
            )

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
            self._closing = True
            self._runner.stop()
            event.accept()
        else:
            event.ignore()
