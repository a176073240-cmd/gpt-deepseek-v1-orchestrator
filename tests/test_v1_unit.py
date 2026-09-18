"""Unit checks for provider and security boundaries."""
import os
from v1_orchestrator import ProviderConfig, ProviderError, TaskContract
from v1_orchestrator.adapters import DeepSeekHarnessAdapter
from v1_orchestrator.security import redact, safe_path


def test_required_contract_fields_and_fenced_json():
    text = '```json\n{"goal_interpretation":"x","scope":["s"],"implementation_plan":["i"],"acceptance_criteria":["a"],"validation_requirements":["v"]}\n```'
    from v1_orchestrator.models import contract_from_response
    assert contract_from_response(text).goal_interpretation == "x"


def test_secret_redaction_and_safe_path(tmp_path):
    root = tmp_path / "repo"; root.mkdir(); (root / ".git").mkdir()
    assert "secret" not in redact("api_key=secret", ["secret"])
    try:
        safe_path("../outside", root)
    except PermissionError:
        pass
    else:
        raise AssertionError("path escape was not rejected")


def test_dsh_session_extraction():
    assert DeepSeekHarnessAdapter._session_from_output('{"type":"session","sessionId":"abc"}') == "abc"


def test_missing_gpt_config_is_actionable(monkeypatch):
    for key in ("GPT_API_BASE", "GPT_API_KEY", "GPT_MODEL"):
        monkeypatch.delenv(key, raising=False)
    try:
        from v1_orchestrator import GPTCompatibleAdapter
        GPTCompatibleAdapter()
    except ProviderError as exc:
        assert "GPT_API_BASE" in str(exc)
    else:
        raise AssertionError("missing config did not fail")
