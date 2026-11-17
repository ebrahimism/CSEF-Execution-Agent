"""Validate a proposed per-project task DAG; never grant execution or Gate authority.

A task graph is a model/Spec Kit *proposal*. The owner revision and all
acceptance criteria remain outside candidate control. No storage or new service.
"""
from __future__ import annotations

import re
from collections import deque

from ..core import Refused, encoded, digest, relative_name


TASK_KEYS = frozenset({
    "id", "title", "fact_ids", "depends_on", "files",
    "deliverable", "acceptance", "test_ids",
})
GRAPH_KEYS = frozenset({"schema_version", "project_version", "project_sha256", "tasks"})
TASK_ID = re.compile(r"TASK-[0-9]{3,5}\Z")
TEST_ID = re.compile(r"TEST-[0-9]{3,5}\Z")
MAX_TASKS = 200


def _text(value, label):
    if not isinstance(value, str) or not value.strip() or len(value) > 2000:
        raise Refused("invalid or empty " + label)


def _unique_strings(value, label, *, nonempty=False, limit=200):
    if not isinstance(value, list) or len(value) > limit or (nonempty and not value):
        raise Refused("invalid " + label)
    if any(not isinstance(x, str) or not x or len(x) > 512 for x in value):
        raise Refused("invalid " + label)
    if len(set(value)) != len(value):
        raise Refused("duplicate " + label)
    return value


def validate_graph(project: dict, proposal: dict) -> dict:
    """Fail closed on stale, incomplete, overlapping or cyclic plans.

    This is a *structural* check, not semantic correctness, approval, or a
    secure execution sandbox. Returns a normalized proposal and ready task IDs.
    """
    if not isinstance(project, dict) or not isinstance(proposal, dict):
        raise Refused("project and task graph must be objects")
    if set(proposal) != GRAPH_KEYS or type(proposal["schema_version"]) is not int or proposal["schema_version"] != 1:
        raise Refused("unsupported task graph contract")
    if (type(project.get("version")) is not int or project["version"] < 1
            or type(proposal["project_version"]) is not int
            or proposal["project_version"] != project["version"]
            or proposal["project_sha256"] != project.get("sha256")):
        raise Refused("stale or foreign owner revision")
    if (not isinstance(project.get("facts"), list)
            or not isinstance(project.get("goal"), str) or not project["goal"].strip()):
        raise Refused("invalid owner project")
    # Recompute the owner revision rather than trusting a model-supplied hash.
    body = {"goal": project["goal"], "answers": project.get("answers"), "facts": project["facts"]}
    if digest(encoded(body)) != project["sha256"]:
        raise Refused("owner revision integrity mismatch")
    facts = project["facts"]
    if any(not isinstance(f, dict) or not isinstance(f.get("id"), str)
           or f.get("kind") not in ("requirement", "constraint", "decision") for f in facts):
        raise Refused("invalid owner facts")
    fact_ids = {f["id"] for f in facts}
    if len(fact_ids) != len(facts):
        raise Refused("duplicate owner fact")
    tasks = proposal["tasks"]
    if not isinstance(tasks, list) or not 1 <= len(tasks) <= MAX_TASKS:
        raise Refused("task graph requires 1 to 200 tasks")
    by_id = {}
    file_owners = {}
    covered = set()
    for task in tasks:
        if not isinstance(task, dict) or set(task) != TASK_KEYS:
            raise Refused("task fields do not match versioned contract")
        tid = task["id"]
        if not isinstance(tid, str) or not TASK_ID.fullmatch(tid) or tid in by_id:
            raise Refused("invalid or duplicate task id")
        by_id[tid] = task
        _text(task["title"], "task title")
        _text(task["deliverable"], "task deliverable")
        _text(task["acceptance"], "task acceptance")
        refs = _unique_strings(task["fact_ids"], "fact references", nonempty=True)
        if not set(refs) <= fact_ids:
            raise Refused("task references unknown owner facts")
        covered.update(refs)
        deps = _unique_strings(task["depends_on"], "dependencies")
        if tid in deps:
            raise Refused("self dependency")
        tests = _unique_strings(task["test_ids"], "acceptance test IDs", nonempty=True)
        if any(not TEST_ID.fullmatch(test) for test in tests):
            raise Refused("invalid acceptance test id")
        paths = _unique_strings(task["files"], "file ownership", nonempty=True)
        for name in paths:
            relative_name(name)
            folded = name.casefold()
            if folded in file_owners:
                raise Refused("file has multiple task owners: " + name)
            file_owners[folded] = tid
    if covered != fact_ids:
        raise Refused("uncovered owner facts: " + ", ".join(sorted(fact_ids - covered)))
    for task in tasks:
        if not set(task["depends_on"]) <= by_id.keys():
            raise Refused("unknown task dependency")
    indegree = {tid: len(task["depends_on"]) for tid, task in by_id.items()}
    followers = {tid: [] for tid in by_id}
    for tid, task in by_id.items():
        for dep in task["depends_on"]:
            followers[dep].append(tid)
    ready = sorted(tid for tid, degree in indegree.items() if degree == 0)
    queue = deque(ready)
    ordered = []
    while queue:
        tid = queue.popleft()
        ordered.append(tid)
        for child in sorted(followers[tid]):
            indegree[child] -= 1
            if indegree[child] == 0:
                queue.append(child)
    if len(ordered) != len(by_id):
        raise Refused("cyclic task dependencies")
    # A model-generated acceptance text or checkbox is never Gate evidence.
    return {"status": "proposed", "release_approved": False,
            "project_version": project["version"], "project_sha256": project["sha256"],
            "task_count": len(by_id), "ready": ready, "order": ordered,
            "covered_fact_ids": sorted(covered), "proposal_sha256": digest(encoded(proposal))}


def ready_tasks(project: dict, proposal: dict, completed: list[str]) -> list[str]:
    """Pure scheduling preview; completed is external state, not proof of PASS."""
    validate_graph(project, proposal)
    done = set(_unique_strings(completed, "completed task IDs"))
    tasks = {task["id"]: task for task in proposal["tasks"]}
    if not done <= tasks.keys():
        raise Refused("unknown completed task")
    # Never infer a completion from a checkbox or from the graph itself.
    return sorted(tid for tid, task in tasks.items()
                  if tid not in done and set(task["depends_on"]) <= done)
