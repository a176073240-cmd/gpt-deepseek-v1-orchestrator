#!/usr/bin/env python3
"""Read-only connectivity checks for the configured V1 providers.

The script reads environment variables (and a local .env file when present),
performs one minimal request per provider, and checks the DeepSeek Harness
version command. It never writes project files and never prints credentials.
"""
from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_dotenv(path: Path) -> None:
    """Load simple KEY=VALUE entries without overriding process variables."""
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        if key and key not in os.environ:
            os.environ[key] = value


def required(*names: str) -> list[str]:
    return [name for name in names if not os.getenv(name)]


def endpoint(base: str) -> str:
    base = base.rstrip("/")
    return base if base.endswith("/chat/completions") else base + "/chat/completions"


def provider_timeout(prefix: str) -> float:
    """Return a provider-specific timeout without exposing any credentials."""
    defaults = {"GPT": "300", "DEEPSEEK": "60"}
    raw = os.getenv(f"{prefix}_API_TIMEOUT", defaults.get(prefix, "60"))
    try:
        return max(1.0, float(raw))
    except ValueError:
        return float(defaults.get(prefix, "60"))


def check_provider(prefix: str) -> tuple[bool, str]:
    missing = required(f"{prefix}_API_KEY", f"{prefix}_API_BASE", f"{prefix}_MODEL")
    if missing:
        return False, "Missing configuration: " + ", ".join(missing)
    url = endpoint(os.environ[f"{prefix}_API_BASE"])
    payload = {
        "model": os.environ[f"{prefix}_MODEL"],
        "messages": [{"role": "user", "content": "Reply with the single word OK."}],
        "temperature": 0,
        "max_tokens": 8,
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + os.environ[f"{prefix}_API_KEY"],
        },
        method="POST",
    )
    try:
        timeout = provider_timeout(prefix)
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
        choices = body.get("choices") if isinstance(body, dict) else None
        if not isinstance(choices, list) or not choices:
            return False, "Response did not contain a choices array"
        return True, f"HTTP {response.status}; completion payload received"
    except urllib.error.HTTPError as exc:
        return False, f"HTTP {exc.code}: provider rejected the request (check endpoint, model, or API key)"
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", None)
        if isinstance(reason, TimeoutError) or str(reason).lower() in ("timed out", "timeout"):
            return False, f"Request timed out after {timeout:.0f} seconds; increase {prefix}_API_TIMEOUT if needed"
        return False, f"Connection failed: {reason}"
    except TimeoutError:
        return False, f"Request timed out after {timeout:.0f} seconds; increase {prefix}_API_TIMEOUT if needed"
    except OSError as exc:
        return False, f"Connection failed: {exc}"
    except (json.JSONDecodeError, UnicodeDecodeError):
        return False, "Provider returned a non-JSON response"


def check_dsh() -> tuple[bool, str]:
    raw = os.getenv("DSH_COMMAND", "dsh")
    try:
        command = shlex.split(raw, posix=False)
    except ValueError as exc:
        return False, f"Invalid DSH_COMMAND: {exc}"
    if not command:
        return False, "DSH_COMMAND is empty"
    resolved = shutil.which(command[0])
    if resolved:
        command[0] = resolved
    try:
        result = subprocess.run(command + ["--version"], cwd=ROOT, capture_output=True, text=True, timeout=20, check=False)
    except FileNotFoundError:
        return False, f"Executable not found: {command[0]}"
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"Could not start dsh: {exc}"
    output = (result.stdout or result.stderr or "").strip().splitlines()
    version = output[-1] if output else "no version output"
    return (result.returncode == 0, version if result.returncode == 0 else f"exit code {result.returncode}: {version}")


def report(label: str, ok: bool, detail: str) -> None:
    print(f"{label}:")
    print("PASS" if ok else "FAILED")
    print(f"Reason: {detail}")
    print()


def main() -> int:
    load_dotenv(ROOT / ".env")
    results = [check_provider("GPT"), check_provider("DEEPSEEK"), check_dsh()]
    report("GPT API", *results[0])
    report("DeepSeek API", *results[1])
    report("DeepSeek Harness (dsh)", *results[2])
    return 0 if all(ok for ok, _ in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
