"""Atomic JSON persistence for resumable orchestration tasks."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from threading import RLock
from typing import Any, Dict, Iterable, List, Optional

from .models import OrchestrationState


class StateStore:
    """One JSON file per task with an atomic replace on every write."""

    def __init__(self, root: str | os.PathLike[str]):
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()

    def path_for(self, task_id: str) -> Path:
        if not task_id or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for ch in task_id):
            raise ValueError("invalid task id")
        return self.root / f"{task_id}.json"

    def save(self, state: OrchestrationState | Dict[str, Any]) -> Path:
        payload = state.to_dict() if isinstance(state, OrchestrationState) else dict(state)
        task_id = str(payload.get("task_id") or "")
        path = self.path_for(task_id)
        with self._lock:
            fd, temp_name = tempfile.mkstemp(prefix=f".{task_id}.", suffix=".tmp", dir=str(self.root))
            try:
                with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                    json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
                    handle.write("\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temp_name, path)
            finally:
                try:
                    os.unlink(temp_name)
                except FileNotFoundError:
                    pass
        return path

    def load_dict(self, task_id: str) -> Dict[str, Any]:
        path = self.path_for(task_id)
        with self._lock:
            with path.open("r", encoding="utf-8") as handle:
                value = json.load(handle)
        if not isinstance(value, dict):
            raise ValueError(f"state file is not an object: {path}")
        return value

    def load(self, task_id: str) -> OrchestrationState:
        return OrchestrationState.from_dict(self.load_dict(task_id))

    def exists(self, task_id: str) -> bool:
        return self.path_for(task_id).is_file()

    def list_ids(self) -> List[str]:
        return sorted(path.stem for path in self.root.glob("*.json") if path.is_file())

    def delete(self, task_id: str) -> None:
        # Explicit task-level deletion only; never recursively remove the store.
        self.path_for(task_id).unlink(missing_ok=True)

    def append_event(self, task_id: str, event: Dict[str, Any]) -> None:
        state = self.load(task_id)
        state.metadata.setdefault("events", []).append(dict(event))
        state.touch()
        self.save(state)

