"""Entry point for the GPT-DeepSeek Windows launcher."""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

try:
    from .ui import LauncherWindow
except ImportError:  # Supports ``python launcher/main.py`` from a checkout.
    from ui import LauncherWindow


def main() -> int:
    app = QApplication(sys.argv)
    window = LauncherWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
