"""Provider adapters: GPT-compatible HTTP, DeepSeek Harness subprocess, and fake.

No provider library is required. Credentials are read from constructor values or
environment variables and are never included in returned evidence.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Optional, Sequence

from .models import ExecutionReport, ReviewResult, TaskContract, contract_from_response, utc_now
from .security import redact, secret_values_from_env


class ProviderError(RuntimeError):
    pass


@dataclass
class ProviderConfig:
    base_url: str
    api_key: Optional[str]
    model: str
    timeout: float = 120.0
    headers: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_env(cls, prefix: str, *, default_base: str = "", default_model: str = "") -> "ProviderConfig":
        p = prefix.upper().rstrip("_")
        return cls(
            base_url=os.getenv(f"{p}_API_BASE", os.getenv(f"{p}_BASE", default_base)).rstrip("/"),
            api_key=os.getenv(f"{p}_API_KEY", os.getenv(f"{p}_KEY")),
            model=os.getenv(f"{p}_MODEL", default_model),
            timeout=float(os.getenv(f"{p}_API_TIMEOUT", "120")),
        )


class GPTCompatibleAdapter:
    """Thin `/chat/completions` adapter compatible with OpenAI-style APIs."""

    def __init__(self, config: ProviderConfig | None = None, *, role: str = "planner"):
        self.config = config or ProviderConfig.from_env("GPT")
        self.role = role
        if not self.config.base_url:
            raise ProviderError("GPT_API_BASE is not configured")
        if not self.config.model:
            raise ProviderError("GPT_MODEL is not configured")
        if not self.config.api_key:
            raise ProviderError("GPT_API_KEY is not configured")

    def complete(self, messages: list[dict[str, str]], *, response_format: Optional[dict] = None, temperature: float = 0.0) -> str:
        payload: Dict[str, Any] = {"model": self.config.model, "messages": messages, "temperature": temperature}
        if response_format:
            payload["response_format"] = response_format
        url = self.config.base_url
        if not url.endswith("/chat/completions"):
            url += "/chat/completions"
        data = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.config.api_key}", **self.config.headers}
        request = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:1000]
            raise ProviderError(f"{self.role} HTTP {exc.code}: {redact(detail, [self.config.api_key or ''])}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise ProviderError(f"{self.role} request failed: {redact(exc, [self.config.api_key or ''])}") from exc
        try:
            body = json.loads(raw)
            return str(body["choices"][0]["message"]["content"])
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise ProviderError(f"{self.role} returned invalid completion payload") from exc

    def plan(self, original_goal: str, context: str = "") -> TaskContract:
        schema = {"type": "object", "required": ["goal_interpretation", "scope", "non_goals", "implementation_plan", "acceptance_criteria", "validation_requirements", "allowed_paths", "risk_notes"]}
        prompt = (
            "Produce only a JSON task contract with these keys: " + ", ".join(schema["required"]) +
            ". Do not invent credentials, expand scope, or ask the executor to redefine the goal.\n" +
            f"Original goal:\n{original_goal}\nRepository context:\n{context}"
        )
        content = self.complete([{"role": "system", "content": "You are a precise software planner."}, {"role": "user", "content": prompt}], response_format={"type": "json_object"})
        contract = contract_from_response(content)
        errors = contract.validate()
        if errors:
            raise ProviderError("planner returned incomplete task contract: " + "; ".join(errors))
        return contract

    def review(self, original_goal: str, contract: TaskContract, evidence: Dict[str, Any], previous_feedback: Iterable[str] = ()) -> ReviewResult:
        packet = {"original_goal": original_goal, "task_contract": contract.to_dict(), "evidence": evidence, "previous_feedback": list(previous_feedback)}
        prompt = "Review the implementation against the original goal and contract. Output JSON only with verdict PASS, REVISE, or BLOCKED; notes; repair_requirements; block_reason. Do not expand scope.\n" + json.dumps(packet, ensure_ascii=False)
        content = self.complete([{"role": "system", "content": "You are an independent code reviewer."}, {"role": "user", "content": prompt}], response_format={"type": "json_object"})
        try:
            text = content.strip()
            if text.startswith("```"):
                lines = text.splitlines()[1:]
                if lines and lines[-1].strip().startswith("```"):
                    lines = lines[:-1]
                text = "\n".join(lines).strip()
            value = json.loads(text)
            if isinstance(value, dict) and isinstance(value.get("review"), dict):
                value = value["review"]
            return ReviewResult.from_dict(value)
        except (ValueError, TypeError) as exc:
            raise ProviderError("reviewer returned invalid JSON verdict") from exc


class DeepSeekHarnessAdapter:
    """Run the documented DeepSeek Harness headless CLI in a bounded subprocess."""

    def __init__(self, executable: str = "dsh", model: Optional[str] = None, timeout: float = 3600.0, env: Optional[dict] = None):
        self.executable = executable
        self.model = model or os.getenv("DEEPSEEK_MODEL", "")
        self.timeout = timeout
        self.env = dict(env or os.environ)

    @staticmethod
    def _session_from_output(output: str) -> Optional[str]:
        """Extract a session identity from text/JSONL without retaining secrets.

        Different dsh versions have emitted ``session_id``, ``sessionId`` and
        nested ``session.id`` fields.  Parse each JSON line first and fall back
        to a conservative textual match; arbitrary output is never interpreted
        as an identity.
        """
        def find(value: Any) -> Optional[str]:
            if isinstance(value, dict):
                for key in ("session_id", "sessionId", "session", "conversation_id", "conversationId"):
                    item = value.get(key)
                    if isinstance(item, str) and item and len(item) <= 256:
                        if key == "session" and item.startswith("{"):
                            continue
                        return item
                    if key == "session" and isinstance(item, dict):
                        nested = item.get("id") if isinstance(item.get("id"), str) else find(item)
                        if nested:
                            return nested
                for item in value.values():
                    nested = find(item)
                    if nested:
                        return nested
            elif isinstance(value, list):
                for item in value:
                    nested = find(item)
                    if nested:
                        return nested
            return None

        # Handle a complete JSON payload as well as JSONL event streams.
        candidates = [output] + output.splitlines()
        for line in candidates:
            text = line.strip()
            if not text:
                continue
            try:
                identity = find(json.loads(text))
            except (ValueError, TypeError):
                identity = None
            if identity:
                return identity
        # Some versions print ``session_id=<id>`` in a human-readable line.
        import re
        match = re.search(r"\b(?:session[_-]?id|conversation[_-]?id)\s*[:=]\s*([A-Za-z0-9_.:/-]{1,256})", output, re.I)
        return match.group(1) if match else None

    def _command(self, task_packet: str, *, session_id: Optional[str], resume: bool) -> list[str]:
        """Build the documented dsh invocation.

        Headless resume is an explicit ``--session-id`` flag.  Keep the task as
        one argv element so shell metacharacters in a goal cannot be evaluated.
        """
        executable = self.executable
        if os.name == "nt" and not os.path.isabs(executable):
            executable = shutil.which(executable) or executable
        command = [executable, "--profile", "headless"]
        if resume and session_id:
            command.extend(["--session-id", session_id])
        command.append(task_packet)
        return command

    def run(self, task_packet: str, workspace: str, *, session_id: Optional[str] = None, resume: bool = False) -> ExecutionReport:
        started = utc_now()
        session_id = session_id or f"dsh-{uuid.uuid4().hex[:12]}"
        command = self._command(task_packet, session_id=session_id, resume=resume)
        safe_argv = [*command[:3], *(["[SESSION_ID]"] if resume and session_id else []), "[TASK_PACKET]"]
        child_env = dict(self.env)
        # Project-side alias accepted by this wrapper; the harness itself reads
        # DEEPSEEK_BASE_URL.  Do not overwrite an explicit harness value.
        if child_env.get("DEEPSEEK_BASE_URL") is None and child_env.get("DEEPSEEK_API_BASE"):
            child_env["DEEPSEEK_BASE_URL"] = child_env["DEEPSEEK_API_BASE"]
        if self.model:
            # dsh currently accepts provider configuration from its environment; retain model for adapters that support it.
            child_env.setdefault("DEEPSEEK_MODEL", self.model)
        secrets = secret_values_from_env(child_env)
        try:
            proc = subprocess.run(command, cwd=workspace, env=child_env, text=True, capture_output=True, timeout=self.timeout, check=False, shell=False)
            output = redact(proc.stdout or "", secrets)
            error = redact(proc.stderr or "", secrets)
            observed_session = self._session_from_output(output) or session_id
            return ExecutionReport(ok=proc.returncode == 0, summary=output[-4000:], raw_output=output, raw_error=error, session_id=observed_session, commands=[{"argv": safe_argv, "returncode": proc.returncode, "resumed": bool(resume)}], started_at=started, finished_at=utc_now())
        except FileNotFoundError as exc:
            return ExecutionReport(ok=False, summary="DeepSeek Harness executable not found", raw_error=redact(str(exc), secrets), session_id=session_id, commands=[{"argv": safe_argv, "error": "not_found", "resumed": bool(resume)}], started_at=started, finished_at=utc_now())
        except subprocess.TimeoutExpired as exc:
            return ExecutionReport(ok=False, summary="DeepSeek Harness timed out", raw_output=redact(exc.stdout or "", secrets), raw_error=redact(exc.stderr or "", secrets), session_id=session_id, commands=[{"argv": safe_argv, "error": "timeout", "resumed": bool(resume)}], started_at=started, finished_at=utc_now())
        except OSError as exc:
            return ExecutionReport(ok=False, summary="DeepSeek Harness could not start", raw_error=redact(str(exc), secrets), session_id=session_id, commands=[{"argv": safe_argv, "error": "os_error", "resumed": bool(resume)}], started_at=started, finished_at=utc_now())


class FakeAdapter:
    """Deterministic offline adapter for integration tests and demos."""

    def __init__(self, *, contract: Optional[TaskContract] = None, reports: Optional[Iterable[ExecutionReport]] = None, reviews: Optional[Iterable[ReviewResult]] = None):
        self.contract = contract
        self.reports = list(reports or [])
        self.reviews = list(reviews or [])
        self.plan_calls = self.execute_calls = self.review_calls = 0

    def plan(self, original_goal: str, context: str = "") -> TaskContract:
        self.plan_calls += 1
        if self.contract:
            return self.contract
        return TaskContract(goal_interpretation=original_goal, scope=["repository changes required by goal"], non_goals=["unrelated refactors"], implementation_plan=["inspect repository", "implement requested behavior", "run validation"], acceptance_criteria=["requested behavior works", "existing tests remain passing"], validation_requirements=["run project tests"], allowed_paths=["."], risk_notes=[])

    def run(self, task_packet: str, workspace: str, *, session_id: Optional[str] = None, resume: bool = False) -> ExecutionReport:
        self.execute_calls += 1
        if self.reports:
            report = self.reports.pop(0)
            if report.session_id is None:
                report.session_id = session_id
            return report
        return ExecutionReport(ok=True, summary="fake executor completed", session_id=session_id)

    def review(self, original_goal: str, contract: TaskContract, evidence: Dict[str, Any], previous_feedback: Iterable[str] = ()) -> ReviewResult:
        self.review_calls += 1
        if self.reviews:
            return self.reviews.pop(0)
        return ReviewResult("PASS", notes="fake review passed")


