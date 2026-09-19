from __future__ import annotations

import argparse
import json
import sys


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="todo-cli")
    parser.add_argument("items", nargs="*")
    parser.add_argument("--json", action="store_true", help="emit a JSON response")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = {"items": args.items, "count": len(args.items)}
    if args.json:
        print(json.dumps(payload, sort_keys=True))
    else:
        print(f"items ({payload['count']}): " + (", ".join(args.items) if args.items else "none"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
