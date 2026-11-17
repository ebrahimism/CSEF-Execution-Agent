"""Reviewed Docker adapter contract tests; no real isolation is implied."""
import json
from types import SimpleNamespace

import pytest

from csef_gate.core import Gate, Refused, encoded
from csef_gate.execution.docker_reviewed import DockerReviewedExecutor

IMAGE = "python:3.11-slim@sha256:" + "a" * 64


def test_docker_requires_pinned_image():
    with pytest.raises(Refused, match="immutable"):
        DockerReviewedExecutor(image="python:3.11-slim", docker="docker")


def test_reviewed_executor_cannot_authorize_release(tmp_path, monkeypatch):
    from csef_gate.execution import docker_reviewed as module
    monkeypatch.setattr(module.subprocess, "run",
                        lambda *a, **kw: SimpleNamespace(returncode=0))
    seen = []

    def fake_docker(argv, **kwargs):
        seen.append(argv)
        if "-c" in argv:
            output = json.dumps({
                "source_read": True, "scratch_write": True, "source_write_denied": True,
                "control_absent": True, "host_loopback_denied": True,
            })
        else:
            output = "1"
        return {"exit_code": 0, "stdout": output, "stderr": "",
                "timed_out": False, "overflow": False, "elapsed_s": 0.001}

    backend = DockerReviewedExecutor(image=IMAGE, docker="docker", runner=fake_docker)
    source = tmp_path / "source"
    source.mkdir()
    (source / "app.py").write_text("print(1)\n")
    spec_path = tmp_path / "spec.json"
    spec_path.write_bytes(encoded({
        "version": 1, "objective": "return JSON value 1",
        "source_files": ["app.py"], "editable_files": ["app.py"],
        "entrypoint": "app.py", "max_attempts": 1,
        "agent_timeout_s": 10, "case_timeout_s": 5,
        "cases": [{"id": "ONE", "args": [], "exit_code": 0, "stdout_json": 1}],
    }))
    gate = Gate.initialize(tmp_path / "control", source, spec_path)
    run = gate.prepare()
    report = gate.evaluate(run, backend, measure_only=True)
    assert report["status"] == "review" and report["cases"][0]["passed"] is True
    assert report["boundary"]["file_boundary_verified"] is True
    assert report["boundary"]["verified"] is False
    with pytest.raises(Refused):
        gate.accept(run)
    assert len(seen) == 2
    for argv in seen:
        joined = " ".join(argv)
        assert "--network none" in joined
        assert "--read-only" in joined
        assert "--cap-drop ALL" in joined
        assert "no-new-privileges" in joined
        assert "target=/src,readonly" in joined
        assert "target=/scratch" in joined
        assert "target=/csef-control" not in joined


def test_regular_mode_refuses_reviewed_executor():
    from csef_gate.__main__ import _executor
    with pytest.raises(Refused, match="requires --measure-only"):
        _executor("docker-reviewed", docker_image=IMAGE)
