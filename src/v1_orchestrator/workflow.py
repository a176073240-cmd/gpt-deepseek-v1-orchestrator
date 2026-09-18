"""Resumable PLANNING -> EXECUTING -> VALIDATING -> REVIEWING workflow."""
from __future__ import annotations

import json
import os
import fnmatch
import shlex
import subprocess
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from .models import ExecutionReport, OrchestrationState, ReviewResult, TaskContract, utc_now
from .persistence import StateStore
from .security import git_diff, git_snapshot, safe_workspace, redact, secret_values_from_env


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
        validation = self._validate_workspace(
            state.workspace,
            contract=state.task_contract,
            reported_changed_files=report.get("changed_files", []),
            baseline_commit=state.baseline_git.get("commit"),
        )
        state.test_results.append(validation)
        if not report.get("ok", False):
            state.metadata.setdefault("validation_issues", []).append("executor reported failure")
        if not validation.get("ok", False):
            state.metadata.setdefault("validation_issues", []).extend(
                str(issue) for issue in validation.get("issues", [])
            )
        state.metadata["git_diff"] = git_diff(state.workspace, state.baseline_git.get("commit"))
        state.git_state = git_snapshot(state.workspace)
        state.completed_steps.append(f"validation-{state.iteration + 1}")
        violations = validation.get("allowed_path_violations", [])
        if violations:
            # A path-policy violation is a safety boundary, so do not hand it
            # to a reviewer as an ordinary repair request.  Persist all Git
            # evidence above, then stop before another executor call.
            self._block(
                state,
                "changed files outside allowed_paths: " + ", ".join(violations),
            )
            return
        state.transition("REVIEWING")

    def _reviewing(self, state: OrchestrationState) -> None:
        evidence = {"execution_report": state.execution_reports[-1] if state.execution_reports else {}, "test_results": state.test_results[-1] if state.test_results else {}, "validation_issues": state.metadata.get("validation_issues", []), "git_diff": state.metadata.get("git_diff", ""), "git_state": state.git_state}
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
    def _validate_workspace(
        workspace: str,
        *,
        contract: Optional[TaskContract] = None,
        reported_changed_files: Optional[list[str]] = None,
        baseline_commit: Optional[str] = None,
        command_timeout: float = 300.0,
    ) -> dict:
        root = safe_workspace(workspace)
        commands = []
        issues: list[str] = []
        secrets = secret_values_from_env()

        # The executor is responsible for project-specific tests, but the
        # planner may provide concrete validation commands.  Parse each command
        # into argv and always use shell=False so shell metacharacters are never
        # evaluated by a child shell.
        validation_commands = list(getattr(contract, "validation_commands", ()) or ())
        for command in validation_commands:
            command_text = str(command or "").strip()
            entry: dict[str, Any] = {"command": redact(command_text, secrets)}
            if not command_text:
                entry.update({"error": "empty_command", "returncode": None})
                commands.append(entry)
                issues.append("validation command is empty")
                continue
            try:
                argv = shlex.split(command_text, posix=True)
            except ValueError as exc:
                entry.update({"error": "invalid_command", "detail": redact(str(exc), secrets), "returncode": None})
                commands.append(entry)
                issues.append(f"invalid validation command: {redact(str(exc), secrets)}")
                continue
            if not argv:
                entry.update({"error": "empty_command", "returncode": None})
                commands.append(entry)
                issues.append("validation command is empty")
                continue
            # Keep command evidence useful without persisting a workspace path
            # or inline credentials.  The actual subprocess receives argv.
            safe_argv = [redact(token, secrets) for token in argv]
            entry["argv"] = safe_argv
            try:
                result = subprocess.run(
                    argv,
                    cwd=str(root),
                    text=True,
                    capture_output=True,
                    check=False,
                    shell=False,
                    timeout=command_timeout,
                )
            except subprocess.TimeoutExpired as exc:
                entry.update(
                    {
                        "returncode": None,
                        "error": "timeout",
                        "stdout": redact(exc.stdout or "", secrets),
                        "stderr": redact(exc.stderr or "", secrets),
                    }
                )
                issues.append(f"validation command timed out: {safe_argv[0]}")
                commands.append(entry)
                continue
            except (OSError, ValueError) as exc:
                entry.update({"returncode": None, "error": "could_not_start", "stderr": redact(str(exc), secrets)})
                issues.append(f"validation command could not start: {safe_argv[0]}")
                commands.append(entry)
                continue
            entry.update(
                {
                    "returncode": result.returncode,
                    "stdout": redact(result.stdout, secrets),
                    "stderr": redact(result.stderr, secrets),
                }
            )
            commands.append(entry)
            if result.returncode != 0:
                issues.append(f"validation command failed ({result.returncode}): {safe_argv[0]}")

        # Always collect Git evidence, including files the executor omitted from
        # its self-reported completion packet.  This makes the allowed-path
        # check authoritative over the actual workspace state.
        result = subprocess.run(["git", "-C", str(root), "status", "--short"], text=True, capture_output=True, check=False)
        commands.append({"argv": ["git", "status", "--short"], "returncode": result.returncode, "stdout": redact(result.stdout, secrets), "stderr": redact(result.stderr, secrets)})
        if result.returncode != 0:
            issues.append("git status failed")

        changed_files = Orchestrator._changed_files(root, baseline=baseline_commit)
        # ``git diff`` against the baseline is assembled by the caller for the
        # reviewer.  Here we use the current status plus the executor report;
        # this also catches untracked files that git diff does not list.
        status_files = Orchestrator._status_changed_files(result.stdout)
        all_changed = []
        for item in [*(reported_changed_files or []), *status_files, *changed_files]:
            normalized = Orchestrator._normalize_changed_file(item, root)
            if normalized not in all_changed:
                all_changed.append(normalized)

        allowed_paths = list(getattr(contract, "allowed_paths", ()) or ()) if contract is not None else []
        violations: list[str] = []
        if allowed_paths:
            violations = [path for path in all_changed if path and not Orchestrator._path_allowed(path, allowed_paths)]
            if violations:
                issues.append("changed files outside allowed_paths: " + ", ".join(violations))
        evidence = ["git status collected"]
        if validation_commands:
            evidence.append(f"executed {len(validation_commands)} validation command(s)")
        if allowed_paths:
            evidence.append("allowed_paths checked against reported and workspace changes")
        return {
            "ok": result.returncode == 0 and not issues,
            "commands": commands,
            "evidence": evidence,
            "issues": issues,
            "changed_files": all_changed,
            "allowed_paths": allowed_paths,
            "allowed_path_violations": violations,
        }

    @staticmethod
    def _status_changed_files(status: str) -> list[str]:
        """Extract paths from porcelain status output without exposing cwd."""
        paths: list[str] = []
        for line in str(status or "").splitlines():
            if len(line) < 3:
                continue
            payload = line[3:]
            # Rename/copy records are ``old -> new``; the destination is the
            # path that must be allowed.
            if " -> " in payload:
                payload = payload.rsplit(" -> ", 1)[-1]
            payload = payload.strip().strip('"')
            if payload:
                paths.append(payload)
        return paths

    @staticmethod
    def _changed_files(root: Path, baseline: Optional[str] = None) -> list[str]:
        """Return tracked and untracked changed paths relative to *root*."""
        args = ["git", "-C", str(root), "diff", "--name-only"]
        if baseline:
            args.append(baseline)
        args.append("--")
        diff = subprocess.run(args, text=True, capture_output=True, check=False)
        others = subprocess.run(
            ["git", "-C", str(root), "ls-files", "--others", "--exclude-standard"],
            text=True,
            capture_output=True,
            check=False,
        )
        return [line.strip() for line in (diff.stdout + "\n" + others.stdout).splitlines() if line.strip()]

    @staticmethod
    def _normalize_changed_file(value: object, root: Path) -> str:
        raw = str(value or "").strip().strip('"').replace("\\", "/")
        if not raw:
            return ""
        candidate = Path(raw)
        if candidate.is_absolute():
            try:
                raw = candidate.resolve().relative_to(root).as_posix()
            except ValueError:
                return "<outside-workspace>"
        while raw.startswith("./"):
            raw = raw[2:]
        # Executor-reported paths are untrusted. A relative traversal must not
        # be made safe merely by string normalization below.
        if raw == ".." or raw.startswith("../"):
            return "<outside-workspace>"
        return raw or "."

    @staticmethod
    def _path_allowed(path: str, allowed_paths: list[str]) -> bool:
        if path == "<outside-workspace>":
            return False
        rel = str(path).replace("\\", "/")
        while rel.startswith("./"):
            rel = rel[2:]
        if rel == ".." or rel.startswith("../") or rel.startswith("/"):
            return False
        for rule_value in allowed_paths:
            rule = str(rule_value or "").strip().replace("\\", "/")
            if not rule or rule in {".", "./", "*", "**"}:
                return True
            # Rules that escape the repository can never grant permission.
            if rule.startswith("/") or rule == ".." or rule.startswith("../"):
                continue
            while rule.startswith("./"):
                rule = rule[2:]
            if fnmatch.fnmatchcase(rel, rule):
                return True
            # A plain directory rule grants its descendants.  Wildcard rules
            # retain their exact fnmatch semantics.
            if not any(mark in rule for mark in "*?[") and rel.startswith(rule.rstrip("/") + "/"):
                return True
        return False


def run_goal(original_goal: str, workspace: str, *, planner: Any, executor: Any, reviewer: Any | None = None, state_dir: str = ".orchestrator", max_iterations: int = 3) -> OrchestrationState:
    store = StateStore(state_dir)
    runner = Orchestrator(store, planner, executor, reviewer, max_iterations=max_iterations)
    state = runner.create(original_goal, workspace)
    return runner.run(state.task_id)
