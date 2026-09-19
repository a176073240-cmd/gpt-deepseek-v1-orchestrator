"""First-run wizard for users who have never opened the desktop launcher."""
from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QLabel,
    QLineEdit,
    QWizard,
    QWizardPage,
)

try:
    from .checks import check_api_configuration, check_harness_configuration, check_python_environment
    from .envfile import CONFIG_KEYS, first_run_marker_path, save_environment
    from .runner import APPLICATION_ROOT
except ImportError:  # Direct execution through ``python launcher/main.py``.
    from checks import check_api_configuration, check_harness_configuration, check_python_environment
    from envfile import CONFIG_KEYS, first_run_marker_path, save_environment
    from runner import APPLICATION_ROOT


class FirstRunWizard(QWizard):
    """Four short pages: environment, API, connection check, and ready."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("GPT-DeepSeek 首次启动向导")
        self.setMinimumSize(620, 430)
        self._fields: dict[str, QLineEdit] = {}
        self._connection_label = QLabel()
        self._build_pages()
        self.finished.connect(self._mark_complete)

    @staticmethod
    def is_complete() -> bool:
        try:
            return first_run_marker_path().is_file()
        except OSError:
            return False

    def _build_pages(self) -> None:
        environment = QWizardPage()
        environment.setTitle("1. Environment Check")
        environment.setSubTitle("启动器会检查 Python、API 配置和 DeepSeek Harness。")
        env_label = QLabel()
        env_label.setWordWrap(True)
        python = check_python_environment()
        harness = check_harness_configuration(application_root=APPLICATION_ROOT)
        env_label.setText("\n".join((
            ("✓ " if python.ok else "✗ ") + f"Python: {python.message}",
            ("✓ " if harness.ok else "✗ ") + f"Harness: {harness.message}",
            "提示：向导不会发送真实模型请求。",
        )))
        environment_layout = QFormLayout()
        environment_layout.addRow(env_label)
        environment.setLayout(environment_layout)
        self.addPage(environment)

        api = QWizardPage()
        api.setTitle("2. API Configuration")
        api.setSubTitle("值只保存到本机 .env，不会提交到 Git。")
        form = QFormLayout()
        for key in CONFIG_KEYS:
            field = QLineEdit(os.getenv(key, ""))
            if key.endswith("_KEY"):
                field.setEchoMode(QLineEdit.EchoMode.Password)
            field.setPlaceholderText(key)
            self._fields[key] = field
            form.addRow(QLabel(key), field)
        api.setLayout(form)
        self.addPage(api)

        connection = QWizardPage()
        connection.setTitle("3. Connection Test")
        connection.setSubTitle("检查本地配置完整性，不会消耗 API 配额。")
        self._connection_label.setWordWrap(True)
        connection_layout = QFormLayout()
        connection_layout.addRow(self._connection_label)
        connection.setLayout(connection_layout)
        self.addPage(connection)

        ready = QWizardPage()
        ready.setTitle("4. Ready")
        ready.setSubTitle("可以开始运行 Demo 或执行你的第一个任务。")
        ready_layout = QFormLayout()
        ready_layout.addRow(QLabel("设置已保存。点击 Finish 进入启动器。"))
        ready.setLayout(ready_layout)
        self.addPage(ready)

    def nextId(self) -> int:  # noqa: N802 - Qt API name
        return super().nextId()

    def validateCurrentPage(self) -> bool:  # noqa: N802 - Qt API name
        if self.currentId() == 1:
            save_environment({key: field.text() for key, field in self._fields.items()})
        if self.currentId() == 2:
            api = check_api_configuration()
            harness = check_harness_configuration(application_root=APPLICATION_ROOT)
            self._connection_label.setText(
                ("✓ " if api.ok else "✗ ") + f"API: {api.message}\n" +
                ("✓ " if harness.ok else "✗ ") + f"Harness: {harness.message}"
            )
        return True

    def _mark_complete(self, _result: int) -> None:
        marker = first_run_marker_path()
        try:
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.write_text("completed\n", encoding="utf-8")
        except OSError:
            pass

