"""Data contracts for the small, durable V1 orchestration core.

The module deliberately uses dataclasses and plain dictionaries so state can be
saved and resumed without a database or third party runtime.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


@dataclass
class TaskContract:
    """Machine-checkable plan produced by the planner."""

    goal_interpretation: str
    scope: List[str] = field(default_factory=list)
    non_goals: List[str] = field(default_factory=list)
    implementation_plan: List[str] = field(default_factory=list)
    acceptance_criteria: List[str] = field(default_factory=list)
    validation_requirements: List[str] = field(default_factory=list)
    allowed_paths: List[str] = field(default_factory=list)
    risk_notes: List[str] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.goal_interpretation = str(self.goal_interpretation or "").strip()
        if not self.goal_interpretation:
            raise ValueError("goal_interpretation is required")
        for name in (
            "scope",
            "non_goals",
            "implementation_plan",
            "acceptance_criteria",
            "validation_requirements",
            "allowed_paths",
            "risk_notes",
        ):
            value = getattr(self, name)
            if isinstance(value, str):
                value = [value]
            setattr(self, name, [str(item) for item in (value or [])])

    @classmethod
    def from_dict(cls, value: Dict[str, Any]) -> "TaskContract":
        if not isinstance(value, dict):
            raise TypeError("task contract must be an object")
        # Keep unknown planner fields in raw for forward compatibility.
        known = {f.name for f in cls.__dataclass_fields__.values()}
        payload = {k: v for k, v in value.items() if k in known}
        payload.setdefault("raw", {k: v for k, v in value.items() if k not in known})
        return cls(**payload)

    def to_dict(self) -> Dict[str, Any]:
        value = asdict(self)
        if not value.get("raw"):
            value.pop("raw", None)
        return value

    def validate(self) -> List[str]:
        errors: List[str] = []
        if not self.scope:
            errors.append("scope must contain at least one item")
        if not self.implementation_plan:
            errors.append("implementation_plan must contain at least one item")
        if not self.acceptance_criteria:
            errors.append("acceptance_criteria must contain at least one item")
        if not self.validation_requirements:
            errors.append("validation_requirements must contain at least one item")
        return errors


@dataclass
class ExecutionReport:
    """Evidence returned by an executor, independent of its prose response."""

    ok: bool
    summary: str = ""
    changed_files: List[str] = field(default_factory=list)
    git_diff: str = ""
    commands: List[Dict[str, Any]] = field(default_factory=list)
    build_results: List[Dict[str, Any]] = field(default_factory=list)
    test_results: List[Dict[str, Any]] = field(default_factory=list)
    validation_evidence: List[str] = field(default_factory=list)
    unresolved_issues: List[str] = field(default_factory=list)
    session_id: Optional[str] = None
    raw_output: str = ""
    raw_error: str = ""
    started_at: str = field(default_factory=utc_now)
    finished_at: str = field(default_factory=utc_now)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: Dict[str, Any]) -> "ExecutionReport":
        return cls(**{k: v for k, v in value.items() if k in cls.__dataclass_fields__})


@dataclass
class ReviewResult:
    """Strict reviewer result. Verdict is one of PASS, REVISE, BLOCKED."""

    verdict: str
    notes: str = ""
    repair_requirements: List[str] = field(default_factory=list)
    block_reason: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)
    reviewed_at: str = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        self.verdict = str(self.verdict or "").upper().strip()
        aliases = {"ACCEPT": "PASS", "ACCEPTED": "PASS", "REPAIR": "REVISE", "REJECT": "BLOCKED"}
        self.verdict = aliases.get(self.verdict, self.verdict)
        if self.verdict not in {"PASS", "REVISE", "BLOCKED"}:
            raise ValueError("review verdict must be PASS, REVISE, or BLOCKED")
        if isinstance(self.repair_requirements, str):
            self.repair_requirements = [self.repair_requirements]

    @property
    def passed(self) -> bool:
        return self.verdict == "PASS"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: Dict[str, Any]) -> "ReviewResult":
        return cls(**{k: v for k, v in value.items() if k in cls.__dataclass_fields__})


PHASES = ("PLANNING", "EXECUTING", "VALIDATING", "REVIEWING", "COMPLETED", "BLOCKED")


@dataclass
class OrchestrationState:
    """Durable task ledger. Every transition writes this object atomically."""

    task_id: str = field(default_factory=lambda: _id("task"))
    original_goal: str = ""
    workspace: str = ""
    phase: str = "PLANNING"
    iteration: int = 0
    max_iterations: int = 3
    task_contract: Optional[TaskContract] = None
    acceptance_criteria: List[str] = field(default_factory=list)
    deepseek_session_id: Optional[str] = None
    completed_steps: List[str] = field(default_factory=list)
    execution_reports: List[Dict[str, Any]] = field(default_factory=list)
    test_results: List[Dict[str, Any]] = field(default_factory=list)
    reviewer_feedback: List[Dict[str, Any]] = field(default_factory=list)
    block_reason: Optional[str] = None
    baseline_git: Dict[str, Any] = field(default_factory=dict)
    git_state: Dict[str, Any] = field(default_factory=dict)
    timestamps: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.phase not in PHASES:
            raise ValueError(f"unknown phase: {self.phase}")
        if self.max_iterations < 1:
            raise ValueError("max_iterations must be positive")
        if not self.timestamps:
            now = utc_now()
            self.timestamps = {"created_at": now, "updated_at": now}

    @classmethod
    def from_dict(cls, value: Dict[str, Any]) -> "OrchestrationState":
        payload = dict(value)
        contract = payload.get("task_contract")
        if isinstance(contract, dict):
            payload["task_contract"] = TaskContract.from_dict(contract)
        fields = cls.__dataclass_fields__
        return cls(**{k: v for k, v in payload.items() if k in fields})

    def to_dict(self) -> Dict[str, Any]:
        value = asdict(self)
        return value

    def touch(self, event: Optional[str] = None) -> None:
        self.timestamps["updated_at"] = utc_now()
        if event:
            self.timestamps[event] = self.timestamps["updated_at"]

    def transition(self, phase: str) -> None:
        phase = phase.upper()
        if phase not in PHASES:
            raise ValueError(f"unknown phase: {phase}")
        allowed = {
            "PLANNING": {"PLANNING", "EXECUTING", "BLOCKED"},
            "EXECUTING": {"EXECUTING", "VALIDATING", "BLOCKED"},
            "VALIDATING": {"VALIDATING", "REVIEWING", "EXECUTING", "BLOCKED"},
            "REVIEWING": {"REVIEWING", "COMPLETED", "EXECUTING", "BLOCKED"},
            "COMPLETED": {"COMPLETED"},
            "BLOCKED": {"BLOCKED", "PLANNING", "EXECUTING"},
        }
        if phase not in allowed[self.phase]:
            raise ValueError(f"invalid transition {self.phase} -> {phase}")
        self.phase = phase
        self.touch(phase.lower())


def contract_from_response(value: Any) -> TaskContract:
    """Extract a contract from common provider response envelopes."""
    if isinstance(value, TaskContract):
        return value
    if isinstance(value, str):
        import json
        text = value.strip()
        # Models occasionally wrap JSON in a markdown fence despite the schema request.
        if text.startswith("```"):
            lines = text.splitlines()
            if lines and lines[0].lstrip().startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        value = json.loads(text)
    if isinstance(value, dict):
        for key in ("task_contract", "contract", "result", "output"):
            nested = value.get(key)
            if isinstance(nested, dict) and any(k in nested for k in ("goal_interpretation", "scope")):
                value = nested
                break
        return TaskContract.from_dict(value)
    raise TypeError("planner response must be a mapping or TaskContract")
