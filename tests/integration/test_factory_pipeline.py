"""Offline factory integration: real Python code and Gate, scripted model and guest boundary.

The FixtureGuest is a TEST DOUBLE. A green result does not establish safe
host isolation, live model capability or permission to ship arbitrary code.
"""
from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from csef_gate.core import Gate, Refused, encoded
from csef_gate.factory import (
    _read_plan, bootstrap_sources, build_plan, create_brief, plan_brief,
)
from csef_gate.project import ProjectBook


ANSWERS = {
    "users": "An individual reviewing a simple example",
    "workflow": "Run the CLI and get a structured answer",
    "success": "Output has a verified numeric value",
    "constraints": "Python standard library and no network",
}


class ScriptedPlanner:
    def __init__(self, *, questions=None):
        self.questions = [] if questions is None else questions
        self.calls = 0

    def call(self, *, prompt, schema, folder, control, role, timeout=180):
        self.calls += 1
        assert role == "factory_planner"
        assert "REQ-001" in prompt
        assert schema["required"] == ["spec_text", "plan_text", "tasks_text", "questions", "tasks"]
        return {
            "spec_text": "REQ-001: A CLI returns a JSON value.",
            "plan_text": "REQ-001: Build a domain module, then its CLI entrypoint.",
            "tasks_text": "TASK-001 domain, TASK-002 CLI; TEST-001 and TEST-002.",
            "questions": self.questions,
            "tasks": [
                {"id": "TASK-001", "title": "domain", "fact_ids": ["REQ-001"],
                 "depends_on": [], "files": ["lib.py"],
                 "deliverable": "A callable get function",
                 "acceptance": "TEST-001 verifies a numeric result",
                 "test_ids": ["TEST-001"]},
                {"id": "TASK-002", "title": "CLI", "fact_ids": ["REQ-001"],
                 "depends_on": ["TASK-001"], "files": ["main.py"],
                 "deliverable": "JSON output CLI",
                 "acceptance": "TEST-002 verifies CLI integration",
                 "test_ids": ["TEST-002"]},
            ],
        }, {"adapter": "scripted-fixture", "model": "scripted", "exit_code": 0,
            "usage": {"input_tokens": 1, "output_tokens": 1}, "cost_usd": None}


class ScriptedCoder:
    def __init__(self, *, wrong_scope=False, fail_on=None):
        self.calls = []
        self.wrong_scope = wrong_scope
        self.fail_on = fail_on

    def propose(self, *, spec, sources, feedback, folder, workspace, control):
        target = spec["editable_files"][0]
        self.calls.append(target)
        if self.fail_on == target:
            raise Refused("simulated coding call outcome unknown")
        if self.wrong_scope:
            target = "protected.py"
        code = ("def get():\n    return 10\n" if target == "lib.py"
                else "import json\nfrom lib import get\nprint(json.dumps({'value': get()}))\n")
        return {"summary": "scripted task proposal", "files": [
            {"path": target, "content": code}]}, {"exit_code": 0, "adapter": "scripted-fixture"}


class FixtureGuest:
    """Runs known test source locally; only for unit/integration tests."""

    def __init__(self, *, verified=True):
        self.verified = verified
        self.runs = 0

    def probe(self, *, snapshot, scratch, control):
        return {"backend": "test-fixture-not-isolation", "verified": self.verified,
                "file_boundary_verified": True, "network_isolation_verified": False}

    def run(self, *, snapshot, scratch, control, entrypoint, args, timeout):
        self.runs += 1
        run = subprocess.run([sys.executable, str(snapshot / entrypoint), *args],
                             cwd=scratch, capture_output=True, text=True, timeout=timeout)
        return {"exit_code": run.returncode, "stdout": run.stdout,
                "stderr": run.stderr, "timed_out": False, "overflow": False,
                "elapsed_s": 0.01}


def oracle(tmp_path):
    spec = {
        "version": 1,
        "objective": "Python CLI emits a JSON object with value 10",
        "source_files": ["lib.py", "main.py"],
        "editable_files": ["lib.py", "main.py"],
        "entrypoint": "main.py",
        "max_attempts": 4, "agent_timeout_s": 20, "case_timeout_s": 5,
        "cases": [
            {"id": "TEST-001", "args": [], "exit_code": 0,
             "stdout_json": {"value": 10}},
            {"id": "TEST-002", "args": [], "exit_code": 0,
             "stdout_json": {"value": 10}},
        ],
    }
    path = tmp_path / "owner-oracle.json"
    path.write_bytes(encoded(spec))
    return path


