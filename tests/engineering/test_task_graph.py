"""Structural planning contract; no network, agent, Gate or sandbox required."""
from copy import deepcopy

import pytest

from csef_gate.core import Refused, digest, encoded
from csef_gate.engineering.task_graph import ready_tasks, validate_graph


@pytest.fixture
def example():
    body = {
        "goal": "Build a small inventory web app",
        "answers": {},
        "facts": [
            {"id": "REQ-101", "kind": "requirement", "text": "Track items"},
            {"id": "REQ-102", "kind": "requirement", "text": "Show stock in browser"},
            {"id": "ADR-001", "kind": "decision", "text": "Use a local database"},
        ],
    }
    project = {"version": 1, "sha256": digest(encoded(body)), **body}
    graph = {"schema_version": 1, "project_version": 1,
             "project_sha256": project["sha256"], "tasks": [
        {"id": "TASK-001", "title": "Persistence", "fact_ids": ["REQ-101", "ADR-001"],
         "depends_on": [], "files": ["app/db.py"], "deliverable": "Persist items",
         "acceptance": "Can create and read item", "test_ids": ["TEST-001"]},
        {"id": "TASK-002", "title": "UI", "fact_ids": ["REQ-102"],
         "depends_on": ["TASK-001"], "files": ["app/ui.py"],
         "deliverable": "Browser view", "acceptance": "Stock appears",
         "test_ids": ["TEST-002"]},
    ]}
    return project, graph


def test_valid_graph_has_coverage_and_order_but_no_authority(example):
    project, graph = example
    result = validate_graph(project, graph)
    assert result["ready"] == ["TASK-001"]
    assert result["order"] == ["TASK-001", "TASK-002"]
    assert result["covered_fact_ids"] == ["ADR-001", "REQ-101", "REQ-102"]
    assert result["status"] == "proposed" and result["release_approved"] is False
    assert ready_tasks(project, graph, ["TASK-001"]) == ["TASK-002"]
    assert ready_tasks(project, graph, ["TASK-001", "TASK-002"]) == []


@pytest.mark.parametrize("mutation,expected", [
    (lambda g: g["tasks"][1].update(fact_ids=["REQ-101"]), "uncovered"),
    (lambda g: g["tasks"][1].update(fact_ids=["REQ-999"]), "unknown owner"),
    (lambda g: g["tasks"][1].update(depends_on=["TASK-999"]), "unknown task"),
    (lambda g: g["tasks"][0].update(depends_on=["TASK-002"]), "cyclic"),
    (lambda g: g["tasks"][1].update(files=["APP/DB.py"]), "multiple task owners"),
    (lambda g: g["tasks"][1].update(files=["../escape.py"]), "noncanonical"),
    (lambda g: g["tasks"][1].update(test_ids=[]), "acceptance test"),
    (lambda g: g["tasks"][1].update(acceptance=""), "task acceptance"),
    (lambda g: g["tasks"][1].update(id="TASK-001"), "duplicate task"),
    (lambda g: g.update(schema_version=True), "contract"),
    (lambda g: g.update(project_version=2), "stale"),
    (lambda g: g.update(release_approved=True), "contract"),
])
def test_bad_plans_are_refused(example, mutation, expected):
    project, graph = deepcopy(example)
    mutation(graph)
    with pytest.raises(Refused, match=expected):
        validate_graph(project, graph)


def test_owner_revision_mutation_blocks_old_plan(example):
    project, graph = deepcopy(example)
    project["facts"][0]["text"] = "Changed by another party"
    with pytest.raises(Refused, match="integrity"):
        validate_graph(project, graph)
    project["sha256"] = digest(encoded({k: project[k] for k in ("goal", "answers", "facts")}))
    with pytest.raises(Refused, match="stale"):
        validate_graph(project, graph)


def test_empty_or_oversized_plan_and_unknown_completion_refused(example):
    project, graph = deepcopy(example)
    with pytest.raises(Refused, match="unknown completed"):
        ready_tasks(project, graph, ["TASK-999"])
    graph["tasks"] = []
    with pytest.raises(Refused, match="1 to 200"):
        validate_graph(project, graph)
    graph["tasks"] = [example[1]["tasks"][0]] * 201
    with pytest.raises(Refused, match="1 to 200"):
        validate_graph(project, graph)


def test_duplicate_test_ids_and_unowned_file_refused(example):
    project, graph = deepcopy(example)
    graph["tasks"][0]["test_ids"] = ["TEST-001", "TEST-001"]
    with pytest.raises(Refused, match="duplicate"):
        validate_graph(project, graph)
    graph = deepcopy(example[1])
    graph["tasks"][0]["files"] = ["app/.secret"]
    with pytest.raises(Refused, match="reserved"):
        validate_graph(project, graph)
