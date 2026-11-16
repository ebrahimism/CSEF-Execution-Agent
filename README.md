# CSEF — Execution Agent (Provider-Agnostic Migration)

**Status: source migration in progress; not a production release.**

CSEF is intended to be a provider-agnostic software engineering controller that persists project goals and accepted decisions, scopes coding proposals, independently evaluates real program behavior, and records verifiable evidence. It should accept coding/model providers through versioned contracts rather than require one vendor or a particular CLI.

## Current reality

This branch imports the tested historical code from [ebrahimism/csef-builder](https://github.com/ebrahimism/csef-builder) at pinned source commit `87eae612cd38a85fdaac095993d9b9adc370da32`. See [migration provenance](docs/MIGRATION-PROVENANCE.md) and the untouched [source README](docs/SOURCE-README.md).

- **Reused, not rebuilt:** independent Gate, strict JSON/scope verification, project context, lifecycle/requirements/questions, SQLite persistence/migration, event journal, leases, stage workflow, tests, examples and historical evidence.
- **Previously tested in source:** the source ledger reports T001–T007 complete and 237 tests passing. **These results are historical and must be rerun in this repository; they do not certify this branch.**
- **Current coupling:** `model_session.CodexJSON`, `backends.CodexAgent`, `backends.CodexSandbox`, and CLI defaults use installed Codex. This migration has **not yet removed** that runtime requirement.
- **Security:** the native Windows sandbox previously failed the local TCP isolation probe. Normal runs block; `--measure-only` remains REVIEW with no checkpoint. No arbitrary untrusted execution, deployment, or self-promotion is authorized.
- **Not yet established:** direct two-provider API integration, complete resume at all interruption boundaries, real independent guest isolation, production packaging, and verified savings from decomposing tasks.

## Roadmap (incremental; preserve tested behavior)

1. **Freeze and verify:** preserve pinned provenance, rerun the baseline suite and publish a destination-specific test receipt. Maintain no-op compatibility while changing provider interfaces.
2. **Provider independence:** extract minimal `ModelProvider` / `CodingAgent` contracts, keep Codex as an *optional* adapter, and add two independent direct API adapters; record schema/usage/error/capability receipts and fail closed for unsupported features.
3. **Safe continuation:** complete unknown-outcome reconciliation (T008); never auto-retry irreversible external effects; keep verified source hashes, decision versions and budgets.
4. **Independent execution:** implement guest isolation and negative probes before granting PASS. A model or fixture cannot assert its own isolation.
5. **First self-development:** a frozen controller proposes a small, non-security change to a separate candidate version of CSEF, evaluates against protected tests, and submits a human-reviewable PR. Never auto-merge/auto-promote the controller being tested.
6. **Economics benchmark:** compare direct cheap models, structured CSEF decomposition with the same model, and a strong direct baseline on the same frozen problems and acceptance oracle. Report all generation/review/repair/infrastructure costs and final holdout quality.

Tracking: [Bootstrap implementation task](https://github.com/ebrahimism/CSEF-Execution-Agent/issues/1).

## Developer setup for the imported baseline

Python 3.11+ and a Python environment with project dependencies are required. Install `pytest` for tests. From the repository root:

```bash
python -m pip install -e .
python -m pip install pytest
python -m pytest -o addopts='' -q tests
```

These commands are instructions, not a claim that tests have been run here. The historical Codex-backed live workflow needs Codex CLI and authentication; offline ProjectBook operations and scripted tests do not imply live provider independence.

## Engineering rules

Keep accepted project facts and authority separate from model output; preserve strict negative tests; apply changes only to authorized, version-bound file sets; keep provenance for every imported record; avoid unnecessary new services/databases; prefer standard Python and SQLite until a measured requirement justifies more. All security-sensitive changes require independent review.
