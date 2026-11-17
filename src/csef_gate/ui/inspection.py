"""Read-only S0–S7 observability adapter; Gate remains the only authority.

No SQL schema changes, model calls or candidate execution. Every status is
derived from the trusted owner store, or marked unverified. Never read or send
candidate source, prompts, secrets or unbounded execution logs to the browser.
"""
from __future__ import annotations

import re
from pathlib import Path

from ..core import Refused, digest, encoded, parse_json, plain, read_json
from ..project import ProjectBook
from ..persistence.sqlite import DATABASE
from ..providers.usage import snapshot as provider_snapshot

RUN_ID = re.compile(r"run-[0-9a-f]{32}\Z")
MAX_RUNS = 50
MAX_ATTEMPTS = 80
MAX_EVALUATIONS = 80


def _control(book: ProjectBook):
    if book.db.name != DATABASE:
        raise Refused("dashboard evidence requires the unified control store")
    return book.connection()


def _valid_report(path: str, report_hash: str | None) -> dict | None:
    """Return only a bounded, integrity-checked evaluation report."""
    if not isinstance(path, str) or not isinstance(report_hash, str):
        return None
    target = Path(path)
    plain(target)
    try:
        if not target.is_file() or target.stat().st_size > 512_000:
            return None
        content = target.read_bytes()
        if digest(content) != report_hash:
            return None
        report = parse_json(content.decode("utf-8"))
        return report if isinstance(report, dict) else None
    except (OSError, ValueError, TypeError, UnicodeError):
        return None


