from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .core import Gate, Refused, read_json


def _executor(kind, *, measure_only=False, docker_image=None):
    if kind == "codex":
        from .backends import CodexSandbox
        return CodexSandbox()
    if kind == "docker-reviewed":
        if not measure_only:
            raise Refused("Docker reviewed executor requires --measure-only")
        from .execution.docker_reviewed import DockerReviewedExecutor
        return DockerReviewedExecutor(image=docker_image)
    raise Refused("choose an explicit --executor; no unsandboxed host fallback")


def main(argv=None):
    p = argparse.ArgumentParser(description="CSEF: independent model proposals and black-box acceptance")
    sub = p.add_subparsers(dest="command", required=True)
    from .project_cli import configure
    configure(sub)
    from .interfaces.cli import configure as configure_workflow
    configure_workflow(sub)
    init = sub.add_parser("init")
    init.add_argument("--control", type=Path, required=True)
    init.add_argument("--project", type=Path, required=True)
    init.add_argument("--spec", type=Path, required=True)
    for name in ("prepare", "evaluate", "accept", "run", "propose", "apply"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--control", type=Path, required=True)
        if name not in ("prepare", "run"):
            cmd.add_argument("--run-id", required=True)
        elif name == "run":
            cmd.add_argument("--run-id", help="resume unaccepted run, persistent attempt budget")
        if name in ("evaluate", "run"):
            cmd.add_argument("--measure-only", action="store_true")
            cmd.add_argument("--executor", choices=("codex", "docker-reviewed"))
            cmd.add_argument("--docker-image", help="immutable image@sha256:digest for Docker reviewed mode")
        if name in ("run", "propose"):
            cmd.add_argument("--provider", choices=("openai", "anthropic", "codex"))
            cmd.add_argument("--model", help="required with direct APIs")
        if name == "apply":
            cmd.add_argument("--proposal", type=Path, required=True)
    args = p.parse_args(argv)
    try:
        if args.command == "workflow":
            from .interfaces.cli import execute
            result = execute(args)
        elif args.command == "project":
            from .project_cli import execute
            result = execute(args)
        elif args.command == "init":
            Gate.initialize(args.control, args.project, args.spec)
            result = {"status": "initialized", "control": str(args.control)}
        else:
            gate = Gate(args.control)
            if args.command == "prepare":
                result = {"run_id": gate.prepare()}
            elif args.command == "apply":
                gate.apply_proposal(args.run_id, read_json(args.proposal))
                result = {"status": "prepared", "run_id": args.run_id}
            elif args.command == "evaluate":
                result = gate.evaluate(args.run_id, _executor(args.executor, measure_only=args.measure_only, docker_image=args.docker_image), measure_only=args.measure_only)
            elif args.command == "accept":
                result = {"status": "accepted", "checkpoint": gate.accept(args.run_id)}
            elif args.command == "propose":
                from .providers.direct import select_provider
                _, agent = select_provider(args.provider, args.model)
                result = gate.agent_attempt(args.run_id, agent)
            else:
                from .providers.direct import select_provider
                _, agent = select_provider(args.provider, args.model)
                executor = _executor(args.executor, measure_only=args.measure_only, docker_image=args.docker_image)
                def progress(report):
                    print(json.dumps({"run_id": report["run_id"], "evaluation_id": report["evaluation_id"], "status": report["status"], "passed": sum(c["passed"] for c in report["cases"]), "total": len(report["cases"]), "error": report["error"]}), file=sys.stderr, flush=True)
                result = gate.run(executor, agent, args.run_id, progress, measure_only=args.measure_only)
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 2 if result.get("status") in ("review", "awaiting_owner", "draft_requires_validation", "review_required", "needs_revision", "paused") else 1 if result.get("status") in ("fail", "blocked") else 0
    except (Refused, OSError, ValueError, KeyError) as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}, ensure_ascii=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
