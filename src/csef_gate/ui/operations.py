"""Owner-initiated, narrow dashboard actions backed by the unchanged trusted Gate.

Docker review remains measure-only. Packaging delegates to Factory's checkpoint
verifier. The dashboard cannot create PASS, resume uncertain tasks or deploy.
"""
from __future__ import annotations

import re
from pathlib import Path

from ..core import Gate, Refused, digest, plain, encoded, now
from ..factory import _delivery
from ..project import ProjectBook
from ..persistence.sqlite import DATABASE
from .inspection import inspection, run_detail, RUN_ID

IMAGE = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9._:/-]*@sha256:[a-f0-9]{64}\Z")


def reviewed_evaluation(book: ProjectBook, run_id: str, payload: dict,
                        executor_factory=None) -> dict:
    """Opt-in Docker measurement; no PASS even for all-green behavioral cases."""
    if (not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id)
            or not isinstance(payload, dict)
            or set(payload) != {"image", "confirm_reviewed_source", "confirm_measure_only"}
            or payload["confirm_reviewed_source"] is not True
            or payload["confirm_measure_only"] is not True):
        raise Refused("explicit review-only authorization and valid run ID required")
    image = payload["image"]
    if not isinstance(image, str) or not IMAGE.fullmatch(image):
        raise Refused("immutable Docker image with verified sha256 required")
    detail = run_detail(book, run_id)
    if detail["run"]["status"] == "accepted":
        raise Refused("accepted runs cannot be reevaluated")
    if any(x["status"] in ("started", "failed_or_unknown") for x in detail["attempts"]):
        raise Refused("unknown coding attempts must be reconciled before review")
    if executor_factory is None:
        from ..execution.docker_reviewed import DockerReviewedExecutor
        executor = DockerReviewedExecutor(image=image)
    else:
        executor = executor_factory(image)
    # Gate supplies the independent behavioral tests, not the frontend.
    report = Gate(book.root).evaluate(run_id, executor, measure_only=True)
    if report["status"] == "pass":
        raise Refused("measure-only evaluation must never grant PASS")
    return {
        "status": report["status"], "run_id": run_id,
        "measurement_only": True, "release_approved": False,
        "cases_passed": sum(x.get("passed") is True for x in report.get("cases", [])),
        "cases_total": len(report.get("cases", [])),
        "boundary_verified_for_release": False,
        "note": "Docker review never authorizes checkpoint or software release",
    }


def export_accepted(book: ProjectBook, run_id: str, payload: dict) -> dict:
    """Package from a verified Gate checkpoint; no arbitrary destination paths."""
    if (not isinstance(payload, dict) or set(payload) != {"confirm_export"}
            or payload["confirm_export"] is not True
            or not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id)):
        raise Refused("explicit export authorization and valid run ID required")
    row = run_detail(book, run_id)["run"]
    if row["accepted_checkpoint"] is not True:
        raise Refused("Gate checkpoint is absent or has invalid evidence")
    directory = book.root / "deliveries"
    plain(directory)
    directory.mkdir(exist_ok=True)
    output = directory / (run_id + ".zip")
    plain(output)
    result = _delivery(book, Gate(book.root), run_id, output)
    data = output.read_bytes()
    if len(data) > 12_000_000:
        output.unlink()
        raise Refused("delivery exceeded configured size limit")
    archive_sha = digest(data)
    # Record package proof in the existing owner/control transaction.
    # Resolve owner revision BEFORE acquiring a SQLite write transaction.
    owner_sha = book.current()["sha256"]
    with book.connection() as con:
        con.execute("BEGIN IMMEDIATE")
        con.execute("INSERT INTO changes(proposal,status,created) VALUES(?,?,?)",
                    (encoded({"type": "verified_delivery", "run_id": run_id,
                              "archive_sha256": archive_sha,
                              "owner_sha256": owner_sha}).decode(),
                     "delivered", now()))
    return {"status": result["status"], "run_id": run_id,
            "archive_sha256": archive_sha, "file_name": run_id + ".zip",
            "download_url": f"/api/projects/{book.root.name}/runs/{run_id}/artifact",
            "independent_gate_pass": True,
            "deployment_approved": False}


def read_export(book: ProjectBook, run_id: str) -> bytes:
    """Only download a byte-identical, provenance-backed previously exported ZIP."""
    if not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id):
        raise Refused("invalid run ID")
    row = run_detail(book, run_id)["run"]
    if not row["accepted_checkpoint"]:
        raise Refused("accepted Gate checkpoint is not independently verified")
    with book.connection() as con:
        records = con.execute(
            "SELECT proposal FROM changes WHERE status='delivered' "
            "ORDER BY id DESC LIMIT 200").fetchall()
    expected = []
    for record in records:
        from ..core import parse_json
        value = parse_json(record["proposal"])
        if (isinstance(value, dict) and value.get("type") == "verified_delivery"
                and value.get("run_id") == run_id
                and value.get("owner_sha256") == book.current()["sha256"]):
            expected.append(value["archive_sha256"])
    if len(expected) != 1:
        raise Refused("no unique verified archive receipt")
    path = book.root / "deliveries" / (run_id + ".zip")
    plain(path)
    if not path.is_file() or path.stat().st_size > 12_000_000:
        raise Refused("archive missing or exceeds byte limit")
    data = path.read_bytes()
    if digest(data) != expected[0]:
        raise Refused("archive differs from verified export receipt")
    return data
