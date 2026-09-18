"""Self-contained V1 GPT-6 / DeepSeek orchestration core."""
from .adapters import DeepSeekHarnessAdapter, FakeAdapter, GPTCompatibleAdapter, ProviderConfig, ProviderError
from .models import ExecutionReport, OrchestrationState, ReviewResult, TaskContract
from .persistence import StateStore
from .workflow import Orchestrator, WorkflowError, run_goal

__all__ = [
    "DeepSeekHarnessAdapter",
    "FakeAdapter",
    "GPTCompatibleAdapter",
    "ProviderConfig",
    "ProviderError",
    "ExecutionReport",
    "OrchestrationState",
    "ReviewResult",
    "TaskContract",
    "StateStore",
    "Orchestrator",
    "WorkflowError",
    "run_goal",
]

