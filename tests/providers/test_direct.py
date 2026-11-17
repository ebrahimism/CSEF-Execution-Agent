"""Contract regressions for two different HTTP APIs; no paid calls are made."""
import json

import pytest

from csef_gate.core import Gate, Refused, encoded
from csef_gate.providers.direct import DirectAPI, DirectAPIAgent, select_provider

SCHEMA = {"type": "object", "properties": {"ok": {"type": "boolean"}},
          "required": ["ok"], "additionalProperties": False}


def openai_response(value, status="completed"):
    return {"status": status, "model": "openai-test",
            "output": [{"type": "message", "content": [
                {"type": "output_text", "text": json.dumps(value)}]}],
            "usage": {"input_tokens": 11, "output_tokens": 4,
                      "input_tokens_details": {"cached_tokens": 3}}}


def anthropic_response(value, reason="end_turn"):
    return {"stop_reason": reason, "model": "anthropic-test",
            "content": [{"type": "text", "text": json.dumps(value)}],
            "usage": {"input_tokens": 12, "output_tokens": 5,
                      "cache_read_input_tokens": 2}}


@pytest.mark.parametrize("provider,response,endpoint,header", [
    ("openai", openai_response({"ok": True}), "/v1/responses", "Authorization"),
    ("anthropic", anthropic_response({"ok": True}), "/v1/messages", "x-api-key"),
])
def test_direct_provider_schema_receipt_without_leaking_key(tmp_path, provider, response, endpoint, header):
    observed = []
    key = "test-secret-do-not-write-to-disk"

    def send(url, headers, payload, timeout):
        observed.append((url, headers, payload, timeout))
        return response

    client = DirectAPI(provider, "explicit-model", api_key=key, send=send)
    result, receipt = client.call(prompt="Return ok", schema=SCHEMA,
                                  folder=tmp_path / "call", control=tmp_path / "control",
                                  role="reviewer")
    assert result == {"ok": True}
    assert receipt["usage"]["cached_input_tokens"] in (2, 3)
    assert receipt["provider"] == provider and receipt["model"] == "explicit-model"
    assert receipt["cost_usd"] is None and receipt["role"] == "reviewer"
    assert observed[0][0].endswith(endpoint) and key in observed[0][1][header]
    assert observed[0][2]["model"] == "explicit-model"
    assert "Return ok" in json.dumps(observed[0][2])
    for path in (tmp_path / "call").iterdir():
        assert key not in path.read_text(encoding="utf-8")


@pytest.mark.parametrize("provider,response", [
    ("openai", openai_response({})),
    ("anthropic", anthropic_response({"ok": "yes"})),
    ("openai", openai_response({"ok": True}, status="incomplete")),
    ("anthropic", anthropic_response({"ok": True}, reason="max_tokens")),
])
def test_bad_model_content_never_counts_as_completed(tmp_path, provider, response):
    client = DirectAPI(provider, "model", api_key="dummy", send=lambda *_: response)
    with pytest.raises(Refused):
        client.call(prompt="p", schema=SCHEMA, folder=tmp_path / "call",
                    control=tmp_path / "control")
    assert not (tmp_path / "call" / "receipt.json").exists()


@pytest.mark.parametrize("provider,response", [
    ("openai", {"status": "completed", "output": [{"type": "message",
        "content": [{"type": "output_text", "text": '{"ok":true,"ok":false}'}]}]}),
    ("anthropic", {"stop_reason": "end_turn", "content": [
        {"type": "text", "text": "not JSON"}]}),
])
def test_malformed_output_is_refused(tmp_path, provider, response):
    client = DirectAPI(provider, "model", api_key="dummy", send=lambda *_: response)
    with pytest.raises(Refused):
        client.call(prompt="p", schema=SCHEMA, folder=tmp_path / "call",
                    control=tmp_path / "control")


def test_missing_key_and_unselected_provider_do_not_launch_codex(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(Refused, match="missing API key"):
        DirectAPI("openai", "model")
    with pytest.raises(Refused, match="missing API key"):
        DirectAPI("anthropic", "model")
    with pytest.raises(Refused, match="select --provider"):
        select_provider(None, None)
    with pytest.raises(Refused, match="explicit model"):
        DirectAPI("openai", "", api_key="dummy")


def test_transport_error_is_not_retried_or_disclosed(tmp_path):
    n = []
    def fail(*args):
        n.append(True)
        raise Refused("provider transport failed; outcome is unknown")
    client = DirectAPI("openai", "model", api_key="secret", send=fail)
    with pytest.raises(Refused, match="outcome is unknown"):
        client.call(prompt="p", schema=SCHEMA, folder=tmp_path / "call",
                    control=tmp_path / "control")
    assert len(n) == 1


def _gate(tmp_path):
    project = tmp_path / "program"
    project.mkdir()
    (project / "app.py").write_text("print(0)\n", encoding="utf-8")
    spec = {"version": 1, "objective": "return JSON integer", "source_files": ["app.py"],
            "editable_files": ["app.py"], "entrypoint": "app.py",
            "max_attempts": 2, "agent_timeout_s": 20, "case_timeout_s": 5,
            "cases": [{"id": "OUTPUT", "args": [], "exit_code": 0,
                       "stdout_json": 4}]}
    spec_path = tmp_path / "spec.json"
    spec_path.write_bytes(encoded(spec))
    gate = Gate.initialize(tmp_path / "control", project, spec_path)
    return gate, gate.prepare()


def _proposal_response(provider, code):
    proposal = {"summary": "scoped fix", "files": [
        {"path": "app.py", "content": code}]}
    return openai_response(proposal) if provider == "openai" else anthropic_response(proposal)


def test_two_direct_api_proposals_share_gate_without_codex(tmp_path, monkeypatch):
    import shutil
    monkeypatch.setattr(shutil, "which", lambda _: None)  # No Codex executable
    gate, run = _gate(tmp_path)
    clients = []
    for provider, value in (("openai", "print(3)\n"), ("anthropic", "print(4)\n")):
        client = DirectAPI(provider, "explicit-model", api_key="dummy",
                           send=lambda *_args, p=provider, v=value:
                               _proposal_response(p, v))
        clients.append(client)
        receipt = gate.agent_attempt(run, DirectAPIAgent(client))
        assert receipt["adapter"] == provider + "-direct"
        assert (gate.candidate(run) / "app.py").read_text() == value
    with gate.connect() as con:
        assert con.execute("SELECT attempts FROM runs WHERE id=?", (run,)).fetchone()[0] == 2
        assert con.execute("SELECT count(*) FROM checkpoints").fetchone()[0] == 0
    # A model's proposal is not a verified acceptance claim.
    with pytest.raises(Refused):
        gate.accept(run)


def test_no_provider_but_intake_status_and_guarded_eval_work(tmp_path, capsys, monkeypatch):
    from csef_gate.__main__ import main
    import shutil
    monkeypatch.setattr(shutil, "which", lambda _: None)
    root = tmp_path / "project"
    assert main(["workflow", "init", "--root", str(root), "--goal", "Design app"]) == 2
    capsys.readouterr()
    assert main(["workflow", "continue", "--root", str(root)]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "awaiting_owner"
    gate, run = _gate(tmp_path)
    assert main(["evaluate", "--control", str(gate.root), "--run-id", run]) == 2
    assert "choose an explicit --executor" in capsys.readouterr().err
