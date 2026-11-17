"""Opt-in validation of both model APIs with sanitized receipts."""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

from ..core import Refused
from .direct import DirectAPI

SCHEMA = {
    "type": "object",
    "properties": {
        "ok": {"type": "boolean", "const": True},
        "proof": {"type": "string", "const": "csef-live-check"},
    },
    "required": ["ok", "proof"],
    "additionalProperties": False,
}
EXPECTED = {"ok": True, "proof": "csef-live-check"}
PROMPT = (
    'Return exactly this JSON object, without Markdown or commentary: '
    '{"ok":true,"proof":"csef-live-check"}.'
)
PROVIDERS = (("openai", "OPENAI_API_KEY"), ("anthropic", "ANTHROPIC_API_KEY"))


def verify_configuration(models: dict[str, str], *, environ=None) -> None:
    env = os.environ if environ is None else environ
    missing = [name for provider, name in PROVIDERS if not env.get(name, "").strip()]
    if missing:
        raise Refused("missing environment credential(s): " + ", ".join(missing))
    if set(models) != {name for name, _ in PROVIDERS}:
        raise Refused("both providers require explicit model names")
    if any(not isinstance(value, str) or not value.strip() for value in models.values()):
        raise Refused("both model names must be nonempty")


def run_check(models: dict[str, str], *, timeout: int = 60, factory=DirectAPI) -> list[dict]:
    """Exactly one request per provider. No implicit retry or secret logging."""
    verify_configuration(models)
    if not isinstance(timeout, int) or isinstance(timeout, bool) or not 1 <= timeout <= 120:
        raise Refused("timeout must be between 1 and 120 seconds")
    results = []
    with tempfile.TemporaryDirectory(prefix="csef-provider-probe-") as dirname:
        for provider, _ in PROVIDERS:
            client = factory(provider, models[provider])
            result, receipt = client.call(
                prompt=PROMPT, schema=SCHEMA,
                folder=Path(dirname) / provider, control=Path(dirname) / "controller",
                timeout=timeout, role="live-validation",
            )
            if result != EXPECTED:
                raise Refused(provider + " returned unexpected content")
            results.append({
                "provider": provider, "status": "PASS",
                "requested_model": models[provider],
                "reported_model": receipt.get("reported_model"),
                "schema_valid": True, "usage": receipt.get("usage"),
                "elapsed_s": receipt.get("elapsed_s"), "cost_usd": None,
            })
    return results


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="One live request for each direct API")
    parser.add_argument("--openai-model", required=True)
    parser.add_argument("--anthropic-model", required=True)
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args(argv)
    models = {"openai": args.openai_model, "anthropic": args.anthropic_model}
    try:
        results = run_check(models, timeout=args.timeout)
    except Refused as exc:
        print(json.dumps({"status": "FAILED", "reason": str(exc)}, ensure_ascii=False))
        return 2
    except Exception:
        print(json.dumps({"status": "FAILED", "reason": "unexpected validation error"}))
        return 2
    print(json.dumps({
        "status": "PASS", "live_requests": 2, "results": results,
        "note": "USD cost, secure execution and economic advantage remain unverified.",
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
