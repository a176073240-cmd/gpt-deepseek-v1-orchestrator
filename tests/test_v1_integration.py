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
