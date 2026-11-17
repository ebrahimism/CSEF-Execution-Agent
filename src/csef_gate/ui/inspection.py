"""Evidence-first local dashboard projection over existing CSEF control records.

This module is read-only, does not change the SQLite schema and never treats a
model, checkbox or raw PASS string as Gate release authority. All paths and
sensitive request payloads remain server-side.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

from ..core import Gate, Refused, digest, encoded, parse_json, plain, read_json
from ..engineering.task_graph import validate_graph
from ..persistence.sqlite import DATABASE
from ..providers.usage import snapshot as provider_snapshot

MAX_ENTRIES = 80


def _safe_error(error) -> str:
    if error is None:
        return ""
    # Do not echo potentially sensitive paths, stderr, or model output.
    return type(error).__name__ + ": integrity check failed"


def _report(book, row, expected_spec_hash):
    """Read only a bounded, hashed report from the controller-owned run tree."""
    file = Path(row["report"]).absolute()
    plain(file)
    try:
        file.relative_to(book.root / "runs")
        if not file.is_file() or file.stat().st_size > 512_000:
            raise Refused("report missing or oversized")
        raw = file.read_bytes()
        if not row["report_hash"] or digest(raw) != row["report_hash"]:
            raise Refused("report digest mismatch")
        report = parse_json(raw.decode("utf-8"))
        if (not isinstance(report, dict)
                or report.get("evaluation_id") != row["id"]
                or report.get("run_id") != row["run_id"]
                or report.get("status") != row["status"]
                or report.get("spec_sha256") != row["spec_hash"]
                or row["spec_hash"] != expected_spec_hash
                or report.get("source_sha256") != row["source_hash"]
                or not isinstance(report.get("cases"), list)
                or len(report["cases"]) > 100):
            raise Refused("inconsistent report metadata")
        cases = []
        for c in report["cases"]:
            if not isinstance(c, dict) or not isinstance(c.get("id"), str):
                raise Refused("malformed test case")
            cases.append({
                "id": c["id"][:65],
                "passed": c.get("passed") is True,
                "exit_code": c.get("exit_code"),
                "timed_out": c.get("timed_out") is True,
                "overflow": c.get("overflow") is True,
            })
        return {
            "integrity": "valid",
            "status": report["status"],
            "measurement_only": report.get("measurement_only") is True,
            "boundary_verified": isinstance(report.get("boundary"), dict)
                                 and report["boundary"].get("verified") is True,
            "cases": cases,
            "passed": sum(int(c["passed"]) for c in cases),
            "total": len(cases),
            "finished_at": report.get("finished_at"),
            "error_present": report.get("error") is not None,
        }
    except (Refused, OSError, UnicodeError, TypeError, ValueError, KeyError):
        return {"integrity": "invalid", "status": "blocked", "cases": [],
                "passed": 0, "total": None, "measurement_only": None,
                "boundary_verified": False, "error_present": True}


def _gate_state(book, con):
    config = con.execute("SELECT spec_hash,baseline_hash FROM config LIMIT 1").fetchone()
    if config is None:
        return {"state": "not_configured", "tests": [],
                "runs": [], "checkpoints": [], "evaluations": [], "integrity": "not_applicable"}
    try:
        spec, spec_sha = Gate(book.root).spec()
        if config["spec_hash"] != spec_sha:
            raise Refused("oracle digest mismatched")
        integrity = "valid"
        tests = [{"id": test["id"], "status": "frozen"}
                 for test in spec["cases"]]
        max_attempts = spec["max_attempts"]
    except (Refused, OSError, ValueError, TypeError, KeyError):
        integrity = "invalid"
        tests = []
        max_attempts = None
        spec_sha = None

    run_rows = [dict(row) for row in con.execute(
        "SELECT id,status,attempts,created FROM runs ORDER BY created DESC LIMIT ?", (MAX_ENTRIES,))]
    attempted = [dict(row) for row in con.execute(
        "SELECT id,run_id,status,created FROM attempts ORDER BY created DESC LIMIT ?", (MAX_ENTRIES,))]
    evaluated = [dict(row) for row in con.execute(
        "SELECT id,run_id,status,report,report_hash,source_hash,spec_hash,created "
        "FROM evaluations ORDER BY created DESC LIMIT ?", (MAX_ENTRIES,))]
    checkpoints = [dict(row) for row in con.execute(
        "SELECT id,run_id,evaluation_id,source_hash,spec_hash,report_hash,created "
        "FROM checkpoints ORDER BY created DESC LIMIT ?", (MAX_ENTRIES,))]
    gate = Gate(book.root)
    evals = []
    by_eval = {}
    for row in evaluated:
        report = _report(book, row, spec_sha) if integrity == "valid" else {
            "integrity": "invalid", "status": "blocked", "cases": [],
            "passed": 0, "total": None, "boundary_verified": False,
            "measurement_only": None, "error_present": True}
        entry = {"id": row["id"], "run_id": row["run_id"],
                 "recorded_status": row["status"], "created": row["created"], **report}
        evals.append(entry)
        by_eval[row["id"]] = entry
    completed = []
    for cp in checkpoints:
        ev = by_eval.get(cp["evaluation_id"])
        # Only an intact, matching, non-measurement Gate report can be presented
        # as an accepted checkpoint. Never trust status strings alone.
        proven = (
            integrity == "valid" and ev is not None and ev["integrity"] == "valid"
            and ev["status"] == "pass" and ev["measurement_only"] is False
            and ev["boundary_verified"] is True and ev["total"] == len(tests)
            and ev["passed"] == len(tests) and cp["spec_hash"] == spec_sha
            and cp["report_hash"] == next((e["report_hash"] for e in evaluated
                                            if e["id"] == cp["evaluation_id"]), None)
            and cp["source_hash"] == next((e["source_hash"] for e in evaluated
                                            if e["id"] == cp["evaluation_id"]), None)
            and any(run["id"] == cp["run_id"] and run["status"] == "accepted"
                    for run in run_rows)
        )
        if proven:
            try:
                # Check actual pinned snapshot/candidate bytes, not just DB rows.
                from ..core import manifest
                snap = con.execute("SELECT snapshot FROM checkpoints WHERE id=?",
                                   (cp["id"],)).fetchone()["snapshot"]
                proven = (manifest(Path(snap), spec["source_files"])[0] == cp["source_hash"]
                          and manifest(gate.candidate(cp["run_id"]), spec["source_files"])[0]
                              == cp["source_hash"])
            except (Refused, OSError, TypeError, KeyError):
                proven = False
        completed.append({
            "id": cp["id"], "run_id": cp["run_id"], "created": cp["created"],
            "integrity": "valid" if proven else "unverified",
            "export_ready": bool(proven),
        })
    attempted_by_run = Counter(a["run_id"] for a in attempted)
    outcome_by_run = {}
    for run in run_rows:
        related = [a for a in attempted if a["run_id"] == run["id"]]
        evaluations = [e for e in evals if e["run_id"] == run["id"]]
        unknown = any(a["status"] in ("started", "failed_or_unknown") for a in related)
        interrupted = run["status"] in ("prepared", "verifying") or unknown
        outcome_by_run[run["id"]] = {
            **run,
            "attempt_records": attempted_by_run[run["id"]],
            "unknown_attempt": unknown,
            "recovery": "manual_reconciliation" if unknown or run["status"] == "verifying"
                        else "review_preconditions" if run["status"] == "prepared"
                        else "not_needed" if run["status"] == "accepted"
                        else "conditional",
            "latest_evaluation": evaluations[0]["id"] if evaluations else None,
            "checkpoint": any(c["run_id"] == run["id"] and c["integrity"] == "valid"
                              for c in completed),
            "interrupted": interrupted,
        }
    return {
        "state": "configured" if integrity == "valid" else "blocked",
        "integrity": integrity,
        "max_attempts": max_attempts,
        "tests": tests,
        "runs": [outcome_by_run[r["id"]] for r in run_rows],
        "attempts": attempted,
        "evaluations": evals,
        "checkpoints": completed,
        "accepted_count": sum(c["integrity"] == "valid" for c in completed),
    }


def _events(book, con):
    results = []
    for row in con.execute(
        "SELECT id,proposal,status,created FROM changes ORDER BY id DESC LIMIT ?", (MAX_ENTRIES,)):
        try:
            item = parse_json(row["proposal"])
            kind = item.get("type") if isinstance(item, dict) else "unknown"
            if not isinstance(kind, str) or len(kind) > 65:
                kind = "unknown"
        except (Refused, ValueError, TypeError):
            kind = "invalid"
        results.append({"id": row["id"], "type": kind, "status": row["status"],
                        "created": row["created"]})
    return results


def _task_progress(book, plan, events, gate):
    """Coding intent is never represented as an independently accepted task."""
    if not plan or not isinstance(plan, dict) or plan.get("state") not in ("proposed", "needs_owner"):
        return []
    task_ids = {task["id"] for task in plan.get("tasks", [])}
    candidates = {run["id"] for run in gate.get("runs", [])}
    with book.connection() as con:
        records = con.execute(
            "SELECT proposal,status FROM changes WHERE status IN ('factory_running','factory_done') "
            "ORDER BY id DESC LIMIT 300").fetchall()
    latest = {}
    for row in records:
        try:
            entry = parse_json(row["proposal"])
        except (Refused, ValueError, TypeError):
            continue
        if (not isinstance(entry, dict) or entry.get("type") != "factory_task"
                or entry.get("run_id") not in candidates
                or entry.get("task_id") not in task_ids):
            continue
        latest.setdefault(entry["task_id"], row["status"])
    return [{"id": task["id"],
             "status": "coded_unverified" if latest.get(task["id"]) == "factory_done"
                       else "unknown" if latest.get(task["id"]) == "factory_running"
                       else "proposed",
             "independently_accepted": False}
            for task in plan["tasks"]]


def _journey(project, plan, gate, requests):
    """Evidence-derived project journey; not the historical CSEF backlog."""
    generated = bool(plan and plan.get("state") in ("proposed", "needs_owner"))
    runs = gate["runs"]
    evaluated = gate["evaluations"]
    accepted = gate.get("accepted_count", 0)
    return [
        {"id": "S0", "state": "recorded", "evidence": "owner_revision"},
        {"id": "S1", "state": "proposed" if generated else "not_started",
         "evidence": "validated_task_graph" if generated else None},
        {"id": "S6a", "state": "available", "evidence": "local_dashboard"},
        {"id": "S2", "state": "configured_only" if requests["used_calls"] else "not_verified",
         "evidence": "request_intents_only" if requests["used_calls"] else None},
        {"id": "S3", "state": "attempted" if runs else "not_started",
         "evidence": "gate_run_records" if runs else None},
        {"id": "S4", "state": "verified" if accepted else "reviewed" if evaluated else "not_verified",
         "evidence": "gate_checkpoint" if accepted else "evaluation_records" if evaluated else None},
        {"id": "S5", "state": "checkpoint_only" if accepted else "blocked",
         "evidence": "gate_checkpoint" if accepted else None},
        {"id": "S7", "state": "not_verified", "evidence": None},
    ]


def inspect(book, plan=None):
    """Read existing journal, attempts, frozen tests, evidence and request budgets."""
    owner = book.current()
    with book.connection() as con:
        con.execute("BEGIN")
        versions = [
            {"version": row["version"], "sha256": row["sha256"],
             "reason": row["reason"], "created": row["created"]}
            for row in con.execute("SELECT version,sha256,reason,created FROM revisions "
                                   "ORDER BY version DESC LIMIT ?", (MAX_ENTRIES,))
        ]
        stages = [dict(r) for r in con.execute(
            "SELECT position,name,status,version FROM stages ORDER BY position")]
        calls = [
            {"id": row["id"], "role": row["role"], "status": row["status"],
             "has_receipt": bool(row["receipt"])}
            for row in con.execute("SELECT id,role,status,receipt FROM calls "
                                   "ORDER BY id DESC LIMIT ?", (MAX_ENTRIES,))
        ]
        events = _events(book, con)
        gate = _gate_state(book, con)
    budget = provider_snapshot(book.root)
    progress = _task_progress(book, plan, events, gate)
    return {
        "schema_version": 1,
        "owner_version": owner["version"],
        "owner_sha256": owner["sha256"],
        "revisions": versions, "stages": stages, "model_calls": calls,
        "events": events,
        "budget": budget,
        "gate": gate,
        "task_progress": progress,
        "journey": _journey(owner, plan, gate, budget),
        "capabilities": {
            "planning": True, "owner_amendment": True,
            "gate_read_only": True, "run_execution": False,
            "unsafe_host_execution": False, "automatic_resume": False,
            "delivery_export": False, "live_api_verified": False,
        },
        "release_approved": False,
    }
