import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def run_cli(*args: str) -> str:
    result = subprocess.run([sys.executable, str(ROOT / "todo_cli.py"), *args], text=True, capture_output=True, check=True)
    return result.stdout.strip()


def test_text_output_remains_compatible():
    assert run_cli("alpha", "beta") == "items (2): alpha, beta"


def test_json_output_contains_items_and_count():
    assert json.loads(run_cli("alpha", "beta", "--json")) == {"count": 2, "items": ["alpha", "beta"]}
