"""S6a: bilingual local dashboard integration and security regression.

No paid API calls, no browser install, no candidate-code execution.
"""
from __future__ import annotations

import json
import threading
from contextlib import contextmanager
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from csef_gate.core import Refused
from csef_gate.ui.server import DashboardService, make_handler


class FixturePlanner:
    def __init__(self):
        self.calls = 0

    def call(self, *, prompt, schema, folder, control, role, timeout=180):
        self.calls += 1
        assert "REQ-001" in prompt
        assert role == "factory_planner"
        assert schema["properties"]["tasks"]["maxItems"] == 200
        return {
            "spec_text": "REQ-001: Build a local inventory tool.",
            "plan_text": "REQ-001: Create storage, then the CLI.",
            "tasks_text": "TASK-001 storage -> TASK-002 CLI.",
            "questions": [],
            "tasks": [
                {"id": "TASK-001", "title": "Storage", "fact_ids": ["REQ-001"],
                 "depends_on": [], "files": ["storage.py"],
                 "deliverable": "Data persistence", "acceptance": "Test data writes",
                 "test_ids": ["TEST-001"]},
                {"id": "TASK-002", "title": "CLI", "fact_ids": ["REQ-001"],
                 "depends_on": ["TASK-001"], "files": ["cli.py"],
                 "deliverable": "CLI output", "acceptance": "Test end-to-end output",
                 "test_ids": ["TEST-002"]},
            ],
        }, {"adapter": "fixture", "model": "fixture", "exit_code": 0,
            "usage": {"input_tokens": 1, "output_tokens": 1}, "cost_usd": None}


@contextmanager
def running_dashboard(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    planner = FixturePlanner()
    service = DashboardService(workspace, planner=lambda provider, model: planner)
    handler = make_handler(service, "fixture-token-opaque")
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_port, planner, workspace
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=4)


def http(port, path, *, method="GET", payload=None, csrf=True, origin=True,
         host=None, content_type="application/json"):
    url = "http://127.0.0.1:" + str(port) + path
    headers = {"Host": host or "127.0.0.1:" + str(port)}
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    if method != "GET":
        headers["Content-Type"] = content_type
        if origin:
            headers["Origin"] = "http://127.0.0.1:" + str(port)
        if csrf:
            headers["X-CSEF-CSRF"] = "fixture-token-opaque"
    request = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=8) as response:
            raw = response.read()
            ctype = response.headers.get("Content-Type", "")
            if "application/json" in ctype:
                return response.status, json.loads(raw), response.headers
            return response.status, raw.decode("utf-8"), response.headers
    except HTTPError as error:
        return error.code, json.loads(error.read()), error.headers


def create(port, slug="inventory", brief="A small local inventory program"):
    return http(port, "/api/projects", method="POST",
                payload={"slug": slug, "brief": brief})


def test_read_only_dashboard_and_security_headers(tmp_path):
    with running_dashboard(tmp_path) as (port, planner, workspace):
        status, body, headers = http(port, "/")
        assert status == 200
        assert '<html lang="fa" dir="rtl">' in body
        assert 'id="language-toggle"' in body
        assert 'id="graph-nodes"' in body
        assert "script-src 'self'" in headers["Content-Security-Policy"]
        assert headers["X-Frame-Options"] == "DENY"
        for path, text in (("/app.css", "prefers-reduced-motion"),
                           ("/app.js", 'document.documentElement.dir')):
            status, body, headers = http(port, path)
            assert status == 200 and text in body
            assert "no-store" == headers["Cache-Control"]
        status, payload, _ = http(port, "/api/overview")
        assert status == 200
        assert payload["summary"]["projects"] == 0
        assert payload["summary"]["verified_deliveries"] is None
        assert len(payload["roadmap"]) == 8
        assert planner.calls == 0
        assert not list(workspace.iterdir())


def test_real_create_and_detail_bilingual_html_is_not_authority(tmp_path):
    with running_dashboard(tmp_path) as (port, planner, workspace):
        status, data, headers = http(port, "/api/session")
        assert status == 200 and data["csrf_token"] == "fixture-token-opaque"
        status, result, _ = create(port, brief="<script>not executable</script> — پروژهٔ من")
        assert status == 201 and result["status"] == "brief_recorded"
        assert result["release_approved"] is False
        status, overview, _ = http(port, "/api/overview")
        assert overview["summary"]["projects"] == 1
        assert overview["projects"][0]["questions_count"] > 0
        assert overview["projects"][0]["plan_state"] == "not_started"
        assert str(workspace) not in json.dumps(overview)
        status, details, _ = http(port, "/api/projects/inventory")
        assert status == 200 and details["goal"] == "<script>not executable</script> — پروژهٔ من"
        assert details["facts"][0]["id"] == "REQ-001"
        assert details["plan"] is None
        assert details["release_approved"] is False
        assert not (workspace / "inventory" / "spec.json").exists()
        assert planner.calls == 0


