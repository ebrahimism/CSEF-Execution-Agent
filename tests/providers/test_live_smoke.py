"""Zero-cost contract tests for opt-in API validation."""
import json
import pytest
from csef_gate.core import Refused
from csef_gate.providers import smoke

MODELS = {"openai": "model-openai", "anthropic": "model-anthropic"}


def test_missing_key_blocks_both_providers_before_network(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    calls = []
    def forbidden(*args):
        calls.append(args)
        raise AssertionError("network must not be contacted")
    with pytest.raises(Refused, match="ANTHROPIC_API_KEY"):
        smoke.run_check(MODELS, factory=forbidden)
    assert not calls


def test_two_calls_and_redacted_report(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "secret-1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "secret-2")
    seen = []
    class FakeClient:
        def __init__(self, provider, model):
            self.provider, self.model = provider, model
        def call(self, **kwargs):
            seen.append((self.provider, self.model, kwargs))
            return smoke.EXPECTED, {
                "reported_model": self.model,
                "usage": {"input_tokens": 5, "output_tokens": 7},
                "elapsed_s": 0.2, "secret_field": "do-not-copy",
            }
    result = smoke.run_check(MODELS, factory=FakeClient)
    assert len(seen) == 2
    assert [x["provider"] for x in result] == ["openai", "anthropic"]
    for provider, model, params in seen:
        assert model == MODELS[provider]
        assert params["schema"] == smoke.SCHEMA
        assert params["timeout"] == 60
        assert params["role"] == "live-validation"
    output = json.dumps(result)
    assert "do-not-copy" not in output
    assert "secret-1" not in output and "secret-2" not in output
    assert all(x["cost_usd"] is None and x["status"] == "PASS" for x in result)


def test_mismatched_result_is_refused(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy")
    class FakeClient:
        def __init__(self, provider, model):
            pass
        def call(self, **kwargs):
            return {"ok": True, "proof": "invalid"}, {}
    with pytest.raises(Refused, match="unexpected content"):
        smoke.run_check(MODELS, factory=FakeClient)


@pytest.mark.parametrize("timeout", [0, 121, True, 1.5])
def test_invalid_timeout(monkeypatch, timeout):
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy")
    with pytest.raises(Refused, match="timeout"):
        smoke.run_check(MODELS, timeout=timeout, factory=lambda *a: None)


def test_missing_credentials_are_not_printed(monkeypatch, capsys):
    monkeypatch.setenv("OPENAI_API_KEY", "secret-not-to-print")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert smoke.main(["--openai-model", "m1", "--anthropic-model", "m2"]) == 2
    output = capsys.readouterr().out
    assert json.loads(output)["status"] == "FAILED"
    assert "secret-not-to-print" not in output
