"""S0–S7 local UI evidence: no model calls or arbitrary-code execution.

A fake guest is used ONLY to exercise the Gate persistence and tamper
verification paths. It is not evidence of real VM isolation.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from csef_gate.core import Gate, Refused, encoded
from csef_gate.project import ProjectBook
from csef_gate.ui.inspection import inspection, run_detail
from csef_gate.ui.server import DashboardService
from test_dashboard import create, http, running_dashboard


def make_project(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    book = ProjectBook.create(workspace / "sample", "An example",
                              answers={"users": "test", "workflow": "run",
                                       "success": "value 10", "constraints": "offline"},
                              facts=[{"id": "REQ-001", "kind": "requirement",
                                      "text": "An example"}])
    return book


def attach_gate(book, tmp_path):
    source = tmp_path / "candidate"
    source.mkdir()
    (source / "app.py").write_text("print(10)\n", encoding="utf-8")
    oracle = tmp_path / "oracle.json"
    oracle.write_bytes(encoded({
        "version": 1, "objective": "emit 10",
        "source_files": ["app.py"], "editable_files": ["app.py"],
        "entrypoint": "app.py", "max_attempts": 2, "agent_timeout_s": 20,
        "case_timeout_s": 5, "cases": [
            {"id": "OUTPUT", "args": [], "exit_code": 0, "stdout_json": 10}]}))
    return Gate.initialize(book.root, source, oracle, attach=True)


class FakeGuest:
    def probe(self, *, snapshot, scratch, control):
        return {"backend": "unit-test-not-real-isolation", "verified": True,
                "file_boundary_verified": True, "network_isolation_verified": True}

    def run(self, *, snapshot, scratch, control, entrypoint, args, timeout):
        return {"exit_code": 0, "stdout": "10", "stderr": "",
                "timed_out": False, "overflow": False, "elapsed_s": 0.01}


def test_empty_project_reports_truth_not_fiction(tmp_path):
    book = make_project(tmp_path)
    result = inspection(book)
    assert result["owner"]["version"] == 1
    assert result["gate"]["initialized"] is False
    assert result["gate"]["runs"] == []
    assert result["gate"]["accepted_checkpoint_count"] == 0
    assert result["delivery"]["verified_package_count"] is None
    assert result["capabilities"]["S4"] == "blocked"
    assert result["capabilities"]["S7"] == "not_verified"
    assert all(v is False for k, v in result["restrictions"].items()
               if k.endswith("_in_browser"))
    assert result["provider_budget"]["used_calls"] == 0


def test_gate_run_and_evaluation_visible_without_exposing_source(tmp_path):
    book = make_project(tmp_path)
    gate = attach_gate(book, tmp_path)
    run = gate.prepare()
    initial = run_detail(book, run)
    assert initial["run"]["accepted_checkpoint"] is False
    assert initial["run"]["can_resume_automatically"] is False
    assert initial["evaluations"] == []
    report = gate.evaluate(run, FakeGuest())
    assert report["status"] == "pass"
    data = inspection(book)
    assert data["gate"]["evaluations"][0]["report_integrity"] is True
    assert data["gate"]["evaluations"][0]["verified_boundary"] is True
    assert data["gate"]["evaluations"][0]["cases"] == [
        {"id": "OUTPUT", "passed": True}]
    assert data["gate"]["runs"][0]["accepted_checkpoint"] is False
    gate.accept(run)
    accepted = run_detail(book, run)
    assert accepted["run"]["accepted_checkpoint"] is True
    assert accepted["run"]["delivery_package"] == "not_tracked"
    assert accepted["actions"]["deploy_in_browser"] is False
    assert "print(10)" not in json.dumps(accepted)


def test_tampered_report_can_never_show_verified_checkpoint(tmp_path):
    book = make_project(tmp_path)
    gate = attach_gate(book, tmp_path)
    run = gate.prepare()
    gate.evaluate(run, FakeGuest())
    gate.accept(run)
    with gate.connect() as con:
        report_path = Path(con.execute(
            "SELECT report FROM evaluations WHERE run_id=?", (run,)).fetchone()[0])
    report_path.write_text('{"status":"pass","fiction":true}', encoding="utf-8")
    data = inspection(book)
    assert data["gate"]["evaluations"][0]["report_integrity"] is False
    assert data["gate"]["runs"][0]["accepted_checkpoint"] is False
    assert data["gate"]["accepted_checkpoint_count"] == 0


def test_recent_run_detail_rejects_foreign_and_malformed_ids(tmp_path):
    book = make_project(tmp_path)
    attach_gate(book, tmp_path)
    with pytest.raises(Refused, match="invalid run"):
        run_detail(book, "../../other")
    with pytest.raises(Refused, match="not found"):
        run_detail(book, "run-" + "f" * 32)


def test_http_monitor_has_original_security_headers_and_no_new_mutation(tmp_path):
    with running_dashboard(tmp_path) as (port, planner, workspace):
        status, result, _ = create(port, "demo", "Build a demo")
        assert status == 201
        status, evidence, headers = http(port, "/api/projects/demo/inspection")
        assert status == 200
        assert evidence["gate"]["runs"] == []
        assert evidence["delivery"]["verified_package_count"] is None
        assert evidence["restrictions"]["gate_accept_in_browser"] is False
        assert headers["Cache-Control"] == "no-store"
        assert "frame-ancestors 'none'" in headers["Content-Security-Policy"]
        for route in ("/api/projects/demo/inspection", "/api/projects/demo/runs/run-" + "a" * 32):
            status, payload, _ = http(port, route, method="POST", payload={})
            assert status == 404
        assert planner.calls == 0


def test_http_inspection_rejects_path_escape_and_foreign_run(tmp_path):
    with running_dashboard(tmp_path) as (port, planner, workspace):
        assert create(port, "demo")[0] == 201
        code, data, _ = http(port, "/api/projects/demo/runs/run-" + "b" * 32)
        assert code == 400
        assert data["error"]
        code, data, _ = http(port, "/api/projects/%2e%2e/inspection")
        assert code == 400
        code, data, _ = http(port, "/api/projects/demo/inspection", host="malicious.example")
        assert code == 403
        assert planner.calls == 0


def test_frontend_operational_sections_are_bilingual_and_safe(tmp_path):
    with running_dashboard(tmp_path) as (port, planner, workspace):
        _, html, _ = http(port, "/")
        _, js, _ = http(port, "/app.js")
        _, css, _ = http(port, "/app.css")
        for section in ("execution-center", "verification-center", "delivery-center",
                        "run-list", "evaluation-list", "recovery-list"):
            assert 'id="' + section + '"' in html
        for term in ('executionCenter:"', 'deliveryCenter:"', 'verificationCenter:"',
                     'function renderOperations()', '"/inspection"', "accepted_checkpoint"):
            assert term in js
        assert ".innerHTML" not in js
        assert "ops-panel" in css and "@media(max-width:620px)" in css


def test_project_list_still_uses_projectbook_not_another_db(tmp_path):
    book = make_project(tmp_path)
    service = DashboardService(book.root.parent)
    data = service.project_inspection("sample")
    assert data["owner"]["sha256"] == book.current()["sha256"]
    assert service.projects()[0]["slug"] == "sample"
    assert not (book.root.parent / "ui.sqlite3").exists()
