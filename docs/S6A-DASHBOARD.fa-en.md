# S6a — Bilingual local dashboard / داشبورد محلی فارسی و انگلیسی

**وضعیت:** S6a UI prototype. This interface is an adapter, **not** a new authority, database or standalone execution engine.

## اجرای Windows PowerShell

From the root of \`ebrahimism/CSEF-Execution-Agent\`:

\`\`\`powershell
python -m pip install -e .
New-Item -ItemType Directory -Force -Path .\csef-workspace | Out-Null
python -m csef_gate.ui.server --workspace .\csef-workspace --port 8765
\`\`\`

Open **http://127.0.0.1:8765/** on the **same computer**. Click **EN / فا** at the top to switch English LTR / Persian RTL. The language choice stays in the browser.

## اجرای Linux / Ubuntu

\`\`\`bash
python3 -m pip install -e .
mkdir -p ./csef-workspace
python3 -m csef_gate.ui.server --workspace ./csef-workspace --port 8765
\`\`\`

**Do not expose port 8765 to the internet.** The server deliberately binds only to \`127.0.0.1\`, checks its Host and Origin, requires per-process CSRF tokens for writes, and does not support other hosts. Do not place it behind a public reverse proxy or port forward. There is **no multi-user authentication, remote access or TLS** in S6a.

## قابلیت‌های واقعی / What works

- Attractive dark, responsive UI with both Persian RTL and English LTR, language toggle, mobile layout and reduced-motion support; no CDN, external fonts, telemetry, React or npm build.
- Create an owner ProjectBook from a user-entered brief and a safe project slug. New projects are stored in the **existing SQLite** database.
- List and filter actual projects. See the recorded owner questions, live stage counts and proposed task count; do not confuse an incomplete graph with accepted execution.
- Display a dependency graph from the **existing stored factory plan**, including task IDs, file ownership, tests, acceptance notes and dependencies. Invalid/stale proposals do not appear as valid.
- Read-only architecture stage visualization marked partial/prototype/unverified as appropriate. No fictional completion percentages, revenue or release metrics.
- Display only whether provider API keys are configured, **not live provider availability**; no secrets are sent to the browser.
- Generate a plan through **the existing** \`factory.plan_brief\` + \`DirectAPI\` (OpenAI/Anthropic) only after explicitly selecting provider, model and accepting possible API charges for that call. This does **not** execute code.
- The Gate remains independent. The dashboard provides no endpoint to grant PASS, accept a checkpoint, deploy, bypass owner acceptance or directly modify SQLite.

## امنیت / Boundary

- HTTP server binds only to 127.0.0.1; exact Host/Origin checks and an unguessable in-memory CSRF token protect mutations from browser-origin attacks.
- CSP rejects inline scripts and third-party resources; all user/model content is rendered with DOM \`textContent\`, not HTML injection.
- Projects are limited to canonical ASCII slugs and a designated workspace; symlinks/reparse points are refused.
- Request bodies are bounded; credentials are not logged or shown; no public API key configuration is exposed.
- Plan requests are **potentially billable** and are explicit. A successful plan is still \`proposed\` and can contain unresolved questions.

## محدودیت‌های فعلی / Remaining work

- This is a **local single-owner** GUI, not a remote dashboard or live-chat service.
- Browsing projects, planning and the DAG work; running a build, accepting its Gate verdict, deployments, recovery and task-stage corrections are not yet permitted from this UI. Those require S3/S4 trust and integration work.
- The overview deliberately shows verified deliveries as **unknown**, rather than inventing PASS count.
- Browser visual QA across actual devices is still required; automated tests cover HTTP API and basic bilingual static assets, not screenshot-perfect visual rendering.
- The roadmap remains historically status-inconsistent with \`docs/roadmap/backlog.json\`. This UI labels roadmap milestones conservatively until an authoritative evidence-derived source is implemented.

## Tests

\`\`\`bash
python -m pytest -q tests/ui/test_dashboard.py
python -m pytest -o addopts='' -q tests
\`\`\`

The HTTP tests use an ephemeral loopback port and a scripted planner, not billable APIs. A green S6a CI run is evidence of local behavior and security checks, not remote-host security.