@pytest.mark.parametrize("path,method,payload,csrf,origin,host,code", [
    ("/api/projects", "POST", {"slug": "safe", "brief": "test"}, False, True, None, 403),
    ("/api/projects", "POST", {"slug": "safe", "brief": "test"}, True, False, None, 403),
    ("/api/projects", "POST", {"slug": "safe", "brief": "test"}, True, True, "attacker.test", 403),
    ("/api/projects", "POST", {"slug": "../escape", "brief": "test"}, True, True, None, 400),
    ("/api/projects", "POST", {"slug": "UPPER", "brief": "test"}, True, True, None, 400),
    ("/api/projects", "POST", {"slug": ".secret", "brief": "test"}, True, True, None, 400),
    ("/api/projects", "POST", {"slug": "test", "brief": "", "role": "admin"}, True, True, None, 400),
    ("/api/projects/x/build", "POST", {}, True, True, None, 400),
])
def test_reject_cross_origin_unsafe_paths_and_unapproved_execution(
        tmp_path, path, method, payload, csrf, origin, host, code):
    with running_dashboard(tmp_path) as (port, planner, workspace):
        status, result, _ = http(port, path, method=method, payload=payload,
                                 csrf=csrf, origin=origin, host=host)
        assert status == code
        assert result["error"]
        assert not list(workspace.iterdir())
        assert planner.calls == 0


def test_model_generation_requires_explicit_paid_call_consent_and_stores_task_dag(tmp_path):
    with running_dashboard(tmp_path) as (port, planner, workspace):
        status, result, _ = create(port)
        assert status == 201
        for data in [
            {"provider": "openai", "model": "test-model", "confirm_paid_call": False},
            {"provider": "openai", "model": "test-model"},
            {"provider": "codex", "model": "test-model", "confirm_paid_call": True},
            {"provider": "openai", "model": "../../bad", "confirm_paid_call": True},
        ]:
            status, result, _ = http(port, "/api/projects/inventory/plan",
                                     method="POST", payload=data)
            assert status == 400
        assert planner.calls == 0
        status, result, _ = http(port, "/api/projects/inventory/plan", method="POST",
                                payload={"provider": "openai", "model": "test-model",
                                         "confirm_paid_call": True})
        assert status == 200
        assert result["task_count"] == 2
        assert result["ready"] == ["TASK-001"]
        assert result["release_approved"] is False
        assert "plan_path" not in result
        assert planner.calls == 1
        status, project, _ = http(port, "/api/projects/inventory")
        assert status == 200
        assert project["plan"]["state"] == "proposed"
        assert len(project["plan"]["tasks"]) == 2
        assert project["plan"]["tasks"][1]["depends_on"] == ["TASK-001"]
        assert all(task["state"] == "proposed" for task in project["plan"]["tasks"])
        assert not (workspace / "inventory" / "spec.json").exists()


def test_host_rebinding_and_traversal_urls_are_refused(tmp_path):
    with running_dashboard(tmp_path) as (port, planner, workspace):
        status, payload, _ = http(port, "/api/overview", host="malicious.example")
        assert status == 403
        status, payload, _ = http(port, "/api/projects/%2e%2e")
        assert status == 400
        status, payload, _ = http(port, "/api/projects/not-found")
        assert status == 400
        assert planner.calls == 0


def test_symlinks_in_workspace_not_followed(tmp_path):
    with running_dashboard(tmp_path) as (port, planner, workspace):
        target = tmp_path / "external"
        target.mkdir()
        try:
            (workspace / "linked").symlink_to(target, target_is_directory=True)
        except (NotImplementedError, OSError):
            pytest.skip("unprivileged Windows symlinks unavailable")
        status, payload, _ = create(port, slug="linked")
        assert status == 400 and payload["error"]
        assert not list(target.iterdir())
        status, overview, _ = http(port, "/api/overview")
        assert overview["summary"]["projects"] == 0


def test_frontend_no_model_generated_html_execution_and_both_locales(tmp_path):
    with running_dashboard(tmp_path) as (port, planner, workspace):
        _, js, _ = http(port, "/app.js")
        _, html, _ = http(port, "/")
        for marker in ("fa:", "en:", "document.documentElement.dir",
                       "textContent", "confirm_paid_call:true", "drawEdges"):
            assert marker in js
        assert ".innerHTML" not in js
        assert "fetch(" in js
        assert 'id="new-project-form"' in html
        assert 'id="plan-dialog"' in html
