"""S1: plan is dependency-sound, owner-bound, retry-safe and non-authoritative."""
import copy
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from csef_gate.__main__ import main
from csef_gate.core import Refused, encoded
from csef_gate.engineering.task_graph import (
    TASK_SCHEMA, generate_graph, latest_graph, propose_graph, validate_graph,
)
from csef_gate.integrations.spec_kit import TEMPLATES, export_bundle, import_proposal
from csef_gate.project import ProjectBook


@pytest.fixture
def book(tmp_path):
    return ProjectBook.create(
        tmp_path / "book", "Build an inventory/order service with clean delivery",
        answers={
            "users": "Store owner and staff",
            "workflow": "Staff places order; stock decreases",
            "success": "Working service with acceptance checks",
            "constraints": "No paid infrastructure or external database",
        },
        facts=[
            {"id": "REQ-001", "kind": "requirement",
             "text": "Manage stock and orders without losing inventory"},
            {"id": "CON-001", "kind": "constraint",
             "text": "Use local SQLite and provide an install guide"},
        ],
    )


def plan():
    return {"tasks": [
        {"id": "SPEC", "title": "Document workflow and schema",
         "kind": "document", "fact_ids": ["GOAL", "REQ-001", "CON-001"],
         "depends_on": [], "scope": "Document approved order workflow and storage contract",
         "inputs": ["Owner-approved workflow"], "outputs": ["Schema document"],
         "acceptance": ["Schema and order behavior reflect accepted facts"],
         "files": ["docs/design.md"]},
        {"id": "CODE", "title": "Implement SQLite order logic",
         "kind": "code", "fact_ids": ["GOAL", "REQ-001", "CON-001"],
         "depends_on": ["SPEC"], "scope": "Add bounded implementation of the order flow",
         "inputs": ["Approved schema document"], "outputs": ["Order service module"],
         "acceptance": ["Inventory cannot become negative on valid workflow"],
         "files": ["src/orders.py"]},
        {"id": "INTEG", "title": "Run end to end integration tests",
         "kind": "integration", "fact_ids": ["GOAL", "REQ-001", "CON-001"],
         "depends_on": ["CODE"], "scope": "Verify order save and stock update together",
         "inputs": ["Order service module"], "outputs": ["Integration test results"],
         "acceptance": ["Two consecutive orders persist correctly in clean database"],
         "files": ["tests/test_orders.py"]},
        {"id": "SHIP", "title": "Package a reproducible deliverable",
         "kind": "delivery", "fact_ids": ["GOAL", "REQ-001", "CON-001"],
         "depends_on": ["INTEG"], "scope": "Clean install and recovery instructions",
         "inputs": ["Verified integration results"], "outputs": ["Runnable release bundle"],
         "acceptance": ["Program runs after fresh install and recovery test"],
         "files": ["README.md"]},
    ]}


def test_valid_graph_does_not_claim_completion(book):
    data = plan()
    assert validate_graph(book.current(), data) == data
    before = book.status()
    out = propose_graph(book, data, expected_version=1)
    assert out["status"] == "proposed" and out["release_approved"] is False
    assert out["task_count"] == 4 and out["owner_version"] == 1
    after = book.status()
    assert after["project"] == before["project"]
    assert after["stages"] == before["stages"]
    with book.connection() as con:
        assert con.execute("SELECT count(*) FROM checkpoints").fetchone()[0] == 0
        row = con.execute("SELECT proposal,status FROM changes WHERE id=?", (out["proposal_id"],)).fetchone()
    stored = json.loads(row["proposal"])
    assert row["status"] == "proposed"
    assert stored["type"] == "software_task_graph"
    assert stored["owner_version"] == 1
    assert stored["owner_sha256"] == book.current()["sha256"]
    assert stored["draft"] == data
    view = latest_graph(book)
    assert view["status"] == "proposed" and view["draft"] == data


@pytest.mark.parametrize("corruption,message", [
    ("cycle", "cyclic"),
    ("unknown_dep", "unknown dependency"),
    ("missing_fact", "omits"),
    ("extra_fact", "unknown or unapproved"),
    ("no_code_file", "scoped"),
    ("bad_path", "file path"),
    ("skip_integrate", "integration criteria"),
    ("not_deliverable", "final delivery"),
    ("weak_requirement", "executable or integration"),
    ("unknown_key", "versioned JSON"),
])
def test_corrupt_plans_rejected(book, corruption, message):
    value = plan()
    tasks = value["tasks"]
    if corruption == "cycle":
        tasks[0]["depends_on"] = ["SHIP"]
    elif corruption == "unknown_dep":
        tasks[2]["depends_on"] = ["MISSING"]
    elif corruption == "missing_fact":
        for task in tasks:
            task["fact_ids"] = [x for x in task["fact_ids"] if x != "CON-001"]
    elif corruption == "extra_fact":
        tasks[0]["fact_ids"].append("REQ-999")
    elif corruption == "no_code_file":
        tasks[1]["files"] = []
    elif corruption == "bad_path":
        tasks[1]["files"] = ["../secret.py"]
    elif corruption == "skip_integrate":
        tasks[2]["kind"] = "document"
    elif corruption == "not_deliverable":
        tasks[3]["depends_on"] = []
    elif corruption == "weak_requirement":
        for task in tasks[1:]:
            task["fact_ids"] = ["GOAL", "CON-001"]
    elif corruption == "unknown_key":
        value["release_approved"] = True
    before = book.status()
    with pytest.raises(Refused, match=message):
        propose_graph(book, value)
    assert book.status() == before


