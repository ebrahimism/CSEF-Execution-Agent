"""Real Chromium desktop/mobile screenshot QA of Persian/English dashboard."""
from __future__ import annotations
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen
import pytest

playwright_api = pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright, expect


def _port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture()
def local_dashboard(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    port = _port()
    proc = subprocess.Popen(
        [sys.executable, "-m", "csef_gate.ui.server",
         "--workspace", str(workspace), "--port", str(port)],
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    try:
        for _ in range(100):
            if proc.poll() is not None:
                raise AssertionError("Dashboard exited before becoming ready")
            try:
                with urlopen("http://127.0.0.1:" + str(port) + "/api/session",
                             timeout=.4) as response:
                    if response.status == 200:
                        break
            except OSError:
                time.sleep(.1)
        else:
            raise AssertionError("Local dashboard did not start")
        yield "http://127.0.0.1:" + str(port)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
        proc.stderr.close()


@pytest.mark.parametrize("width,height", [(1440, 900), (390, 844)])
def test_real_chromium_rtl_ltr_and_owner_workflow(local_dashboard, tmp_path, width, height):
    out = Path(os.environ.get("CSEF_VISUAL_OUTPUT", str(tmp_path / "screenshots")))
    out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True, args=["--disable-gpu"])
        page = browser.new_page(viewport={"width": width, "height": height},
                                device_scale_factor=1)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        try:
            page.goto(local_dashboard, wait_until="networkidle")
            expect(page.locator("#language-toggle")).to_be_visible()
            expect(page.locator("#new-project-form")).to_be_visible()
            assert page.evaluate("document.documentElement.dir") == "rtl"
            assert page.evaluate("document.documentElement.lang") == "fa"

            page.locator("#project-slug").fill("visual-demo")
            page.locator("#brief").fill("یک ابزار مدیریت داده کوچک برای آزمون رابط کاربری")
            page.locator("#new-project-form button[type=submit]").click()
            expect(page.locator("#control-project-pill")).to_have_text("visual-demo")
            expect(page.locator("#project-journey .journey-step")).to_have_count(8)
            expect(page.locator("#owner-facts")).to_contain_text("REQ-001")
            expect(page.locator("#delivery-content")).to_contain_text("تحویل")
            page.locator("#operations").scroll_into_view_if_needed()
            overflow = page.evaluate("""() => ({
                width: innerWidth,
                document: document.documentElement.scrollWidth,
                offenders: [...document.querySelectorAll("body *")].map(x => {
                    const b = x.getBoundingClientRect();
                    return {tag: x.tagName, id: x.id, cls: x.className && x.className.baseVal
                      ? x.className.baseVal : String(x.className || "").slice(0,50),
                      left: Math.round(b.left), right: Math.round(b.right), width: Math.round(b.width)};
                }).filter(x => x.right > innerWidth+3 || x.left < -3)
                  .sort((a,b)=>b.right-a.right).slice(0,12)
            })""")
            assert overflow["document"] <= width + 2,                 "Horizontal overflow in RTL " + str(width) + ": " + str(overflow)
            page.screenshot(path=str(out / ("dashboard-" + str(width) + "-fa.png")),
                            full_page=True, animations="disabled")

            page.locator("#language-toggle").click()
            assert page.evaluate("document.documentElement.dir") == "ltr"
            expect(page.locator("#owner-facts")).to_contain_text("REQ-001")
            expect(page.locator("#test-results")).to_contain_text("No Gate evaluation")
            expect(page.locator("#delivery-content")).to_contain_text("No verified")
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 2"), \
                "Horizontal overflow in LTR " + str(width)
            page.screenshot(path=str(out / ("dashboard-" + str(width) + "-en.png")),
                            full_page=True, animations="disabled")
            assert not errors, errors
        finally:
            browser.close()
