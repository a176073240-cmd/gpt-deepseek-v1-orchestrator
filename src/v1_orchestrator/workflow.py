"""Resumable PLANNING -> EXECUTING -> VALIDATING -> REVIEWING workflow."""
from __future__ import annotations

import json
import os
import subprocess
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from .models import ExecutionReport, OrchestrationState, ReviewResult, TaskContract, utc_now
from .persistence import StateStore
from .security import git_diff, git_snapshot, safe_workspace, redact


class WorkflowError(RuntimeError):
    pass


class Orchestrator:
    """Coordinate planner, executor, and reviewer while checkpointing each phase."""

    def __init__(self, store: StateStore, planner: Any, executor: Any, reviewer: Any | None = None, *, max_iterations: int = 3):
        if max_iterations < 1:
            raise ValueError("max_iterations must be positive")
        self.store, self.planner, self.executor = store, planner, executor
        self.reviewer = reviewer or planner
        self.max_iterations = max_iterations

    def create(self, original_goal: str, workspace: str, *, task_id: Optional[str] = None, max_iterations: Optional[int] = None) -> OrchestrationState:
        root = safe_workspace(workspace)
        state = OrchestrationState(task_id=task_id or OrchestrationState().task_id, original_goal=str(original_goal).strip(), workspace=str(root), max_iterations=max_iterations or self.max_iterations, baseline_git=git_snapshot(root))
        if not state.original_goal:
            raise WorkflowError("original goal is required")
        self.store.save(state)
        return state

    def load(self, task_id: str) -> OrchestrationState:
        return self.store.load(task_id)

    def run(self, task_id: str, *, stop_after_phase: Optional[str] = None) -> OrchestrationState:
        state = self.load(task_id)
        while state.phase not in {"COMPLETED", "BLOCKED"}:
            if state.phase == "PLANNING":
                self._planning(state)
            elif state.phase == "EXECUTING":
                self._executing(state)
            elif state.phase == "VALIDATING":
                self._validating(state)
            elif state.phase == "REVIEWING":
                self._reviewing(state)
            else:
                raise WorkflowError(f"cannot resume phase {state.phase}")
            # Persist before honoring a test/CLI checkpoint so interruption never
            # loses the completed phase.
            self.store.save(state)
            if stop_after_phase and state.phase == stop_after_phase.upper():
                break
        return state

    def resume(self, task_id: str) -> OrchestrationState:
        return self.run(task_id)

    def request_input(self, task_id: str, question: str, *, context: str = "") -> OrchestrationState:
        """Persist a human escalation without losing the current execution packet.

        The question is durable and idempotent: asking again while one is
        pending returns the existing record.  Call :meth:`answer_input` after
        the user responds, then :meth:`resume` to continue.
        """
        question = str(question or "").strip()
        if not question:
            raise WorkflowError("question is required")
        state = self.load(task_id)
        pending = state.metadata.get("pending_question")
        if isinstance(pending, dict) and pending.get("status") == "pending":
            return state
        pending = {
            "question_id": f"q-{uuid.uuid4().hex[:12]}",
            "question": question,
            "context": str(context or ""),
            "status": "pending",
            "created_at": utc_now(),
        }
        state.metadata["pending_question"] = pending
        state.metadata["resume_phase"] = state.phase if state.phase not in {"BLOCKED", "COMPLETED"} else ("EXECUTING" if state.task_contract else "PLANNING")
        state.block_reason = "waiting for human input"
        if state.phase != "BLOCKED":
            state.transition("BLOCKED")
        state.touch("input_requested_at")
        self.store.save(state)
        return state

    def answer_input(self, task_id: str, answer: str, *, question_id: Optional[str] = None) -> OrchestrationState:
        """Record an answer and make the task resumable; no model call is made."""
        answer = str(answer or "").strip()
        if not answer:
            raise WorkflowError("answer is required")
        state = self.load(task_id)
        pending = state.metadata.get("pending_question")
        if not isinstance(pending, dict) or pending.get("status") != "pending":
            raise WorkflowError("no pending human question")
        if question_id and question_id != pending.get("question_id"):
            raise WorkflowError("question id does not match pending question")
        pending.update({"status": "answered", "answer": answer, "answered_at": utc_now()})
        state.metadata["human_answer"] = answer
        state.block_reason = None
        resume_phase = state.metadata.pop("resume_phase", None) or ("EXECUTING" if state.task_contract else "PLANNING")
        state.transition(resume_phase)
        state.touch("input_answered_at")
        self.store.save(state)
        return state

    def _planning(self, state: OrchestrationState) -> None:
        if state.task_contract is None:
            context = self._repository_context(state.workspace)
            contract = self.planner.plan(state.original_goal, context)
            if not isinstance(contract, TaskContract):
                from .models import contract_from_response
                contract = contract_from_response(contract)
            errors = contract.validate()
            if errors:
                self._block(state, "invalid planner contract: " + "; ".join(errors))
                return
            state.task_contract = contract
            state.acceptance_criteria = list(contract.acceptance_criteria)
            state.completed_steps.append("planning")
        state.transition("EXECUTING")

    def _executing(self, state: OrchestrationState) -> None:
        if state.task_contract is None:
            self._block(state, "cannot execute without task contract")
            return
        packet = json.dumps({"original_goal": state.original_goal, "task_contract": state.task_contract.to_dict(), "iteration": state.iteration + 1, "previous_repair_requirements": state.metadata.get("repair_requirements", [])}, ensure_ascii=False)
        # Built-in adapters accept ``resume``; retain compatibility with simple
        # third-party/fake adapters that only implement the original two kwargs.
        try:
            report = self.executor.run(packet, state.workspace, session_id=state.deepseek_session_id, resume=bool(state.deepseek_session_id))
        except TypeError as exc:
            if "resume" not in str(exc):
                raise
            report = self.executor.run(packet, state.workspace, session_id=state.deepseek_session_id)
        if not isinstance(report, ExecutionReport):
            report = ExecutionReport.from_dict(report)
        if report.session_id:
            state.deepseek_session_id = report.session_id
        state.execution_reports.append(report.to_dict())
        state.metadata["last_executor_report"] = report.to_dict()
        state.touch("executed_at")
        state.transition("VALIDATING")

    def _validating(self, state: OrchestrationState) -> None:
        report = state.execution_reports[-1] if state.execution_reports else {}
        validation = self._validate_workspace(state.workspace)
        state.test_results.append(validation)
        if not report.get("ok", False):
            state.metadata.setdefault("validation_issues", []).append("executor reported failure")
        state.metadata["git_diff"] = git_diff(state.workspace, state.baseline_git.get("commit"))
        state.git_state = git_snapshot(state.workspace)
        state.completed_steps.append(f"validation-{state.iteration + 1}")
        state.transition("REVIEWING")

    def _reviewing(self, state: OrchestrationState) -> None:
        evidence = {"execution_report": state.execution_reports[-1] if state.execution_reports else {}, "test_results": state.test_results[-1] if state.test_results else {}, "git_diff": state.metadata.get("git_diff", ""), "git_state": state.git_state}
        previous = [str(item.get("notes", "")) for item in state.reviewer_feedback]
        result = self.reviewer.review(state.original_goal, state.task_contract, evidence, previous)
        if not isinstance(result, ReviewResult):
            result = ReviewResult.from_dict(result)
        state.reviewer_feedback.append(result.to_dict())
        state.iteration += 1
        if result.verdict == "PASS":
            state.transition("COMPLETED")
            state.completed_steps.append("review-pass")
        elif result.verdict == "REVISE":
            if state.iteration >= state.max_iterations:
                self._block(state, f"maximum iterations ({state.max_iterations}) reached")
            else:
                # Preserve feedback in the next executor packet; no re-planning needed.
                state.metadata["repair_requirements"] = list(result.repair_requirements)
                state.transition("EXECUTING")
        else:
            self._block(state, result.block_reason or result.notes or "review blocked")

    def _block(self, state: OrchestrationState, reason: str) -> None:
        state.block_reason = redact(reason)
        state.transition("BLOCKED")

    @staticmethod
    def _repository_context(workspace: str) -> str:
        root = safe_workspace(workspace)
        files = []
        for path in root.rglob("*"):
            if path.is_file() and ".git" not in path.parts:
                try:
                    files.append(str(path.relative_to(root)))
                except ValueError:
                    pass
                if len(files) >= 200:
                    break
        return "Repository files:\n" + "\n".join(sorted(files))

    @staticmethod
    def _validate_workspace(workspace: str) -> dict:
        root = safe_workspace(workspace)
        commands = []
        # The executor is responsible for project-specific tests; always collect Git evidence.
        result = subprocess.run(["git", "-C", str(root), "status", "--short"], text=True, capture_output=True, check=False)
        commands.append({"argv": ["git", "status", "--short"], "returncode": result.returncode, "stdout": redact(result.stdout), "stderr": redact(result.stderr)})
        return {"ok": result.returncode == 0, "commands": commands, "evidence": ["git status collected"]}


def run_goal(original_goal: str, workspace: str, *, planner: Any, executor: Any, reviewer: Any | None = None, state_dir: str = ".orchestrator", max_iterations: int = 3) -> OrchestrationState:
    store = StateStore(state_dir)
    runner = Orchestrator(store, planner, executor, reviewer, max_iterations=max_iterations)
    state = runner.create(original_goal, workspace)
    return runner.run(state.task_id)
