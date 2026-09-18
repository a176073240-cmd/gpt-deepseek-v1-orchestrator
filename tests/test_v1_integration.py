"""Offline A-E integration tests for the V1 workflow."""
from pathlib import Path
import subprocess, sys
import pytest

from v1_orchestrator import (ExecutionReport, FakeAdapter, Orchestrator, ReviewResult,
                             StateStore, TaskContract)


def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    (root / "README.md").write_text("fixture\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "-c", "user.email=test@example.com", "-c", "user.name=test", "commit", "-qm", "baseline"], cwd=root, check=True)
    return root


def run_with(tmp_path, adapter, **kwargs):
    root = repo(tmp_path)
    runner = Orchestrator(StateStore(tmp_path / "state"), adapter, adapter, adapter, **kwargs)
    created = runner.create("make the fixture better", str(root))
    return runner.run(created.task_id), runner, root


def test_a_planning_and_pass(tmp_path):
    adapter = FakeAdapter()
    state, _, _ = run_with(tmp_path, adapter)
    assert state.phase == "COMPLETED"
    assert state.task_contract is not None
    assert state.acceptance_criteria
    assert adapter.plan_calls == 1


def test_b_execution_evidence(tmp_path):
    adapter = FakeAdapter(reports=[ExecutionReport(ok=True, changed_files=["README.md"], test_results=[{"ok": True}])])
    state, _, _ = run_with(tmp_path, adapter)
    assert state.phase == "COMPLETED"
    assert state.execution_reports[0]["changed_files"] == ["README.md"]
    assert state.test_results and state.git_state["commit"]


def test_c_revise_then_pass(tmp_path):
    adapter = FakeAdapter(reviews=[ReviewResult("REVISE", repair_requirements=["add missing assertion"]), ReviewResult("PASS")])
    state, _, _ = run_with(tmp_path, adapter, max_iterations=3)
    assert state.phase == "COMPLETED"
    assert state.iteration == 2
    assert len(state.execution_reports) == 2
    assert adapter.execute_calls == 2


def test_d_resume_does_not_replan(tmp_path):
    adapter = FakeAdapter()
    root = repo(tmp_path)
    store = StateStore(tmp_path / "state")
    runner = Orchestrator(store, adapter, adapter, adapter)
    created = runner.create("resume me", str(root))
    partial = runner.run(created.task_id, stop_after_phase="EXECUTING")
    assert partial.phase == "EXECUTING"
    resumed = runner.resume(created.task_id)
    assert resumed.phase == "COMPLETED"
    assert adapter.plan_calls == 1


def test_e_blocked_persists_reason_and_resumes(tmp_path):
    adapter = FakeAdapter(reviews=[ReviewResult("BLOCKED", block_reason="choose a product policy")])
    root = repo(tmp_path)
    store = StateStore(tmp_path / "state")
    runner = Orchestrator(store, adapter, adapter, adapter)
    created = runner.create("needs a decision", str(root))
    blocked = runner.run(created.task_id)
    assert blocked.phase == "BLOCKED"
    assert blocked.block_reason == "choose a product policy"
    blocked.phase = "EXECUTING"
    blocked.block_reason = None
    adapter.reviews.append(ReviewResult("PASS"))
    store.save(blocked)
    resumed = runner.resume(created.task_id)
    assert resumed.phase == "COMPLETED"


def test_e_human_question_answer_round_trip(tmp_path):
    """A persisted human question can be answered without re-planning."""
    adapter = FakeAdapter()
    root = repo(tmp_path)
    store = StateStore(tmp_path / "state")
    runner = Orchestrator(store, adapter, adapter, adapter)
    created = runner.create("needs a human choice", str(root))

    partial = runner.run(created.task_id, stop_after_phase="EXECUTING")
    assert partial.phase == "EXECUTING"

    blocked = runner.request_input(
        created.task_id,
        "Which compatibility policy should be used?",
        context="Two existing formats are present.",
    )
    assert blocked.phase == "BLOCKED"
    pending = blocked.metadata["pending_question"]
    assert pending["status"] == "pending"

    answered = runner.answer_input(
        created.task_id,
        "Keep the existing format and add the new one.",
        question_id=pending["question_id"],
    )
    assert answered.phase == "EXECUTING"
    resumed = runner.resume(created.task_id)

    assert resumed.phase == "COMPLETED"
    assert resumed.metadata["human_answer"] == "Keep the existing format and add the new one."
    assert adapter.plan_calls == 1


def test_validation_runs_contract_commands_and_records_evidence(tmp_path):
    """Planner-supplied checks run in the repository and are persisted."""
    root = repo(tmp_path)
    command = f'"{Path(sys.executable).as_posix()}" -c "print(\'validation-ok\')"'
    contract = TaskContract(
        goal_interpretation="run a validation check",
        scope=["fixture"],
        implementation_plan=["run check"],
        acceptance_criteria=["check succeeds"],
        validation_requirements=["the check exits successfully"],
        validation_commands=[command],
        allowed_paths=["."],
    )
    adapter = FakeAdapter(contract=contract)
    runner = Orchestrator(StateStore(tmp_path / "state"), adapter, adapter, adapter)
    created = runner.create("run a validation check", str(root))

    state = runner.run(created.task_id)

    assert state.phase == "COMPLETED"
    validation = state.test_results[0]
    command_result = validation["commands"][0]
    assert command_result["returncode"] == 0
    assert "validation-ok" in command_result["stdout"]
    assert validation["ok"] is True
    assert "executed 1 validation command(s)" in validation["evidence"]


def test_validation_failure_is_recorded_as_failed_evidence(tmp_path):
    root = repo(tmp_path)
    command = f'"{Path(sys.executable).as_posix()}" -c "import sys; sys.exit(7)"'
    contract = TaskContract(
        goal_interpretation="run a failing check",
        scope=["fixture"],
        implementation_plan=["run check"],
        acceptance_criteria=["failure is visible"],
        validation_requirements=["the check result is recorded"],
        validation_commands=[command],
        allowed_paths=["."],
    )
    adapter = FakeAdapter(contract=contract)
    runner = Orchestrator(StateStore(tmp_path / "state"), adapter, adapter, adapter)
    created = runner.create("run a failing check", str(root))

    state = runner.run(created.task_id)

    validation = state.test_results[0]
    assert validation["ok"] is False
    assert validation["commands"][0]["returncode"] == 7
    assert any("validation command failed" in issue for issue in validation["issues"])
    assert any("validation command failed" in issue for issue in state.metadata["validation_issues"])


def test_allowed_path_violation_blocks_before_review(tmp_path):
    root = repo(tmp_path)
    contract = TaskContract(
        goal_interpretation="limit edits",
        scope=["src files"],
        implementation_plan=["edit src"],
        acceptance_criteria=["only src changes"],
        validation_requirements=["check changed paths"],
        allowed_paths=["src/**"],
    )
    adapter = FakeAdapter(
        contract=contract,
        reports=[ExecutionReport(ok=True, changed_files=["README.md"])],
    )
    runner = Orchestrator(StateStore(tmp_path / "state"), adapter, adapter, adapter)
    created = runner.create("limit edits", str(root))

    state = runner.run(created.task_id)

    assert state.phase == "BLOCKED"
    assert "outside allowed_paths" in state.block_reason
    assert state.test_results[0]["allowed_path_violations"] == ["README.md"]
    assert adapter.review_calls == 0


def test_allowed_path_rejects_reported_parent_traversal(tmp_path):
    root = repo(tmp_path)
    contract = TaskContract(
        goal_interpretation="reject escaped paths",
        scope=["fixture"],
        implementation_plan=["check paths"],
        acceptance_criteria=["escaped paths are blocked"],
        validation_requirements=["check changed paths"],
        allowed_paths=["secret"],
    )
    adapter = FakeAdapter(
        contract=contract,
        reports=[ExecutionReport(ok=True, changed_files=["../secret"])],
    )
    runner = Orchestrator(StateStore(tmp_path / "state"), adapter, adapter, adapter)
    created = runner.create("reject escaped paths", str(root))

    state = runner.run(created.task_id)

    assert state.phase == "BLOCKED"
    assert state.test_results[0]["allowed_path_violations"] == ["<outside-workspace>"]