def test_shared_files_block_independent_writers(book):
    value = plan()
    original = value["tasks"]
    second_code = copy.deepcopy(original[1])
    second_code.update(id="CODE2", title="Implement reporting module",
                       depends_on=["SPEC"], files=["src/orders.py"])
    original.insert(2, second_code)
    original[3]["depends_on"] = ["CODE", "CODE2"]
    with pytest.raises(Refused, match="share a writable file"):
        validate_graph(book.current(), value)
    second_code["files"] = ["src/report.py"]
    assert validate_graph(book.current(), value) == value


def test_stale_plan_does_not_survive_owner_change(book):
    first = propose_graph(book, plan())
    book.amend(replace_facts={"REQ-001": "New accepted order requirement"}, reason="Owner changed the requirement")
    view = latest_graph(book)
    assert view["status"] == "stale"
    assert view["draft"] is None and view["release_approved"] is False
    with pytest.raises(Refused, match="stale"):
        propose_graph(book, plan(), expected_version=1)
    updated = propose_graph(book, plan(), expected_version=2)
    assert updated["owner_version"] == 2 and updated["proposal_id"] != first["proposal_id"]


def test_duplicate_proposals_after_restart_do_not_add_rows(book):
    first = propose_graph(book, plan())
    repeated = propose_graph(ProjectBook(book.root), plan())
    assert repeated["replayed"] is True and repeated["proposal_id"] == first["proposal_id"]
    with ThreadPoolExecutor(max_workers=3) as group:
        repeated = list(group.map(lambda _: propose_graph(ProjectBook(book.root), plan()), range(3)))
    assert len({x["proposal_id"] for x in repeated}) == 1
    with book.connection() as con:
        assert con.execute("SELECT count(*) FROM changes WHERE status='proposed'").fetchone()[0] == 1


class StubModel:
    def __init__(self, result, mutate=None):
        self.result = result
        self.mutate = mutate
        self.prompts = []
    def call(self, **kwargs):
        self.prompts.append(kwargs)
        if self.mutate:
            self.mutate()
        return self.result, {"exit_code": 0, "adapter": "offline-test", "usage": {"input_tokens": 9}}


def test_planner_reuses_spec_kit_and_budget_with_no_codex(book, tmp_path, monkeypatch):
    import shutil
    monkeypatch.setattr(shutil, "which", lambda _: None)
    templates = {document: "Template " + document
                 for document in TEMPLATES}
    bundle = tmp_path / "spec-kit"
    export_bundle(book, bundle, templates)
    imported = import_proposal(book, bundle)
    assert imported["status"] == "proposed"
    model = StubModel(plan())
    result = generate_graph(book, model)
    assert result["status"] == "proposed"
    assert result["release_approved"] is False
    assert len(model.prompts) == 1
    prompt = model.prompts[0]["prompt"]
    assert "spec_kit_documents_untrusted" in prompt
    assert "Template tasks.md" in prompt
    assert "REQ-001" in prompt and "CON-001" in prompt
    assert model.prompts[0]["schema"] == TASK_SCHEMA
    with book.connection() as con:
        row = con.execute("SELECT status FROM calls WHERE id=?", (result["model_call_id"],)).fetchone()
        assert row["status"] == "completed"
        assert con.execute("SELECT count(*) FROM checkpoints").fetchone()[0] == 0


def test_model_response_after_owner_revision_is_stale(book):
    model = StubModel(plan(), mutate=lambda: book.amend(
        replace_facts={"REQ-001": "New requirement during remote model call"},
        reason="Concurrent owner instruction"))
    with pytest.raises(Refused, match="stale"):
        generate_graph(book, model)
    with book.connection() as con:
        assert con.execute("SELECT count(*) FROM changes WHERE status='proposed'").fetchone()[0] == 0
        assert con.execute("SELECT status FROM calls").fetchone()[0] == "failed_or_unknown"


def test_cli_offline_plan_and_status_use_same_book(book, tmp_path, capsys):
    filename = tmp_path / "graph.json"
    filename.write_bytes(encoded(plan()))
    args = ["project", "plan", "--root", str(book.root),
            "--proposal", str(filename), "--version", "1"]
    assert main(args) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "proposed"
    assert main(["project", "plan-status", "--root", str(book.root)]) == 0
    current = json.loads(capsys.readouterr().out)
    assert current["task_count"] == 4 and current["release_approved"] is False
    assert main(["project", "plan", "--root", str(book.root)]) == 2
    error = capsys.readouterr().err
    assert "explicit --provider" in error
