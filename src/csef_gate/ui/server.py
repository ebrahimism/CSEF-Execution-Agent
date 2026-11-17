"""S6a local-only bilingual dashboard over existing ProjectBook and Factory.

No new database or acceptance authority. Host is fixed to 127.0.0.1.
Do not expose via a reverse proxy, port forward, or public network.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import secrets
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from ..core import Refused, encoded, parse_json, plain
from ..engineering.task_graph import validate_graph
from ..factory import create_brief, plan_brief
from ..project import ProjectBook, QUESTIONS
from .inspection import inspection, run_detail

SLUG = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,46}[a-z0-9])?\Z")
MAX_BODY = 24_000
STATIC = Path(__file__).resolve().parent / "static"
ASSETS = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/app.css": ("app.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
}
ROADMAP = (
    ("S0", "baseline", "partial"),
    ("S1", "planning", "partial"),
    ("S2", "providers", "partial"),
    ("S3", "execution", "partial"),
    ("S4", "verification", "partial"),
    ("S5", "delivery", "partial"),
    ("S6a", "interface", "prototype"),
    ("S7", "validation", "not_verified"),
)


def _slug(value: str) -> str:
    if not isinstance(value, str) or not SLUG.fullmatch(value):
        raise Refused("invalid project slug; use 1–48 lower-case letters, digits and hyphens")
    return value


class DashboardService:
    """Thin application adapter, with no copies of project business logic."""

    def __init__(self, workspace: Path, *, planner=None):
        self.workspace = Path(workspace).absolute()
        plain(self.workspace)
        if not self.workspace.is_dir():
            raise Refused("workspace directory must exist; create it explicitly")
        self.planner = planner

    def _directory(self, slug: str) -> Path:
        path = self.workspace / _slug(slug)
        plain(path)
        return path

    def project(self, slug: str) -> dict:
        book = ProjectBook(self._directory(slug))
        state = book.status()
        overview = self._latest_plan(book, state["project"])
        return {
            "slug": slug, "goal": state["project"]["goal"],
            "version": state["project"]["version"],
            "facts": state["project"]["facts"],
            "answers": state["project"]["answers"],
            "stages": state["stages"], "calls": state["calls"],
            "questions": state["questions"],
            "pending_changes": state["pending_changes"],
            "plan": overview, "release_approved": False,
        }

    @staticmethod
    def _latest_plan(book: ProjectBook, owner: dict) -> dict | None:
        with book.connection() as con:
            rows = con.execute(
                "SELECT proposal,created FROM changes WHERE status='proposed' "
                "ORDER BY id DESC LIMIT 200"
            ).fetchall()
        for row in rows:
            record = parse_json(row["proposal"])
            if not isinstance(record, dict) or record.get("type") != "factory_plan":
                continue
            proposal = record.get("body")
            if not isinstance(proposal, dict) or not isinstance(proposal.get("graph"), dict):
                return {"state": "invalid", "tasks": []}
            try:
                result = validate_graph(owner, proposal["graph"])
            except (Refused, KeyError, TypeError, ValueError):
                return {"state": "stale", "tasks": []}
            tasks = proposal["graph"]["tasks"]
            return {
                "state": "needs_owner" if proposal.get("questions") else "proposed",
                "task_count": result["task_count"],
                "ready": result["ready"],
                "questions": proposal.get("questions") or [],
                "receipt": proposal.get("planner_receipt", {}),
                "created": row["created"],
                "tasks": [{
                    "id": t["id"], "title": t["title"], "depends_on": t["depends_on"],
                    "fact_ids": t["fact_ids"], "acceptance": t["acceptance"],
                    "deliverable": t["deliverable"], "files": t["files"],
                    "test_ids": t["test_ids"], "state": "proposed",
                } for t in tasks],
            }
        return None

    def project_inspection(self, slug: str) -> dict:
        """Observable facts from the existing owner/Gate stores; no model authority."""
        book = ProjectBook(self._directory(slug))
        return inspection(book)

    def run_inspection(self, slug: str, run_id: str) -> dict:
        book = ProjectBook(self._directory(slug))
        return run_detail(book, run_id)

    def projects(self) -> list[dict]:
        items = []
        for path in sorted(self.workspace.iterdir(), key=lambda p: p.name):
            if len(items) >= 100:
                break
            if not path.is_dir() or not SLUG.fullmatch(path.name):
                continue
            try:
                item = self.project(path.name)
            except (Refused, OSError, ValueError, KeyError):
                continue
            items.append({
                "slug": item["slug"], "goal": item["goal"],
                "version": item["version"], "questions_count": len(item["questions"]),
                "plan_state": item["plan"]["state"] if item["plan"] else "not_started",
                "task_count": item["plan"]["task_count"] if item["plan"]
                              and item["plan"].get("task_count") else 0,
            })
        return items

    def overview(self) -> dict:
        projects = self.projects()
        return {
            "projects": projects,
            "summary": {
                "projects": len(projects),
                "proposed_tasks": sum(p["task_count"] for p in projects),
                "needs_input": sum(bool(p["questions_count"]) or p["plan_state"] == "needs_owner"
                                   for p in projects),
                "verified_deliveries": None,  # Not asserted from owner/project model data.
            },
            "roadmap": [{"id": code, "name": name, "state": state}
                        for code, name, state in ROADMAP],
            "providers": {
                "openai": bool(os.getenv("OPENAI_API_KEY")),
                "anthropic": bool(os.getenv("ANTHROPIC_API_KEY")),
            },
            "note": "Project plans are proposals; no live API, isolation or release is asserted.",
        }

    def create(self, payload: dict) -> dict:
        if not isinstance(payload, dict) or set(payload) - {"slug", "brief", "answers"}:
            raise Refused("invalid project fields")
        path = self._directory(payload.get("slug"))
        answers = payload.get("answers", {})
        if not isinstance(answers, dict) or set(answers) - set(QUESTIONS):
            raise Refused("invalid intake answers")
        for value in answers.values():
            if not isinstance(value, str) or len(value) > 2000:
                raise Refused("invalid answer")
        book = create_brief(path, payload.get("brief"), answers=answers)
        return {"slug": path.name, "status": "brief_recorded",
                "version": book.current()["version"], "release_approved": False}

    def generate_plan(self, slug: str, payload: dict) -> dict:
        if not isinstance(payload, dict) or set(payload) != {
            "provider", "model", "confirm_paid_call"}:
            raise Refused("explicit model, provider, and consent are required")
        if payload["confirm_paid_call"] is not True:
            raise Refused("API billing consent required for each planning request")
        if payload["provider"] not in ("openai", "anthropic"):
            raise Refused("supported provider must be explicitly selected")
        model = payload["model"]
        if (not isinstance(model, str) or not 1 <= len(model) <= 100
                or not re.fullmatch(r"[a-zA-Z0-9_.:/-]+", model)
                or ".." in model or model.startswith(("/", ".")) or "//" in model):
            raise Refused("invalid explicit model name")
        if self.planner is None:
            from ..providers.direct import select_provider
            client, _ = select_provider(payload["provider"], model)
        else:
            client = self.planner(payload["provider"], model)
        book = ProjectBook(self._directory(slug))
        result = plan_brief(book, client)
        # Never disclose absolute local paths in API responses.
        return {k: v for k, v in result.items()
                if k not in ("plan_path", "spec_kit_bundle")}


def make_handler(service: DashboardService, token: str):
    """Per-server handler; no global shared mutable authentication state."""

    class Handler(BaseHTTPRequestHandler):
        server_version = "CSEF-LocalDashboard/1"
        sys_version = ""

        def _headers(self, status, content_type, content_length):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(content_length))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'none'; script-src 'self'; style-src 'self'; "
                "img-src 'self' data:; connect-src 'self'; font-src 'self'; "
                "base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
            )
            self.end_headers()

        def _send(self, status, payload):
            raw = encoded(payload)
            self._headers(status, "application/json; charset=utf-8", len(raw))
            self.wfile.write(raw)

        def _host_ok(self):
            # Prevent Host-header/DNS-rebinding access to loopback services.
            return self.headers.get("Host", "") == f"127.0.0.1:{self.server.server_port}"

        def _origin_ok(self):
            return self.headers.get("Origin") == f"http://127.0.0.1:{self.server.server_port}"

        def _route(self):
            parsed = urlsplit(self.path)
            if parsed.query or parsed.fragment or "%" in parsed.path:
                raise Refused("unsupported URL")
            if parsed.path in ASSETS:
                return parsed.path, ()
            if parsed.path == "/api/session":
                return "session", ()
            if parsed.path == "/api/overview":
                return "overview", ()
            if parsed.path == "/api/projects":
                return "projects", ()
            m = re.fullmatch(r"/api/projects/([a-z0-9-]{1,48})/runs/(run-[0-9a-f]{32})", parsed.path)
            if m:
                return "run_inspection", (m.group(1), m.group(2))
            m = re.fullmatch(r"/api/projects/([a-z0-9-]{1,48})/(inspection)", parsed.path)
            if m:
                return "inspection", (m.group(1),)
            m = re.fullmatch(r"/api/projects/([a-z0-9-]{1,48})(?:/(plan))?", parsed.path)
            if m:
                return "plan" if m.group(2) else "project", (m.group(1),)
            raise Refused("unknown route")

        def do_GET(self):
            if not self._host_ok():
                return self._send(HTTPStatus.FORBIDDEN, {"error": "invalid host"})
            try:
                route, arguments = self._route()
                if route in ASSETS:
                    filename, content_type = ASSETS[route]
                    payload = (STATIC / filename).read_bytes()
                    self._headers(HTTPStatus.OK, content_type, len(payload))
                    return self.wfile.write(payload)
                if route == "session":
                    return self._send(HTTPStatus.OK, {"csrf_token": token})
                if route == "overview":
                    return self._send(HTTPStatus.OK, service.overview())
                if route == "projects":
                    return self._send(HTTPStatus.OK, {"projects": service.projects()})
                if route == "project":
                    return self._send(HTTPStatus.OK, service.project(arguments[0]))
                if route == "inspection":
                    return self._send(HTTPStatus.OK, service.project_inspection(arguments[0]))
                if route == "run_inspection":
                    return self._send(HTTPStatus.OK, service.run_inspection(*arguments))
                return self._send(HTTPStatus.NOT_FOUND, {"error": "unknown route"})
            except (Refused, OSError, ValueError, KeyError) as error:
                return self._send(HTTPStatus.BAD_REQUEST, {"error": str(error)})

        def do_POST(self):
            if not self._host_ok() or not self._origin_ok():
                return self._send(HTTPStatus.FORBIDDEN, {"error": "invalid origin or host"})
            if not secrets.compare_digest(self.headers.get("X-CSEF-CSRF", ""), token):
                return self._send(HTTPStatus.FORBIDDEN, {"error": "invalid csrf token"})
            try:
                route, arguments = self._route()
                if route not in ("projects", "plan"):
                    return self._send(HTTPStatus.NOT_FOUND, {"error": "unknown route"})
                if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                    raise Refused("JSON body required")
                length = self.headers.get("Content-Length", "")
                if not length.isascii() or not length.isdecimal() or not 1 <= int(length) <= MAX_BODY:
                    raise Refused("invalid body length")
                payload = parse_json(self.rfile.read(int(length)).decode("utf-8"))
                if route == "projects":
                    return self._send(HTTPStatus.CREATED, service.create(payload))
                return self._send(HTTPStatus.OK, service.generate_plan(arguments[0], payload))
            except (Refused, ValueError, UnicodeError, OSError, KeyError, TypeError) as error:
                # Errors may include user-controlled paths but never provider key/header data.
                return self._send(HTTPStatus.BAD_REQUEST, {"error": str(error)})

        def log_message(self, format, *args):
            # Avoid storing owner names, project briefs, paths or API details.
            pass

    return Handler


def serve(workspace: Path, *, port=8765):
    if type(port) is not int or not 1024 <= port <= 65535:
        raise Refused("port must be between 1024 and 65535")
    service = DashboardService(workspace)
    token = secrets.token_urlsafe(32)
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(service, token))
    print(f"CSEF dashboard: http://127.0.0.1:{server.server_port}/", flush=True)
    try:
        server.serve_forever(poll_interval=0.3)
    finally:
        server.server_close()


def main(argv=None):
    parser = argparse.ArgumentParser(description="CSEF local bilingual dashboard")
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    try:
        serve(args.workspace, port=args.port)
    except (Refused, OSError) as error:
        parser.exit(2, str(error) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
