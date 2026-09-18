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


def test_dsh_commands_enable_json_and_resume():
    adapter = DeepSeekHarnessAdapter(executable="dsh")

    fresh = adapter._command('{"task":"inspect"}', session_id=None, resume=False)
    assert fresh[:4] == ["dsh", "--profile", "headless", "--json"]
    assert fresh[-1] == '{"task":"inspect"}'

    resumed = adapter._command('{"task":"continue"}', session_id="session-42", resume=True)
    assert resumed[:4] == ["dsh", "--profile", "headless", "--json"]
    assert resumed[4:6] == ["--session-id", "session-42"]
    assert resumed[-1] == '{"task":"continue"}'


def test_dsh_run_uses_observed_session_and_redacts_evidence(monkeypatch, tmp_path):
    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        return type("Result", (), {
            "returncode": 0,
            "stdout": '{"type":"session","sessionId":"persisted-42"}\n{"type":"final","text":"done"}',
            "stderr": "",
        })()

    monkeypatch.setattr("v1_orchestrator.adapters.subprocess.run", fake_run)
    adapter = DeepSeekHarnessAdapter(executable="dsh", env={"DEEPSEEK_API_KEY": "test-secret"})
    report = adapter.run('{"task":"do work"}', str(tmp_path))

    assert report.session_id == "persisted-42"
    assert captured["command"][:4] == ["dsh", "--profile", "headless", "--json"]
    assert report.commands[0]["argv"] == ["dsh", "--profile", "headless", "--json", "[TASK_PACKET]"]
    assert "test-secret" not in report.raw_output


def test_dsh_run_decodes_harness_output_as_utf8_with_replacement(monkeypatch):
    captured = {}

    def fake_run(command, **kwargs):
        captured.update(kwargs)
        return type("Result", (), {
            "returncode": 0,
            "stdout": '{"type":"session","sessionId":"utf8-42"}\n',
            "stderr": "",
        })()

    monkeypatch.setattr("v1_orchestrator.adapters.subprocess.run", fake_run)
    report = DeepSeekHarnessAdapter(executable="dsh", env={}).run("task", ".")

    assert report.session_id == "utf8-42"
    assert captured["encoding"] == "utf-8"
    assert captured["errors"] == "replace"


def test_dsh_fresh_run_does_not_fabricate_session_id(monkeypatch, tmp_path):
    def fake_run(command, **kwargs):
        return type("Result", (), {"returncode": 1, "stdout": "", "stderr": "failed before session"})()

    monkeypatch.setattr("v1_orchestrator.adapters.subprocess.run", fake_run)
    report = DeepSeekHarnessAdapter(executable="dsh", env={}).run("task", str(tmp_path))
    assert report.session_id is None


def test_dsh_resume_redacts_session_and_task_from_command_evidence(monkeypatch, tmp_path):
    def fake_run(command, **kwargs):
        return type("Result", (), {"returncode": 1, "stdout": "", "stderr": "resume failed"})()

    monkeypatch.setattr("v1_orchestrator.adapters.subprocess.run", fake_run)
    task_packet = '{"private":"task text"}'
    session_id = "session-private-42"
    report = DeepSeekHarnessAdapter(executable="dsh", env={}).run(
        task_packet, str(tmp_path), session_id=session_id, resume=True
    )

    assert report.session_id == session_id
    command_evidence = str(report.commands)
    assert task_packet not in command_evidence
    assert session_id not in command_evidence
    assert report.commands[0]["argv"] == [
        "dsh", "--profile", "headless", "--json",
        "--session-id", "[SESSION_ID]", "[TASK_PACKET]",
    ]


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
