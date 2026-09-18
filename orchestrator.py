"""Thin launch shim so ``python orchestrator.py`` works from a checkout."""
from src.v1_orchestrator.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