def inspection(book: ProjectBook) -> dict:
    """One consistent, bounded presentation snapshot from existing SQL tables."""
    owner = book.current()
    with _control(book) as con:
        runs = [dict(x) for x in con.execute(
            "SELECT id,status,attempts,created FROM runs ORDER BY created DESC LIMIT ?",
            (MAX_RUNS,))]
        attempts = [dict(x) for x in con.execute(
            "SELECT id,run_id,status,created FROM attempts ORDER BY created DESC LIMIT ?",
            (MAX_ATTEMPTS,))]
        evaluations = [dict(x) for x in con.execute(
            "SELECT id,run_id,status,source_hash,spec_hash,report,report_hash,created "
            "FROM evaluations ORDER BY created DESC LIMIT ?", (MAX_EVALUATIONS,))]
        checkpoints = [dict(x) for x in con.execute(
            "SELECT run_id,evaluation_id,source_hash,spec_hash,report_hash,created "
            "FROM checkpoints ORDER BY created DESC LIMIT ?", (MAX_RUNS,))]
        changes = [dict(x) for x in con.execute(
            "SELECT id,status,created,proposal FROM changes "
            "ORDER BY id DESC LIMIT 200")]
        calls = [dict(x) for x in con.execute(
            "SELECT id,role,status,receipt,created FROM calls "
            "ORDER BY id DESC LIMIT 100")]
        # The store may not yet have a gate config or any runs.
        gate_config = con.execute(
            "SELECT spec_hash,baseline_hash FROM config LIMIT 1").fetchone()
    checkpoint_by_run = {x["run_id"]: x for x in checkpoints}
    evaluation_by_id = {x["id"]: x for x in evaluations}
    observed = []
    for item in evaluations:
        report = _valid_report(item["report"], item["report_hash"])
        cases = []
        verified_boundary = False
        if report is not None:
            for case in report.get("cases", [])[:100]:
                if isinstance(case, dict):
                    cases.append({"id": case.get("id"), "passed": case.get("passed") is True})
            verified_boundary = bool(
                isinstance(report.get("boundary"), dict)
                and report["boundary"].get("verified") is True
                and report.get("measurement_only") is False)
        observed.append({
            "id": item["id"], "run_id": item["run_id"], "status": item["status"],
            "created": item["created"], "report_integrity": report is not None,
            "verified_boundary": verified_boundary,
            "cases": cases,
        })
    for run in runs:
        ck = checkpoint_by_run.get(run["id"])
        ev = evaluation_by_id.get(ck["evaluation_id"]) if ck else None
        report = _valid_report(ev["report"], ev["report_hash"]) if ev else None
        run["accepted_checkpoint"] = bool(
            ck and ev and run["status"] == "accepted"
            and ev["status"] == "pass"
            and ev["report_hash"] == ck["report_hash"]
            and ev["source_hash"] == ck["source_hash"]
            and ev["spec_hash"] == ck["spec_hash"]
            and report and report.get("status") == "pass"
            and report.get("measurement_only") is False
            and isinstance(report.get("boundary"), dict)
            and report["boundary"].get("verified") is True
            and report.get("project_sha256") == owner["sha256"])
        run["delivery_package"] = "not_tracked"
        run["can_resume_automatically"] = False
        run["resume_reason"] = "requires_trusted_reconciliation"
    planned = []
    packages = []
    accepted_run_ids = {run["id"] for run in runs if run["accepted_checkpoint"]}
    for row in changes:
        try:
            value = parse_json(row["proposal"])
        except (ValueError, TypeError, UnicodeError):
            continue
        if not isinstance(value, dict):
            continue
        if (row["status"] == "delivered" and value.get("type") == "verified_delivery"
                and value.get("run_id") in accepted_run_ids
                and value.get("owner_sha256") == owner["sha256"]
                and isinstance(value.get("archive_sha256"), str)):
            target = book.root / "deliveries" / (value["run_id"] + ".zip")
            plain(target)
            try:
                if target.is_file() and target.stat().st_size <= 12_000_000:
                    if digest(target.read_bytes()) == value["archive_sha256"]:
                        packages.append({"run_id": value["run_id"],
                                         "sha256": value["archive_sha256"],
                                         "name": value["run_id"] + ".zip"})
            except (OSError, ValueError):
                pass
        if value.get("type") in ("factory_task", "factory_run"):
            planned.append({
                "type": value["type"], "task_id": value.get("task_id"),
                "run_id": value.get("run_id"), "status": row["status"],
                "created": row["created"],
            })
    for run in runs:
        if any(p["run_id"] == run["id"] for p in packages):
            run["delivery_package"] = "verified"
    call_rows = []
    for row in calls:
        receipt = None
        if row["receipt"]:
            try:
                value = parse_json(row["receipt"])
                if isinstance(value, dict):
                    raw_usage = value.get("usage")
                    receipt = {
                        "provider": value.get("provider") if value.get("provider")
                                    in ("openai", "anthropic") else None,
                        "model": value.get("model") if isinstance(value.get("model"), str) else None,
                        "elapsed_s": value.get("elapsed_s") if type(value.get("elapsed_s")) in (int, float) else None,
                        "usage": {
                            "input_tokens": raw_usage.get("input_tokens"),
                            "output_tokens": raw_usage.get("output_tokens")
                        } if isinstance(raw_usage, dict) else None,
                        "cost_usd": None,
                    }
            except (ValueError, TypeError, UnicodeError):
                pass
        call_rows.append({"id": row["id"], "role": row["role"],
                          "status": row["status"], "created": row["created"],
                          "receipt": receipt})
    # Avoid reporting a checkpoint as a deliverable, or an unknown cost as $0.
    try:
        budget = provider_snapshot(book.root)
    except (Refused, OSError, ValueError):
        budget = None
    return {
        "owner": {"version": owner["version"], "sha256": owner["sha256"]},
        "gate": {"initialized": gate_config is not None,
                 "runs": runs, "attempts": attempts, "evaluations": observed,
                 "accepted_checkpoint_count": sum(x["accepted_checkpoint"] for x in runs),
                 "release_authority": "gate_only",
                 "independent_vm_verified": False},
        "task_execution": planned,
        "calls": call_rows,
        "provider_budget": budget,
        "delivery": {"verified_package_count": len(packages),
                     "packages": packages,
                     "reason": "only registered, byte-verified Gate exports are counted"},
        "capabilities": {
            "S0": "partial", "S1": "partial", "S6a": "partial",
            "S2": "partial", "S3": "partial", "S4": "blocked",
            "S5": "blocked", "S7": "not_verified",
        },
        "restrictions": {
            "build_in_browser": False,
            "resume_in_browser": False,
            "gate_accept_in_browser": False,
            "deploy_in_browser": False,
            "reason": "no_verified_guest_or_workflow_authority_for_browser_execution",
        },
    }


def run_detail(book: ProjectBook, run_id: str) -> dict:
    """Inspectable evidence only, including verified evaluation case summaries."""
    if not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id):
        raise Refused("invalid run id")
    data = inspection(book)
    run = next((r for r in data["gate"]["runs"] if r["id"] == run_id), None)
    if run is None:
        raise Refused("run not found in recent history")
    return {
        "run": run,
        "attempts": [a for a in data["gate"]["attempts"] if a["run_id"] == run_id],
        "evaluations": [e for e in data["gate"]["evaluations"] if e["run_id"] == run_id],
        "tasks": [t for t in data["task_execution"] if t["run_id"] == run_id],
        "actions": data["restrictions"],
    }
