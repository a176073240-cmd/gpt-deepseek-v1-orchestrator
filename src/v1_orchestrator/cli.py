"""Tiny command line surface for V1 (``run``, ``resume``, ``status``)."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Sequence

from .adapters import DeepSeekHarnessAdapter, FakeAdapter, GPTCompatibleAdapter, ProviderConfig
from .persistence import StateStore
from .workflow import Orchestrator, WorkflowError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="v1-orchestrator", description="Resumable GPT/DeepSeek V1 workflow")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="plan, execute, validate, and review a goal")
    run.add_argument("goal")
    run.add_argument("--workspace", default=os.getcwd())
    run.add_argument("--state-dir", default=".orchestrator")
    run.add_argument("--max-iterations", type=int, default=int(os.getenv("MAX_REVIEW_ITERATIONS", "3")))
    run.add_argument("--fake", action="store_true", help="use offline deterministic providers")
    run.add_argument("--json", action="store_true")
    resume = sub.add_parser("resume", help="resume a persisted task")
    resume.add_argument("task_id")
    resume.add_argument("--state-dir", default=".orchestrator")
    resume.add_argument("--workspace")
    resume.add_argument("--fake", action="store_true")
    resume.add_argument("--json", action="store_true")
    status = sub.add_parser("status", help="print persisted state")
    status.add_argument("task_id")
    status.add_argument("--state-dir", default=".orchestrator")
    status.add_argument("--json", action="store_true")
    ask = sub.add_parser("ask", help="persist a human escalation question")
    ask.add_argument("task_id")
    ask.add_argument("question")
    ask.add_argument("--state-dir", default=".orchestrator")
    ask.add_argument("--context", default="")
    ask.add_argument("--json", action="store_true")
    answer = sub.add_parser("answer", help="answer a pending escalation")
    answer.add_argument("task_id")
    answer.add_argument("answer")
    answer.add_argument("--question-id")
    answer.add_argument("--state-dir", default=".orchestrator")
    answer.add_argument("--json", action="store_true")
    return parser


def _providers(fake: bool):
    if fake:
        adapter = FakeAdapter()
        return adapter, adapter, adapter
    planner = GPTCompatibleAdapter(ProviderConfig.from_env("GPT"), role="planner")
    reviewer = GPTCompatibleAdapter(ProviderConfig.from_env("GPT"), role="reviewer")
    executor = DeepSeekHarnessAdapter(model=os.getenv("DEEPSEEK_MODEL"))
    return planner, executor, reviewer


def _json_state(state) -> str:
    return json.dumps(state.to_dict(), ensure_ascii=False, indent=2, sort_keys=True)


def run_cli(goal: str, workspace: str, *, state_dir: str = ".orchestrator", max_iterations: int = 3, fake: bool = False):
    planner, executor, reviewer = _providers(fake)
    runner = Orchestrator(StateStore(state_dir), planner, executor, reviewer, max_iterations=max_iterations)
    created = runner.create(goal, workspace)
    return runner.run(created.task_id)


def resume_cli(task_id: str, *, state_dir: str = ".orchestrator", fake: bool = False):
    planner, executor, reviewer = _providers(fake)
    runner = Orchestrator(StateStore(state_dir), planner, executor, reviewer)
    return runner.resume(task_id)


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "run":
            state = run_cli(args.goal, args.workspace, state_dir=args.state_dir, max_iterations=args.max_iterations, fake=args.fake)
        elif args.command == "resume":
            state = resume_cli(args.task_id, state_dir=args.state_dir, fake=args.fake)
        elif args.command == "ask":
            store = StateStore(args.state_dir)
            state = Orchestrator(store, FakeAdapter(), FakeAdapter()).request_input(args.task_id, args.question, context=args.context)
        elif args.command == "answer":
            store = StateStore(args.state_dir)
            state = Orchestrator(store, FakeAdapter(), FakeAdapter()).answer_input(args.task_id, args.answer, question_id=args.question_id)
        else:
            state = StateStore(args.state_dir).load(args.task_id)
        print(_json_state(state) if getattr(args, "json", False) else f"{state.task_id}: {state.phase}")
        return 0 if state.phase == "COMPLETED" else 1
    except (WorkflowError, ValueError, OSError, RuntimeError) as exc:
        print(f"error: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
