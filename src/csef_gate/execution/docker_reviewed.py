"""Limited Docker reviewed-execution backend, *never* a trusted release sandbox.

Intentionally reports verified=False even if observed probes pass: a container
is not the dedicated isolated guest required for general hostile-code release.
It is usable only with Gate.evaluate(..., measure_only=True), producing REVIEW.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import socket
import subprocess
import sys
import uuid
from pathlib import Path

from ..backends import capture, environment
from ..core import Refused, digest, encoded, manifest, plain

PROBE = """import json,pathlib,socket,sys
p=pathlib.Path(sys.argv[1]); s=pathlib.Path('/scratch'); port=int(sys.argv[2])
out={}
out['source_read']=p.is_file() and len(p.read_bytes())>=0
try:
 q=s/'csef-probe';q.write_text('ok');out['scratch_write']=q.read_text()=='ok'
except OSError:out['scratch_write']=False
try:p.write_text('attack');out['source_write_denied']=False
except OSError:out['source_write_denied']=True
out['control_absent']=not pathlib.Path('/csef-control').exists()
try:
 c=socket.create_connection(('127.0.0.1',port),timeout=1);c.close();out['host_loopback_denied']=False
except OSError:out['host_loopback_denied']=True
print(json.dumps(out))
"""


class DockerReviewedExecutor:
    """Non-Codex *review-only* execution; no production isolation claim."""

    def __init__(self, *, image: str, docker: str | None = None, runner=None):
        if not isinstance(image, str) or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._:/-]*@sha256:[a-f0-9]{64}", image):
            raise Refused("Docker reviewed execution requires an immutable image@sha256:digest")
        self.docker = docker or shutil.which("docker")
        if not self.docker:
            raise Refused("Docker is not installed; no unsafe host fallback")
        self.image = image
        self._run = runner or capture

    def _command(self, snapshot: Path, scratch: Path, arguments: list[str], timeout: int):
        plain(snapshot)
        plain(scratch)
        if not snapshot.is_dir() or not scratch.is_dir():
            raise Refused("Docker execution directories not available")
        name = "csef-reviewed-" + uuid.uuid4().hex
        uid = str(os.getuid()) + ":" + str(os.getgid()) if os.name != "nt" else "65534:65534"
        argv = [self.docker, "run", "--rm", "--name", name,
                "--network", "none", "--ipc", "none",
                "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
                "--read-only", "--pids-limit", "64", "--memory", "512m", "--cpus", "1",
                "--user", uid, "--tmpfs", "/tmp:rw,nosuid,noexec,size=16m",
                "--mount", "type=bind,source=" + str(snapshot.resolve()) + ",target=/src,readonly",
                "--mount", "type=bind,source=" + str(scratch.resolve()) + ",target=/scratch",
                "--workdir", "/scratch", "--entrypoint", "python",
                self.image, "-I", "-S", "-X", "utf8", *arguments]
        try:
            result = self._run(argv, cwd=scratch, env=environment(), timeout=timeout, limit=256_000)
            result["command_sha256"] = digest(encoded(argv))
            return result
        finally:
            # Also terminate the container if the docker client was killed on timeout.
            # A missing/already removed container is expected after successful --rm.
            subprocess.run([self.docker, "rm", "-f", name], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=10, check=False)

    def probe(self, *, snapshot: Path, scratch: Path, control: Path) -> dict:
        source_files = sorted(p for p in snapshot.rglob("*") if p.is_file())
        if not source_files:
            raise Refused("empty Docker execution snapshot")
        first = source_files[0].relative_to(snapshot).as_posix()
        listener = socket.socket()
        try:
            listener.bind(("127.0.0.1", 0))
            listener.listen(1)
            port = listener.getsockname()[1]
            result = self._command(snapshot, scratch, ["-c", PROBE, "/src/" + first, str(port)], 30)
        finally:
            listener.close()
        try:
            checks = json.loads(result["stdout"])
        except (ValueError, TypeError):
            checks = {}
        required = {"source_read", "scratch_write", "source_write_denied", "control_absent", "host_loopback_denied"}
        complete = (result["exit_code"] == 0 and not result["timed_out"] and not result["overflow"]
                    and isinstance(checks, dict) and set(checks) == required)
        files_ok = complete and all(checks.get(k) is True for k in required - {"host_loopback_denied"})
        return {
            "backend": "docker-reviewed-only",
            "verified": False,  # Deliberate: this backend cannot mint a PASS/checkpoint.
            "file_boundary_verified": files_ok,
            "network_isolation_verified": complete and checks.get("host_loopback_denied") is True,
            "checks": checks, "process": result,
            "scope": "local reviewed samples only; no release or hostile-code guarantee",
        }

    def run(self, *, snapshot: Path, scratch: Path, control: Path,
            entrypoint: str, args: list[str], timeout: int) -> dict:
        files = [p.relative_to(snapshot).as_posix() for p in snapshot.rglob("*") if p.is_file()]
        before, _ = manifest(snapshot, files)
        from ..core import relative_name
        relative_name(entrypoint)
        arguments = [value.replace(str(scratch), "/scratch") for value in args]
        result = self._command(snapshot, scratch, ["/src/" + entrypoint, *arguments], timeout)
        after, _ = manifest(snapshot, files)
        if after != before:
            raise Refused("Docker source snapshot changed during execution")
        return result
