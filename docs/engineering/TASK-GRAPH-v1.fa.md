# S1 — Draft a software task graph from an owner brief

This is a proposal/validation tool, NOT automatic execution or PASS authority.
It uses existing ProjectBook, SQLite changes and Spec Kit exchange; no new
database, queue or model gateway.

## Offline demonstration (no Codex or API keys)

Install this project with Python 3.11+:

    python -m pip install -e .
    python -m csef_gate project init --root WORK --goal "Build a store stock and order app" --brief examples/task_graph/brief.json
    python -m csef_gate project plan --root WORK --proposal examples/task_graph/plan.json --version 1
    python -m csef_gate project plan-status --root WORK

WORK must not already exist. The sample plan is manually prewritten to
demonstrate validation and storage only; no AI-generated planning is claimed.

## Optional model planning (potentially billed)

    python -m csef_gate project plan --root WORK --provider openai --model YOUR_ENABLED_MODEL

or:

    python -m csef_gate project plan --root WORK --provider anthropic --model YOUR_ENABLED_MODEL

Requires OPENAI_API_KEY or ANTHROPIC_API_KEY set locally. Never put keys in
GitHub, model prompts, sample fixtures or chat. An imported Spec Kit
spec/plan/tasks draft for the SAME owner revision is used as untrusted reference
data. The client is explicit and will not silently fall back.

## Structural validation

Tasks must have ID, kind, accepted fact IDs and GOAL coverage, dependencies,
scope, inputs, outputs, acceptance tests and writable file inventory.
Missing accepted facts, cycles, unknown dependencies, competing independent
file writers, disconnected work, no integration, or no final delivery are
refused. Exactly one final delivery task is required; all tasks lead to it.

The controller binds the proposal to the owner version + hash, rechecks inside
a SQLite transaction, deduplicates retries and never mutates accepted facts.
A concurrent owner change invalidates an old draft. Calls reserve the existing
budget before contacting an API; unknown outcomes are not retried automatically.

This is only structural assurance. Semantic adequacy, execution of code,
safe sandboxing, whole-app testing and deployment are separate later gates.
A model proposal and a checkbox cannot create a Gate checkpoint.
