"""Actual Chromium visual QA across desktop/mobile and FA/EN.

Run explicitly in CI, not as a unit-test fixture. Saves real screenshots and
checks layout overflow, JS errors, live form behavior and the dependency DAG.
No external model API, network resource or untrusted-code execution.
"""
from __future__ import annotations

import json
import tempfile
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright

from csef_gate.factory import create_brief, plan_brief
from csef_gate.ui.server import DashboardService, make_handler


class PlannerFixture:
    def call(self, *, prompt, schema, folder, control, role, timeout=180):
        return {
            "spec_text": "A tiny offline CLI",
            "plan_text": "Implement base module, then interface",
            "tasks_text": "TASK-001 module; TASK-002 CLI",
            "questions": [],
            "tasks": [
                {"id": "TASK-001", "title": "Save an item",
                 "fact_ids": ["REQ-001"], "depends_on": [],
                 "files": ["store.py"], "deliverable": "Storage module",
                 "acceptance": "TEST-001", "test_ids": ["TEST-001"]},
                {"id": "TASK-002", "title": "Display item list",
                 "fact_ids": ["REQ-001"], "depends_on": ["TASK-001"],
                 "files": ["main.py"], "deliverable": "CLI output",
                 "acceptance": "TEST-002", "test_ids": ["TEST-002"]},
            ],
        }, {"adapter": "visual-browser-fixture", "model": "fixture",
            "exit_code": 0, "usage": {}, "cost_usd": None}


def main():
    output = Path("visual-artifacts")
    output.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="csef-ui-browser-") as dirname:
        workspace = Path(dirname) / "workspace"
        workspace.mkdir()
        owner = create_brief(workspace / "stock-demo", "Build a small stock CLI",
                             answers={"users": "individual", "workflow": "enter items",
                                      "success": "list is returned",
                                      "constraints": "offline Python"})
        plan_brief(owner, PlannerFixture())
        service = DashboardService(workspace)
        token = "browser-qa-token"
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(service, token))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                for label, width, height in (
                    ("desktop", 1440, 900), ("mobile", 390, 844)):
                    for language in ("fa", "en"):
                        context = browser.new_context(viewport={
                            "width": width, "height": height},
                            device_scale_factor=1, reduced_motion="reduce")
                        page = context.new_page()
                        failures = []
                        page.on("pageerror", lambda error: failures.append(str(error)))
                        page.goto("http://127.0.0.1:" + str(server.server_port) + "/",
                                  wait_until="networkidle")
                        page.locator("#graph-nodes .graph-node").first.wait_for(timeout=15000)
                        assert page.locator("#graph-nodes .graph-node").count() == 2
                        assert page.locator("#stat-projects").inner_text().strip() == "1"
                        if language == "en":
                            page.locator("#language-toggle").click()
                        assert page.locator("html").get_attribute("dir") == (
                            "rtl" if language == "fa" else "ltr")
                        assert page.locator("#verification-center").is_visible()
                        assert page.locator("#delivery-center").is_visible()
                        assert page.locator("#execution-center").is_visible()
                        assert page.locator("#checkpoint-count").inner_text().strip() == "0"
                        assert page.locator("#run-count").inner_text().strip() == "0"
                        dims = page.evaluate("""() => ({
                            viewport: window.innerWidth,
                            content: document.documentElement.scrollWidth,
                            documentHeight: document.documentElement.scrollHeight,
                            operationsWidth: document.querySelector('.operations-area').getBoundingClientRect().width
                        })""")
                        assert dims["content"] <= dims["viewport"] + 2, dims
                        assert dims["operationsWidth"] <= dims["viewport"], dims
                        assert not failures, failures
                        page.screenshot(path=str(output / (label + "-" + language + ".png")),
                                        full_page=True, animations="disabled")
                        print(json.dumps({"device": label, "lang": language,
                                          "viewport": [width, height],
                                          "document_width": dims["content"],
                                          "screenshot": label + "-" + language + ".png"}))
                        if label == "desktop" and language == "fa":
                            # Real DOM + API project creation; no model API / billing.
                            page.locator("#project-slug").fill("new-project")
                            page.locator("#brief").fill("A second project")
                            page.locator("#new-project-form button[type=submit]").click()
                            page.wait_for_function("document.querySelector('#stat-projects').textContent.trim() === '2'", timeout=10000)
                            assert page.locator("#stat-projects").inner_text().strip() == "2"
                        context.close()
                browser.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=4)


if __name__ == "__main__":
    main()
