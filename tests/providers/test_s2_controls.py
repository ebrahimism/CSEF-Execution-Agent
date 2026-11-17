"""S2 native payloads, durable quota, unknown outcomes and explicit pricing.

All tests are offline. No real OpenAI/Anthropic API is contacted.
"""
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from csef_gate.core import Refused
from csef_gate.project import ProjectBook
from csef_gate.providers.direct import DirectAPI, _native_schema
from csef_gate.providers import usage as s2_usage, smoke

SCHEMA = {
    "type": "object", "required": ["ok", "code"], "additionalProperties": False,
    "properties": {
        "ok": {"type": "boolean", "const": True},
        "code": {"type": "string", "minLength": 2, "maxLength": 10,
                 "pattern": "^[a-z]+$"}
    },
}


def fake_reply(provider, *, count=9, text='{"ok":true,"code":"valid"}'):
    if provider == "openai":
        return {
            "status": "completed", "model": "explicit-model",
            "output": [{"type": "message", "content": [
                {"type": "output_text", "text": text}]}],
            "usage": {"input_tokens": count, "output_tokens": 5,
                      "input_tokens_details": {"cached_tokens": 2}}
        }
    return {
        "stop_reason": "end_turn", "model": "explicit-model",
        "content": [{"type": "text", "text": text}],
        "usage": {"input_tokens": count, "output_tokens": 5,
                  "cache_read_input_tokens": 2, "cache_creation_input_tokens": 1}
    }


@pytest.mark.parametrize("provider,path", [
    ("openai", ["text", "format"]),
    ("anthropic", ["output_config", "format"])
])
def test_native_json_schema_is_sent_to_the_correct_api_with_local_validation(
        tmp_path, monkeypatch, provider, path):
    monkeypatch.delenv("CSEF_PROVIDER_PRICES_FILE", raising=False)
    monkeypatch.delenv("CSEF_PROVIDER_MAX_CALLS", raising=False)
    seen = []
    def send(url, headers, payload, timeout):
        seen.append((url, headers, payload))
        return fake_reply(provider)
    client = DirectAPI(provider, "explicit-model", api_key="sentinel-secret", send=send)
    value, receipt = client.call(prompt="Example", schema=SCHEMA,
                                 folder=tmp_path / "call", control=tmp_path / "control")
    assert value == {"ok": True, "code": "valid"}
    assert len(seen) == 1
    config = seen[0][2]
    native = config
    for field in path:
        native = native[field]
    assert native["type"] == "json_schema"
    schema = native["schema"]
    assert schema["additionalProperties"] is False
    assert schema["properties"]["ok"]["enum"] == [True]
    assert "minLength" not in schema["properties"]["code"]
    assert "pattern" not in schema["properties"]["code"]
    assert "maxLength" not in schema["properties"]["code"]
    assert receipt["schema_sha256"] != receipt["native_schema_sha256"]
    assert receipt["format_contract"] == "native_json_schema_v1"
    assert receipt["cost_usd"] is None and receipt["cost_estimate_usd"] is None
    if provider == "openai":
        assert "output_config" not in config
        assert config["text"]["format"]["strict"] is True
        assert seen[0][0].endswith("/v1/responses")
    else:
        assert "text" not in config
        assert seen[0][0].endswith("/v1/messages")
    assert "sentinel-secret" not in json.dumps(config)
    for artifact in (tmp_path / "call").iterdir():
        assert "sentinel-secret" not in artifact.read_text(encoding="utf-8")


def test_native_schema_rejects_optional_object_or_unbounded_keys():
    bad = dict(SCHEMA, required=["ok"])
    with pytest.raises(Refused, match="requires all properties"):
        _native_schema(bad)
    bad = dict(SCHEMA, additionalProperties=True)
    with pytest.raises(Refused, match="unbounded"):
        _native_schema(bad)


