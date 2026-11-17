# Direct API providers — pre-release

This feature branch implements two distinct direct HTTP model protocols:
OpenAI Responses and Anthropic Messages. It does not claim an autonomous
production coding/release agent, verified paid API operation or lower costs.

## Trust boundaries

- DirectAPI.call implements the existing structured client.call contract.
- DirectAPIAgent.propose implements the existing Gate agent.propose contract.
- The controller records calls and attempts before external requests, validates
  strict JSON and schemas, and owns source scope and acceptance.
- Provider and model are explicit. Codex remains an optional legacy adapter
  selected with --provider codex, never a default. CSEF can create projects,
  inspect project status and generate direct API coding proposals without Codex.
- Usage is recorded when reported. USD cost is unknown, never silently zero.
  No automatic retries or cross-provider fallback are performed.
- API keys come from OPENAI_API_KEY or ANTHROPIC_API_KEY. They are sent in
  authenticated HTTPS headers but not included in saved receipts or injected
  into candidate-code executors. Project context goes to the selected API;
  exclude secrets and sensitive data.
- Invalid, refused, incomplete and schema-breaking model outputs are rejected.
  The existing durable intent system accounts for unknown results.

## Commands

Replace MODEL with a real enabled identifier for your provider. First configure
the corresponding environment variable privately.

    python -m csef_gate project assist --root WORK --stage discovery --provider openai --model MODEL

    python -m csef_gate project review --root WORK --stage architecture --proposal review.json --provider anthropic --model MODEL

    python -m csef_gate propose --control CONTROL --run-id RUN_ID --provider openai --model MODEL

    python -m csef_gate workflow continue --root WORK --steps 1 --provider anthropic --model MODEL

The workflow example deliberately runs only one document stage. Subsequent code
stages require an explicitly selected execution backend. An API call is not
proof that a proposed code change works.

## Execution without Codex — reviewed samples only

An optional --executor docker-reviewed backend provides no container network,
a read-only source bind mount, a writable scratch mount, limited resources,
dropped Linux capabilities and no-new-privileges. A Docker daemon and an
immutable, separately selected Python image digest are required.

    python -m csef_gate evaluate --control CONTROL --run-id RUN_ID --measure-only --executor docker-reviewed --docker-image python:3.11-slim@sha256:REAL_64_HEX_DIGEST

Replace the digest placeholder with a real verified image digest. A Docker
container is NOT the independent VM isolation boundary required for general
hostile-code execution. This backend deliberately reports verified=False
even if file/network checks pass; the Gate returns REVIEW, never PASS or a
release checkpoint. Use only with pre-reviewed, nonsensitive sample code.
If Docker or the probes are unavailable, execution fails closed.

## Outstanding acceptance requirements

1. Opt-in real API smoke runs using user-provided credentials, recording
   real usage, latency and schema validity without logging secrets.
2. Durable cross-provider resume and explicit reconciliation of unknown
   external outcomes (T008); no automatic unknown retry.
3. Trusted isolated VM guest ExecutionProvider with adversarial boundary
   validation before release authority can be granted.
4. Frozen-controller self-development of a scoped non-security component;
   immutable tests, separate candidate worktree, manual approval and PR.
5. Controlled cost/quality benchmark versus direct API use, including all
   generation, review, repair, testing and human intervention.

Contract tests in CI use scripted provider responses. They do not claim live
service availability or measured cost.
