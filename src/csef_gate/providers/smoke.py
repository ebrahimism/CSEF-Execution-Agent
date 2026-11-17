"""Opt-in validation of both model APIs with sanitized receipts."""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

from ..core import Refused, encoded, plain, now
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


def _write_receipt(path: Path | None, *, status: str, models: dict,
                   results: list[dict]) -> None:
    if path is None:
        return
    path = Path(path).absolute()
    plain(path)
    if not path.parent.is_dir():
        raise Refused("live validation receipt parent directory does not exist")
    # Create-once only; never overwrite old evidence or leak credentials.
    item = {"version": 1, "created": now(), "status": status,
            "providers_requested": sorted(models), "providers_verified": [
                result["provider"] for result in results],
            "results": results, "actual_api_calls": len(results) if status == "PASS" else None,
            "unknown_outcomes_possible": status != "PASS",
            "source": "opt_in_owner_credentialed_live_check"}
    try:
        with path.open("xb") as output:
            output.write(encoded(item))
    except FileExistsError:
        raise Refused("receipt exists; never overwrite historical live validation") from None


def run_check(models: dict[str, str], *, timeout: int = 60, factory=DirectAPI,
              receipt_path: Path | None = None) -> list[dict]:
    """Exactly one request per provider, no implicit retry, redacted receipt.

    Successful code + CI fixtures never imply live access. A partially successful
    real run records INCOMPLETE, not PASS, and stops rather than retrying blindly.
    """
    verify_configuration(models)
    if type(timeout) is not int or not 1 <= timeout <= 120:
        raise Refused("timeout must be between 1 and 120 seconds")
    if receipt_path is not None:
        target = Path(receipt_path).absolute()
        plain(target)
        if target.exists():
            raise Refused("receipt exists; choose a new private path before any API call")
    results = []
    try:
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
                    "elapsed_s": receipt.get("elapsed_s"),
                    "format_contract": receipt.get("format_contract"),
                    "cost_usd": None,
                    "cost_estimate_usd": receipt.get("cost_estimate_usd"),
                })
    except Exception:
        _write_receipt(receipt_path, status="INCOMPLETE", models=models, results=results)
        raise
    _write_receipt(receipt_path, status="PASS", models=models, results=results)
    return results


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="One live request for each direct API")
    parser.add_argument("--openai-model", required=True)
    parser.add_argument("--anthropic-model", required=True)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--receipt", type=Path, help="private create-once JSON proof file")
    args = parser.parse_args(argv)
    models = {"openai": args.openai_model, "anthropic": args.anthropic_model}
    try:
        results = run_check(models, timeout=args.timeout, receipt_path=args.receipt)
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