@pytest.mark.parametrize("provider", ["openai", "anthropic"])
def test_native_model_output_still_checked_by_full_original_schema(tmp_path, provider):
    client = DirectAPI(
        provider, "m", api_key="dummy",
        send=lambda *_: fake_reply(provider, text='{"ok":true,"code":"9"}'))
    with pytest.raises(Refused, match="strict JSON schema validation"):
        client.call(prompt="P", schema=SCHEMA, folder=tmp_path / "call",
                    control=tmp_path / "control")
    assert not (tmp_path / "call" / "receipt.json").exists()


@pytest.mark.parametrize("provider", ["openai", "anthropic"])
def test_usage_rejects_negative_numbers_no_false_completion(tmp_path, provider):
    response = fake_reply(provider)
    response["usage"]["input_tokens"] = -4
    client = DirectAPI(provider, "m", api_key="dummy", send=lambda *_: response)
    with pytest.raises(Refused, match="invalid provider usage"):
        client.call(prompt="P", schema=SCHEMA, folder=tmp_path / "call",
                    control=tmp_path / "control")


def _project(tmp_path):
    return ProjectBook.create(tmp_path / "owner",
                              "Small example", answers={}, facts=[])


def test_durable_call_quota_is_shared_across_providers_and_no_retry(tmp_path, monkeypatch):
    book = _project(tmp_path)
    monkeypatch.setenv("CSEF_PROVIDER_MAX_CALLS", "2")
    monkeypatch.delenv("CSEF_PROVIDER_PRICES_FILE", raising=False)
    for i, provider in enumerate(["openai", "anthropic"]):
        client = DirectAPI(provider, "m", api_key="dummy",
                           send=lambda *_args, p=provider: fake_reply(p))
        value, receipt = client.call(prompt="P", schema=SCHEMA,
                                     folder=tmp_path / ("call" + str(i)), control=book.root)
        assert value["ok"]
    calls = []
    client = DirectAPI("openai", "m", api_key="dummy",
                       send=lambda *_: calls.append(1) or fake_reply("openai"))
    with pytest.raises(Refused, match="cap exhausted"):
        client.call(prompt="P", schema=SCHEMA, folder=tmp_path / "call3",
                    control=book.root)
    assert not calls
    assert s2_usage.snapshot(book.root)["used_calls"] == 2
    assert s2_usage.snapshot(book.root)["remaining_calls"] == 0
    assert s2_usage.snapshot(book.root)["usd_hard_cap"] is None
    with book.connection() as con:
        statuses = [x[0] for x in con.execute(
            "SELECT status FROM changes ORDER BY id")]
    assert statuses == ["provider_completed", "provider_completed"]


def test_unknown_response_consumes_slot_and_not_retried(tmp_path, monkeypatch):
    book = _project(tmp_path)
    monkeypatch.setenv("CSEF_PROVIDER_MAX_CALLS", "1")
    def fail(*args):
        raise Refused("provider transport failed; outcome is unknown")
    client = DirectAPI("openai", "m", api_key="dummy", send=fail)
    with pytest.raises(Refused, match="outcome is unknown"):
        client.call(prompt="P", schema=SCHEMA, folder=tmp_path / "call",
                    control=book.root)
    assert s2_usage.snapshot(book.root)["breakdown"]["provider_unknown"] == 1
    calls=[]
    with pytest.raises(Refused, match="cap exhausted"):
        DirectAPI("openai", "m", api_key="dummy",
                  send=lambda *_: calls.append(1)).call(
                      prompt="P", schema=SCHEMA, folder=tmp_path / "call2",
                      control=book.root)
    assert calls == []


def test_invalid_quota_requires_initialized_control_store(tmp_path, monkeypatch):
    monkeypatch.setenv("CSEF_PROVIDER_MAX_CALLS", "1")
    client = DirectAPI("openai", "m", api_key="dummy",
                       send=lambda *_: pytest.fail("must fail before sending"))
    with pytest.raises(Refused, match="unified control"):
        client.call(prompt="P", schema=SCHEMA, folder=tmp_path / "call",
                    control=tmp_path / "uninitialized")
    monkeypatch.setenv("CSEF_PROVIDER_MAX_CALLS", "unlimited")
    with pytest.raises(Refused, match="positive integer"):
        client.call(prompt="P", schema=SCHEMA, folder=tmp_path / "call2",
                    control=tmp_path / "uninitialized")


