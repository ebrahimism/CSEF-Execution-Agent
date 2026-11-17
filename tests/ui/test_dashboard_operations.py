"""Evidence-backed S0-S7 dashboard, real SQLite + Gate, safe owner edits.

No paid API calls, no untrusted program execution and no fabricated PASS.
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

from csef_gate.core import Gate, Refused, encoded
from csef_gate.providers import usage as provider_usage
from csef_gate.ui.server import DashboardService, make_handler


@contextmanager
def browser_api(tmp_path, reviewed_executor=None):
    workspace=tmp_path/"workspace"
    workspace.mkdir()
    service=DashboardService(workspace, reviewed_executor=reviewed_executor)
    server=ThreadingHTTPServer(("127.0.0.1",0),make_handler(service,"known-private-test-csrf"))
    thread=threading.Thread(target=server.serve_forever,daemon=True)
    thread.start()
    try: yield server.server_port,workspace
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def api(port,path,method="GET",payload=None,headers=None):
    origin="http://127.0.0.1:"+str(port)
    h={"Host":"127.0.0.1:"+str(port)}
    h.update(headers or {})
    body=None
    if method != "GET":
        h.setdefault("Content-Type","application/json")
        h.setdefault("Origin",origin)
        h.setdefault("X-CSEF-CSRF","known-private-test-csrf")
        body=json.dumps(payload,ensure_ascii=False).encode("utf-8")
    req=Request(origin+path,headers=h,data=body,method=method)
    try:
        with urlopen(req,timeout=8) as response:
            if response.headers.get("Content-Type", "").startswith("application/zip"):
                return response.status,response.read()
            if path.endswith((".js",".css")) or path=="/":
                return response.status,response.read().decode("utf-8")
            return response.status,json.loads(response.read())
    except HTTPError as error:
        return error.code,json.loads(error.read())


def create(port,slug="sample"):
    return api(port,"/api/projects","POST",{"slug":slug,"brief":"یک CLI ساده برای ثبت داده"})


def test_s0_through_s7_control_is_evidence_derived_not_fabricated(tmp_path):
    with browser_api(tmp_path) as (port,root):
        status,result=create(port)
        assert status==201
        status,data=api(port,"/api/projects/sample/control")
        assert status==200
        assert data["owner_version"]==1
        assert [p["id"] for p in data["journey"]]==[
            "S0","S1","S6a","S2","S3","S4","S5","S7"]
        assert [p["state"] for p in data["journey"]]==[
            "recorded","not_started","available","not_verified","not_started",
            "not_verified","blocked","not_verified"]
        assert data["gate"]["state"]=="not_configured"
        assert data["gate"]["runs"]==[]
        assert data["gate"]["tests"]==[]
        assert data["gate"]["checkpoints"]==[]
        assert data["budget"]["used_calls"]==0
        assert data["capabilities"]["unsafe_host_execution"] is False
        assert data["capabilities"]["automatic_resume"] is False
        assert data["capabilities"]["delivery_export"] is False
        assert data["release_approved"] is False


def test_owner_answer_is_versioned_and_stale_edit_refused(tmp_path):
    with browser_api(tmp_path) as (port,root):
        create(port)
        status,out=api(port,"/api/projects/sample/answers","POST",{
            "expected_version":1,"reason":"مالک الزامات را تکمیل کرد",
            "answers":{"users":"فقط خودم", "workflow":"ورودی JSON و خروجی JSON"}
        })
        assert status==200 and out["project_version"]==2
        status,proj=api(port,"/api/projects/sample")
        assert proj["version"]==2
        assert proj["answers"]["users"]=="فقط خودم"
        status,view=api(port,"/api/projects/sample/control")
        assert view["revisions"][0]["reason"]=="مالک الزامات را تکمیل کرد"
        assert view["revisions"][0]["version"]==2
        assert any(x["type"]=="owner_revision" for x in view["events"])
        assert all("answers" not in row for row in view["events"])
        status,out=api(port,"/api/projects/sample/answers","POST",{
            "expected_version":1,"reason":"outdated change",
            "answers":{"success":"wrong"}
        })
        assert status==400 and "stale" in out["error"]
        assert api(port,"/api/projects/sample")[1]["version"]==2


@pytest.mark.parametrize("headers,payload,expected",[
    ({"Origin":"http://malicious.example"},{
        "expected_version":1,"reason":"owner", "answers":{"users":"X"}},403),
    ({"X-CSEF-CSRF":"bad"},{
        "expected_version":1,"reason":"owner", "answers":{"users":"X"}},403),
    ({},{"expected_version":1,"reason":"owner","answers":{"users":"X"},"status":"pass"},400),
    ({},{"expected_version":1,"reason":"owner","answers":{"BAD":"X"}},400),
    ({},{"expected_version":True,"reason":"owner","answers":{"users":"X"}},400),
])
def test_owner_edits_reject_cross_origin_privilege_and_invalid_contract(
        tmp_path,headers,payload,expected):
    with browser_api(tmp_path) as (port,root):
        create(port)
        status,out=api(port,"/api/projects/sample/answers","POST",payload,headers=headers)
        assert status==expected
        assert api(port,"/api/projects/sample")[1]["version"]==1


class OfflineReviewedExecutor:
    """No real program execution; deliberately not a verified sandbox."""
    def probe(self,*,snapshot,scratch,control):
        return {"backend":"test-fixture", "verified":False,
                "file_boundary_verified":True,
                "network_isolation_verified":False}
    def run(self,*,snapshot,scratch,control,entrypoint,args,timeout):
        return {"exit_code":0,"stdout":'{"value":10}',"stderr":"",
                "timed_out":False,"overflow":False,"elapsed_s":0.001}


def gate_setup(tmp_path,root):
    candidate=tmp_path/"candidate"
    candidate.mkdir()
    (candidate/"app.py").write_text('print("{\\"value\\":10}")\n',encoding="utf-8")
    oracle=tmp_path/"oracle.json"
    oracle.write_bytes(encoded({
        "version":1, "objective":"sample only",
        "source_files":["app.py"],"editable_files":["app.py"],
        "entrypoint":"app.py", "max_attempts":2,
        "agent_timeout_s":20,"case_timeout_s":5,
        "cases":[{"id":"TEST-001","args":[],"exit_code":0,"stdout_json":{"value":10}}],
    }))
    gate=Gate.initialize(root,candidate,oracle,attach=True)
    return gate


def test_gate_run_and_reviewed_tests_show_without_false_pass(tmp_path):
    with browser_api(tmp_path) as (port,root):
        create(port)
        gate=gate_setup(tmp_path,root/"sample")
        run=gate.prepare()
        report=gate.evaluate(run,OfflineReviewedExecutor(),measure_only=True)
        assert report["status"]=="review"
        code,data=api(port,"/api/projects/sample/control")
        assert code==200
        assert data["gate"]["integrity"]=="valid"
        assert data["gate"]["tests"]==[{"id":"TEST-001","status":"frozen"}]
        assert len(data["gate"]["runs"])==1
        assert data["gate"]["runs"][0]["id"]==run
        assert data["gate"]["runs"][0]["checkpoint"] is False
        assert data["gate"]["evaluations"][0]["integrity"]=="valid"
        assert data["gate"]["evaluations"][0]["status"]=="review"
        assert data["gate"]["evaluations"][0]["passed"]==1
        assert data["gate"]["evaluations"][0]["boundary_verified"] is False
        assert data["gate"]["checkpoints"]==[]
        assert data["gate"]["accepted_count"]==0
        assert data["journey"][5]["state"]=="reviewed"
        assert data["journey"][6]["state"]=="blocked"


def test_tampered_report_is_flagged_invalid_never_verified(tmp_path):
    with browser_api(tmp_path) as (port,root):
        create(port)
        gate=gate_setup(tmp_path,root/"sample")
        run=gate.prepare()
        gate.evaluate(run,OfflineReviewedExecutor(),measure_only=True)
        with gate.connect() as con:
            report=Path(con.execute(
                "SELECT report FROM evaluations WHERE run_id=?",(run,)
            ).fetchone()[0])
        report.write_text('{"status":"pass"}',encoding="utf-8")
        _,data=api(port,"/api/projects/sample/control")
        assert data["gate"]["evaluations"][0]["integrity"]=="invalid"
        assert data["gate"]["evaluations"][0]["status"]=="blocked"
        assert data["gate"]["accepted_count"]==0
        assert data["capabilities"]["delivery_export"] is False


def test_unknown_attempt_requires_manual_reconciliation(tmp_path):
    with browser_api(tmp_path) as (port,root):
        create(port)
        gate=gate_setup(tmp_path,root/"sample")
        run=gate.prepare()
        with gate.connect() as con:
            con.execute("INSERT INTO attempts VALUES(?,?,?,?,?)",
                        ("attempt-"+"b"*32,run,"failed_or_unknown",
                         str(root/"sample"/"runs"/run/"fake"),"2026-11-17T01:00:00Z"))
        _,data=api(port,"/api/projects/sample/control")
        assert data["gate"]["runs"][0]["unknown_attempt"] is True
        assert data["gate"]["runs"][0]["recovery"]=="manual_reconciliation"
        assert data["journey"][4]["state"]=="attempted"
        assert data["gate"]["accepted_count"]==0


def test_provider_request_journal_uses_existing_database_not_secret_values(tmp_path,monkeypatch):
    monkeypatch.setenv("CSEF_PROVIDER_MAX_CALLS","3")
    with browser_api(tmp_path) as (port,root):
        create(port)
        ident=provider_usage.reserve(root/"sample","openai","some-model","test")
        provider_usage.settle(root/"sample",ident,completed=False)
        _,data=api(port,"/api/projects/sample/control")
        assert data["budget"]["used_calls"]==1
        assert data["budget"]["remaining_calls"]==2
        assert data["budget"]["breakdown"]["provider_unknown"]==1
        assert any(x["type"]=="provider_request" for x in data["events"])
        assert data["journey"][3]["state"]=="configured_only"
        assert data["capabilities"]["live_api_verified"] is False


def test_operations_assets_are_same_origin_and_do_not_add_execution_routes(tmp_path):
    with browser_api(tmp_path) as (port,root):
        for path,fragment in (
            ("/operations.js","csef:project"),
            ("/operations.css","journey-strip"),
            ("/","project-journey"),
        ):
            code,text=api(port,path)
            assert code==200 and fragment.replace('\\"','"') in text
        assert api(port,"/api/projects/sample/build","POST",{})[0]==400
        assert api(port,"/api/projects/sample/resume","POST",{})[0]==400
        assert api(port,"/api/projects/sample/accept","POST",{})[0]==400
        assert api(port,"/api/projects/sample/deliver","POST",{})[0]==400


def test_unexpected_owner_goal_does_not_become_an_accepted_release(tmp_path):
    with browser_api(tmp_path) as (port,root):
        code,_=api(port,"/api/projects","POST",{
            "slug":"xss","brief":"<img src=x onerror=alert(1)>"
        })
        assert code==201
        _,project=api(port,"/api/projects/xss")
        assert "<img" in project["goal"]
        _,inspection=api(port,"/api/projects/xss/control")
        assert inspection["release_approved"] is False
        assert inspection["gate"]["accepted_count"]==0
        assert not inspection["capabilities"]["run_execution"]



def test_checkpoint_from_old_owner_revision_never_shown_as_current_release(tmp_path):
    """A fixture-only accepted checkpoint must become stale after owner amendment."""
    class FixtureTrusted(OfflineReviewedExecutor):
        def probe(self, *, snapshot, scratch, control):
            return {"backend":"test-double-only", "verified":True,
                    "file_boundary_verified":True,
                    "network_isolation_verified":True}
    with browser_api(tmp_path) as (port,root):
        create(port)
        gate=gate_setup(tmp_path,root/"sample")
        run=gate.prepare()
        report=gate.evaluate(run,FixtureTrusted(),measure_only=False)
        assert report["status"]=="pass"
        gate.accept(run)
        _,before=api(port,"/api/projects/sample/control")
        assert before["gate"]["accepted_count"]==1
        assert before["journey"][5]["state"]=="verified"
        status,_=api(port,"/api/projects/sample/answers","POST",{
            "expected_version":1,
            "reason":"Owner changed a relevant requirement",
            "answers":{"success":"A new and different outcome is now required"}
        })
        assert status==200
        _,after=api(port,"/api/projects/sample/control")
        assert after["gate"]["accepted_count"]==0
        assert after["gate"]["checkpoints"][0]["integrity"]=="unverified"
        assert after["journey"][5]["state"]=="reviewed"
        assert after["journey"][6]["state"]=="blocked"
        assert after["release_approved"] is False


def test_same_task_id_in_unrelated_run_does_not_fake_progress(tmp_path):
    from csef_gate.core import encoded
    from csef_gate.project import ProjectBook
    from csef_gate.ui.inspection import inspect
    with browser_api(tmp_path) as (port,root):
        create(port)
        book=ProjectBook(root/"sample")
        gate=gate_setup(tmp_path,root/"sample")
        run=gate.prepare()
        with book.connection() as con:
            con.execute(
                "INSERT INTO changes(proposal,status,created) VALUES(?,?,?)",
                (encoded({"type":"factory_run","run_id":run,
                          "graph_sha256":"unrelated-graph","owner_sha256":book.current()["sha256"]}).decode(),
                 "recorded","2026-11-17T01:00:00Z"))
            con.execute(
                "INSERT INTO changes(proposal,status,created) VALUES(?,?,?)",
                (encoded({"type":"factory_task","run_id":run,"task_id":"TASK-001"}).decode(),
                 "factory_done","2026-11-17T01:00:01Z"))
        plan={"state":"proposed","graph_sha256":"correct-graph",
              "tasks":[{"id":"TASK-001"}]}
        projection=inspect(book,plan)
        assert projection["task_progress"]==[{
            "id":"TASK-001","status":"proposed","independently_accepted":False}]



def test_reviewed_only_gate_action_requires_owner_confirmation_and_cannot_pass(tmp_path):
    with browser_api(tmp_path, reviewed_executor=lambda image: OfflineReviewedExecutor()) as (port,root):
        create(port)
        gate=gate_setup(tmp_path,root/"sample")
        run=gate.prepare()
        image="python:3.11-slim@sha256:"+"a"*64
        for payload in [
            {"run_id":run,"image":image,"confirm_reviewed_source":False,"measure_only":True},
            {"run_id":run,"image":image,"confirm_reviewed_source":True,"measure_only":False},
            {"run_id":run,"image":"python:latest","confirm_reviewed_source":True,"measure_only":True},
        ]:
            status,out=api(port,"/api/projects/sample/review","POST",payload)
            assert status==400
        status,data=api(port,"/api/projects/sample/review","POST",{
            "run_id":run,"image":image,"confirm_reviewed_source":True,"measure_only":True
        })
        assert status==200 and data["status"]=="review"
        assert data["measurement_only"] is True
        assert data["release_approved"] is False
        assert data["delivery_created"] is False
        assert data["cases_passed"]==1
        _,view=api(port,"/api/projects/sample/control")
        assert view["gate"]["accepted_count"]==0
        assert view["gate"]["evaluations"][0]["status"]=="review"
        assert view["capabilities"]["reviewed_measurement"] is True
        assert view["capabilities"]["run_execution"] is False
        assert view["capabilities"]["delivery_export"] is False


def test_export_gate_checkpoint_only_with_sha256_download_and_revocation(tmp_path):
    from io import BytesIO
    from zipfile import ZipFile
    class FixtureTrusted(OfflineReviewedExecutor):
        def probe(self, *, snapshot, scratch, control):
            return {"backend":"fixture-not-production", "verified":True,
                    "file_boundary_verified":True,"network_isolation_verified":True}
    with browser_api(tmp_path) as (port,root):
        create(port)
        gate=gate_setup(tmp_path,root/"sample")
        run=gate.prepare()
        denied={"run_id":run,"confirm_export":True}
        status,err=api(port,"/api/projects/sample/export","POST",denied)
        assert status==400
        assert not (root/"sample"/"exports").exists()
        gate.evaluate(run,FixtureTrusted(),measure_only=False)
        gate.accept(run)
        status,err=api(port,"/api/projects/sample/export","POST",{
            "run_id":run,"confirm_export":False})
        assert status==400
        status,response=api(port,"/api/projects/sample/export","POST",denied)
        assert status==200 and response["status"]=="delivered"
        assert response["release_approved"] is False
        assert response["deployment_approved"] is False
        assert response["download"].endswith("/archives/"+run)
        status,content=api(port,response["download"])
        assert status==200
        with ZipFile(BytesIO(content)) as archive:
            assert "source/app.py" in archive.namelist()
            assert "manifest.json" in archive.namelist()
        status,err=api(port,"/api/projects/sample/export","POST",denied)
        assert status==400, "second export must not overwrite previous archive"
        saved=root/"sample"/"exports"/(run+".zip")
        saved.write_bytes(b"tampered")
        status,err=api(port,response["download"])
        assert status==400
        assert "integrity" in err["error"]


def test_owner_revision_blocks_export_of_old_checkpoint(tmp_path):
    class FixtureTrusted(OfflineReviewedExecutor):
        def probe(self, *, snapshot, scratch, control):
            return {"backend":"fixture-not-production", "verified":True,
                    "file_boundary_verified":True, "network_isolation_verified":True}
    with browser_api(tmp_path) as (port,root):
        create(port)
        gate=gate_setup(tmp_path,root/"sample")
        run=gate.prepare()
        gate.evaluate(run,FixtureTrusted(),measure_only=False)
        gate.accept(run)
        status,result=api(port,"/api/projects/sample/export","POST",{
            "run_id":run,"confirm_export":True})
        assert status==200
        api(port,"/api/projects/sample/answers","POST",{
            "expected_version":1,"reason":"Updated success criterion",
            "answers":{"success":"New acceptance criteria required"}
        })
        status,err=api(port,result["download"])
        assert status==400
        status,err=api(port,"/api/projects/sample/export","POST",{
            "run_id":run,"confirm_export":True})
        assert status==400