def prepared(tmp_path, *, questions=None):
    book = create_brief(tmp_path / "book", "Build a tiny Python JSON CLI",
                        answers=ANSWERS)
    planner = ScriptedPlanner(questions=questions)
    response = plan_brief(book, planner)
    assert planner.calls == 1
    return book, response


def test_one_brief_to_spec_kit_graph_real_python_gate_and_zip(tmp_path):
    book, plan = prepared(tmp_path)
    assert plan["status"] == "proposed" and plan["task_count"] == 2
    assert plan["ready"] == ["TASK-001"]
    folder = Path(plan["plan_path"]).parent
    for filename in ("spec.md", "plan.md", "tasks.md"):
        text = (folder / "spec-kit" / filename).read_text(encoding="utf-8")
        assert "REQ-001" in text and "Factory-generated proposal" in text
    graph, bundle = _read_plan(book, Path(plan["plan_path"]))
    assert graph["graph"]["tasks"][1]["depends_on"] == ["TASK-001"]
    assert graph["spec_kit_proposal_id"] == plan["proposal_id"]
    spec = oracle(tmp_path)
    project = tmp_path / "candidate"
    bootstrap_sources(project, spec)
    result = build_plan(book, plan["plan_path"], project, spec,
                        ScriptedCoder(), FixtureGuest(), tmp_path / "product.zip",
                        owner_approved=True)
    assert result["status"] == "delivered" and result["independent_gate_pass"]
    assert result["deployment_approved"] is False
    with zipfile.ZipFile(result["archive"]) as zipfile_:
        names = set(zipfile_.namelist())
        assert names == {"source/lib.py", "source/main.py", "manifest.json", "README.txt"}
        assert "return 10" in zipfile_.read("source/lib.py").decode()
        metadata = json.loads(zipfile_.read("manifest.json"))
        assert metadata["deployment_approved"] is False
        assert metadata["case_ids"] == ["TEST-001", "TEST-002"]
    with book.connection() as con:
        assert con.execute("SELECT count(*) FROM checkpoints").fetchone()[0] == 1
        assert con.execute("SELECT count(*) FROM changes WHERE status='factory_done'").fetchone()[0] == 2
    assert len(Gate(book.root).spec()[0]["cases"]) == 2


def test_reviewed_only_never_creates_delivery_or_checkpoint(tmp_path):
    book, plan = prepared(tmp_path)
    spec = oracle(tmp_path)
    project = tmp_path / "candidate"
    bootstrap_sources(project, spec)
    result = build_plan(book, plan["plan_path"], project, spec,
                        ScriptedCoder(), FixtureGuest(verified=False),
                        tmp_path / "must-not-exist.zip",
                        owner_approved=True, measure_only=True)
    assert result["status"] == "review" and result["cases_passed"] == 2
    assert not (tmp_path / "must-not-exist.zip").exists()
    with book.connection() as con:
        assert con.execute("SELECT count(*) FROM checkpoints").fetchone()[0] == 0


def test_owner_must_approve_before_any_gate_side_effect(tmp_path):
    book, plan = prepared(tmp_path)
    spec = oracle(tmp_path)
    project = tmp_path / "candidate"
    bootstrap_sources(project, spec)
    with pytest.raises(Refused, match="explicitly approve"):
        build_plan(book, plan["plan_path"], project, spec,
                   ScriptedCoder(), FixtureGuest(), tmp_path / "none.zip")
    assert not (book.root / "spec.json").exists()


def test_unanswered_questions_and_stale_owner_version_block_execution(tmp_path):
    book, plan = prepared(tmp_path, questions=["Who can access the data?"])
    spec = oracle(tmp_path)
    project = tmp_path / "candidate"
    bootstrap_sources(project, spec)
    with pytest.raises(Refused, match="unresolved owner questions"):
        build_plan(book, plan["plan_path"], project, spec,
                   ScriptedCoder(), FixtureGuest(), tmp_path / "none.zip",
                   owner_approved=True)
    book.amend(replace_facts={"REQ-001": "Use a different interface"},
               reason="Owner changed accepted goal")
    with pytest.raises(Refused, match="stale"):
        build_plan(book, plan["plan_path"], project, spec,
                   ScriptedCoder(), FixtureGuest(), tmp_path / "none.zip",
                   owner_approved=True)
    assert not (book.root / "spec.json").exists()


