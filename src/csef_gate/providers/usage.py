"""S2 provider request-count quota and optional auditable price estimates.

This is an extension over the existing unified SQLite 'changes' ledger.
It is NOT a monetary hard cap: upstream billing can differ from a rate card.
"""
from __future__ import annotations

import json
import os
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

from ..core import Refused, encoded, now, plain
from ..persistence.sqlite import DATABASE, connection

STATES = ("provider_started", "provider_completed", "provider_unknown")


def _limit() -> int | None:
    raw = os.environ.get("CSEF_PROVIDER_MAX_CALLS")
    if raw is None or raw == "":
        return None
    if not raw.isascii() or not raw.isdecimal() or not 1 <= int(raw) <= 100000:
        raise Refused("invalid CSEF_PROVIDER_MAX_CALLS; expected a positive integer")
    return int(raw)


def reserve(control: Path, provider: str, model: str, role: str) -> int | None:
    """Record an intent before sending, atomically honoring the shared call cap.

    No new database, schema or write access for coding agents is introduced.
    Unknown outcomes continue to consume a reserved slot. Legacy control stores
    are allowed only if a quota was not requested.
    """
    limit = _limit()
    root = Path(control).absolute()
    plain(root)
    path = root / DATABASE
    if not path.is_file():
        if limit is not None:
            raise Refused("provider call cap requires an initialized unified control store")
        return None
    with connection(path) as con:
        con.execute("BEGIN IMMEDIATE")
        n = con.execute(
            "SELECT COUNT(*) FROM changes WHERE status IN (?,?,?)", STATES
        ).fetchone()[0]
        if limit is not None and n >= limit:
            raise Refused("provider call-count cap exhausted; no API request sent")
        payload = encoded({"type": "provider_request", "provider": provider,
                           "model": model, "role": role}).decode()
        result = con.execute(
            "INSERT INTO changes(proposal,status,created) VALUES(?,?,?)",
            (payload, "provider_started", now())
        )
        return result.lastrowid


def settle(control: Path, row_id: int | None, *, completed: bool) -> None:
    if row_id is None:
        return
    root = Path(control).absolute()
    with connection(root / DATABASE) as con:
        con.execute("BEGIN IMMEDIATE")
        result = con.execute(
            "UPDATE changes SET status=? WHERE id=? AND status='provider_started'",
            ("provider_completed" if completed else "provider_unknown", row_id)
        )
        if result.rowcount != 1:
            raise Refused("provider intent state changed; manual reconciliation required")


def _decimal(text, label: str) -> Decimal:
    if not isinstance(text, str):
        raise Refused("provider rate must be a decimal string: " + label)
    try:
        value = Decimal(text)
    except InvalidOperation:
        raise Refused("invalid provider rate: " + label) from None
    if not value.is_finite() or value < 0 or value > Decimal("1000000"):
        raise Refused("provider rate out of bounds: " + label)
    return value


def estimate(provider: str, model: str, usage: dict) -> str | None:
    """Estimate only when caller supplies a pinned exact-model price card.

    Return None for unknown/missing metadata. Never identify estimated cost
    as provider invoice or an enforceable USD cap.
    """
    file = os.environ.get("CSEF_PROVIDER_PRICES_FILE")
    if not file:
        return None
    path = Path(file).absolute()
    plain(path)
    try:
        raw = path.read_bytes()
        if len(raw) > 100_000:
            raise Refused("provider pricing file too large")
        card = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, ValueError, TypeError):
        raise Refused("invalid or missing provider pricing card") from None
    if (not isinstance(card, dict) or set(card) != {"version", "models"}
            or type(card["version"]) is not int or card["version"] != 1
            or not isinstance(card["models"], list) or len(card["models"]) > 200):
        raise Refused("unsupported pricing card")
    rows = [x for x in card["models"] if isinstance(x, dict)
            and x.get("provider") == provider and x.get("model") == model]
    if len(rows) != 1:
        return None
    item = rows[0]
    if set(item) != {"provider", "model", "input", "output", "cached_input", "cache_write"}:
        raise Refused("pricing card model fields must be complete")
    input_count, output_count = usage.get("input_tokens"), usage.get("output_tokens")
    if input_count is None or output_count is None:
        return None
    cached = usage.get("cached_input_tokens") or 0
    cache_write = usage.get("cache_creation_input_tokens") or 0
    if (any(type(x) is not int or x < 0 for x in
            (input_count, output_count, cached, cache_write))
            or (provider == "openai" and cached > input_count)):
        raise Refused("invalid token usage for pricing")
    normal_input = input_count - cached if provider == "openai" else input_count
    prices = {field: _decimal(item[field], field)
              for field in ("input", "output", "cached_input", "cache_write")}
    total = ((prices["input"] * normal_input
              + prices["cached_input"] * cached
              + prices["cache_write"] * cache_write
              + prices["output"] * output_count) / Decimal(1_000_000))
    return format(total.quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP), ".8f")


def snapshot(control: Path) -> dict:
    path = Path(control).absolute() / DATABASE
    plain(path)
    with connection(path) as con:
        rows = con.execute(
            "SELECT status,COUNT(*) AS n FROM changes WHERE status IN (?,?,?) "
            "GROUP BY status", STATES
        ).fetchall()
    totals = {key: 0 for key in STATES}
    totals.update({row["status"]: row["n"] for row in rows})
    return {"schema": 1, "used_calls": sum(totals.values()),
            "call_cap": _limit(), "breakdown": totals,
            "remaining_calls": None if _limit() is None else
                               max(0, _limit() - sum(totals.values())),
            "usd_hard_cap": None, "note": "This is a call-count limit, not a USD billing cap"}
