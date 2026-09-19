"""A deterministic, provider-free smoke task for the desktop launcher."""
from __future__ import annotations

import runpy
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DemoResult:
    ok: bool
    message: str
    workspace: Path


def run_demo_task(base_dir: str | Path) -> DemoResult:
    """Create a harmless fixture, execute its assertion, and return PASS/FAIL."""
    workspace = Path(base_dir).expanduser().resolve() / "demo-task"
    workspace.mkdir(parents=True, exist_ok=True)
    fixture = workspace / "demo_fixture.txt"
    test_file = workspace / "demo_test.py"
    fixture.write_text("GPT-DeepSeek demo\n", encoding="utf-8")
    test_file.write_text(
        "from pathlib import Path\n"
        "fixture = Path(__file__).with_name('demo_fixture.txt')\n"
        "assert fixture.read_text(encoding='utf-8').strip() == 'GPT-DeepSeek demo'\n",
        encoding="utf-8",
    )
    try:
        runpy.run_path(str(test_file), run_name="__main__")
    except (AssertionError, OSError, SyntaxError) as exc:
        return DemoResult(False, f"Demo FAILED: {exc or 'assertion failed'}", workspace)
    return DemoResult(True, "Demo PASS: test file created and test completed successfully.", workspace)