def test_agent_cannot_break_task_file_ownership(tmp_path):
    book, plan = prepared(tmp_path)
    spec = oracle(tmp_path)
    project = tmp_path / "candidate"
    bootstrap_sources(project, spec)
    with pytest.raises(Refused, match="outside assigned task"):
        build_plan(book, plan["plan_path"], project, spec,
                   ScriptedCoder(wrong_scope=True), FixtureGuest(),
                   tmp_path / "none.zip", owner_approved=True)
    assert not (tmp_path / "none.zip").exists()
    with book.connection() as con:
        assert con.execute("SELECT count(*) FROM checkpoints").fetchone()[0] == 0


def test_unknown_attempt_cannot_be_blindly_replayed(tmp_path):
    book, plan = prepared(tmp_path)
    spec = oracle(tmp_path)
    project = tmp_path / "candidate"
    bootstrap_sources(project, spec)
    coder = ScriptedCoder(fail_on="main.py")
    with pytest.raises(Refused, match="outcome unknown"):
        build_plan(book, plan["plan_path"], project, spec,
                   coder, FixtureGuest(), tmp_path / "none.zip",
                   owner_approved=True)
    assert coder.calls == ["lib.py", "main.py"]
    with book.connection() as con:
        run_id = con.execute("SELECT id FROM runs").fetchone()[0]
    with pytest.raises(Refused, match="unknown interrupted"):
        build_plan(book, plan["plan_path"], project, spec,
                   coder, FixtureGuest(), tmp_path / "none.zip",
                   owner_approved=True, resume_run_id=run_id)
    assert coder.calls == ["lib.py", "main.py"]
    assert not (tmp_path / "none.zip").exists()


def test_oracle_cases_must_cover_planned_tests_not_model_approval(tmp_path):
    book, plan = prepared(tmp_path)
    spec_path = oracle(tmp_path)
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    spec["cases"].pop()
    spec_path.write_bytes(encoded(spec))
    project = tmp_path / "candidate"
    bootstrap_sources(project, spec_path)
    with pytest.raises(Refused, match="oracle inventory and cases"):
        build_plan(book, plan["plan_path"], project, spec_path,
                   ScriptedCoder(), FixtureGuest(), tmp_path / "none.zip",
                   owner_approved=True)
    assert not (book.root / "spec.json").exists()


def test_existing_workspace_never_overwritten_by_bootstrap(tmp_path):
    spec = oracle(tmp_path)
    project = tmp_path / "candidate"
    project.mkdir()
    (project / "owner-data.txt").write_text("keep me")
    with pytest.raises(Refused, match="existing"):
        bootstrap_sources(project, spec)
    assert (project / "owner-data.txt").read_text() == "keep me"


def test_plan_file_tampering_cannot_erase_open_questions(tmp_path):
    book, plan = prepared(tmp_path, questions=["Which user role can read records?"])
    path = Path(plan["plan_path"])
    original = json.loads(path.read_text(encoding="utf-8"))
    original["questions"] = []
    path.write_bytes(encoded(original))
    spec = oracle(tmp_path)
    project = tmp_path / "candidate"
    bootstrap_sources(project, spec)
    with pytest.raises(Refused, match="factory plan changed"):
        build_plan(book, path, project, spec, ScriptedCoder(),
                   FixtureGuest(), tmp_path / "none.zip", owner_approved=True)
    assert not (book.root / "spec.json").exists()
    assert not (tmp_path / "none.zip").exists()


def test_plan_artifact_edit_invalidates_spec_kit_binding(tmp_path):
    book, plan = prepared(tmp_path)
    bundle = Path(plan["spec_kit_bundle"])
    (bundle / "tasks.md").write_text("changed task claim\n", encoding="utf-8")
    with pytest.raises(Refused, match="Spec Kit bundle differs"):
        _read_plan(book, Path(plan["plan_path"]))
