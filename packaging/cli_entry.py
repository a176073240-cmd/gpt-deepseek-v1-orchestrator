"""Console entry point bundled beside the Windows GUI executable."""
from __future__ import annotations

import os
import sys

from v1_orchestrator.cli import main


def _attach_output_streams() -> None:
    """Attach a windowed helper to QProcess pipes without opening a console."""
    if os.name != "nt":
        return
    import ctypes
    import msvcrt

    def stream(handle_number: int):
        try:
            handle = ctypes.windll.kernel32.GetStdHandle(handle_number)
            if handle in (0, -1):
                raise OSError("standard handle is unavailable")
            descriptor = msvcrt.open_osfhandle(handle, os.O_WRONLY)
            return os.fdopen(descriptor, "w", encoding="utf-8", errors="replace", closefd=False)
        except OSError:
            return open(os.devnull, "w", encoding="utf-8")

    if sys.stdout is None:
        sys.stdout = stream(-11)
    if sys.stderr is None:
        sys.stderr = stream(-12)


if __name__ == "__main__":
    _attach_output_streams()
    raise SystemExit(main())