def test_call_quota_transaction_prevents_concurrent_overallocation(tmp_path, monkeypatch):
    book = _project(tmp_path)
    monkeypatch.setenv("CSEF_PROVIDER_MAX_CALLS", "1")
    def try_reserve(_):
        try:
            return s2_usage.reserve(book.root, "openai", "m", "test")
        except Refused:
            return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        ids = list(pool.map(try_reserve, [0, 1]))
    assert sum(x is not None for x in ids) == 1
    assert s2_usage.snapshot(book.root)["used_calls"] == 1


def test_explicit_price_card_reports_estimate_only(tmp_path, monkeypatch):
    card = tmp_path / "pricing.json"
    card.write_text(json.dumps({
        "version": 1, "models": [
            {"provider": "openai", "model": "exact",
             "input": "4.00", "output": "20.00",
             "cached_input": "0.40", "cache_write": "0.00"},
            {"provider": "anthropic", "model": "exact",
             "input": "3.00", "output": "15.00",
             "cached_input": "0.30", "cache_write": "3.75"}
        ]
    }))
    monkeypatch.setenv("CSEF_PROVIDER_PRICES_FILE", str(card))
    monkeypatch.delenv("CSEF_PROVIDER_MAX_CALLS", raising=False)
    for provider in ("openai", "anthropic"):
        value, receipt = DirectAPI(provider, "exact", api_key="dummy",
                                  send=lambda *_args, p=provider: fake_reply(p)).call(
            prompt="P", schema=SCHEMA,
            folder=tmp_path / provider, control=tmp_path / "none")
        assert receipt["cost_usd"] is None
        assert receipt["cost_estimate_usd"] is not None
        assert receipt["pricing_origin"] == "owner_provided_versioned_file"
        assert receipt["cost_estimate_usd"] != "0.00000000"
    assert s2_usage.estimate("openai", "not-priced", {
        "input_tokens": 100, "output_tokens": 100
    }) is None


def test_live_smoke_writes_redacted_independently_verifiable_receipt(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "secret-openai")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "secret-anthropic")
    class Fixture:
        def __init__(self, provider, model):
            self.provider=provider
        def call(self, **kwargs):
            return smoke.EXPECTED, {"reported_model": "test",
                                    "usage": {"input_tokens": 3, "output_tokens": 3},
                                    "format_contract": "native_json_schema_v1"}
    receipt = tmp_path / "private.json"
    models = {"openai": "m1", "anthropic": "m2"}
    result = smoke.run_check(models, factory=Fixture, receipt_path=receipt)
    recorded = json.loads(receipt.read_text(encoding="utf-8"))
    assert recorded["status"] == "PASS"
    assert recorded["providers_verified"] == ["openai", "anthropic"]
    assert recorded["actual_api_calls"] == 2
    assert len(result) == 2
    raw = receipt.read_text(encoding="utf-8")
    assert "secret-openai" not in raw and "secret-anthropic" not in raw
    with pytest.raises(Refused, match="receipt exists"):
        smoke.run_check(models, factory=Fixture, receipt_path=receipt)


def test_live_smoke_partial_failure_never_issues_pass_receipt(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "dummy1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy2")
    class Fixture:
        def __init__(self, provider, model):
            self.provider=provider
        def call(self, **kwargs):
            if self.provider == "anthropic":
                raise Refused("provider transport failed; outcome is unknown")
            return smoke.EXPECTED, {"reported_model": "m1", "usage": {}}
    receipt = tmp_path / "private.json"
    with pytest.raises(Refused, match="unknown"):
        smoke.run_check({"openai": "m1", "anthropic": "m2"},
                        factory=Fixture, receipt_path=receipt)
    recorded = json.loads(receipt.read_text(encoding="utf-8"))
    assert recorded["status"] == "INCOMPLETE"
    assert recorded["providers_verified"] == ["openai"]
    assert recorded["unknown_outcomes_possible"]
    assert recorded["actual_api_calls"] is None
