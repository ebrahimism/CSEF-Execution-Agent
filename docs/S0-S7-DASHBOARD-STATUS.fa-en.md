# CSEF — S0–S7 dashboard observability and visual QA

This change extends the existing local single-owner dashboard, rather than creating a competing control plane. It intentionally does **not** pretend to complete S3/S4/S5/S7.

## Source and authority

- Owner goal: \`docs/architecture/OWNER-SOFTWARE-FACTORY-v1.fa.md\` and \`docs/roadmap/ACTIVE-EXECUTION-v1.fa.md\`.
- ProjectBook: owner revision, questions, stage progression, model calls.
- \`factory\`: proposed dependency graph and task intent/outcome ledger.
- \`Gate\`: independent acceptance spec, runs, attempts, evaluation records and checkpoint. The UI **never** accepts a run or creates checkpoints.
- \`providers.usage\`: optional provider call-count accounting from the same SQLite.
- Delivery package: not tracked in the control store, so the UI says **unknown** even if an accepted checkpoint exists. Deployment is never inferred from a source snapshot.
- S4: independent VM execution boundary remains unverified. Docker reviewed-only is a REVIEW backend, not a release gate. The UI shows S4/S5 as blocked and S7 as unverified.

## New read-only endpoints

\`\`\`
GET /api/projects/{slug}/inspection
GET /api/projects/{slug}/runs/{run-id}
\`\`\`

They preserve loopback Host/Origin protections, the same CSP, zero exposure of full untrusted run stdout/stderr or candidate source, and bounded row counts. Run detail shows sanitized case results, integrity check and whether a checkpoint is credible. A tampered report is never presented as verified. There are no new POST endpoints capable of build/resume/accept/release.

If a user needs to execute a task or resume interrupted work, the existing Gate/Factory controller must be used in its separately authorized execution environment. The UI reports inability to resume automatically where reconciliation is needed.

## Visual testing

A browser workflow runs actual headless Chromium, **not just HTML string checks**, on Ubuntu CI. It verifies rendered FA RTL and EN LTR, 1440×900 desktop and 390×844 mobile, real Graph DOM nodes and edges, all operations panels, absence of client JavaScript errors, absence of horizontal document overflow, and actual project creation. Four full-page screenshots are saved as GitHub Actions artifacts.

\`\`\`
python -m pip install -e .
python -m pip install playwright
python -m playwright install chromium
python tests/ui/visual_browser.py
\`\`\`

Visual CI does not establish professional aesthetic quality across every browser/device. Review its screenshots, accessibility, text truncation, color contrast and focus order manually before final sign-off. No external model/API calls occur in visual CI.

## Remaining acceptance

- S3: trusted task-by-task acceptance and reconciliation-safe resume are not delivered by UI observability.
- S4: independently proven isolated guest not present.
- S5: an independent Gate-backed package receipt and authorization workflow not in DB.
- S7: build and deploy a complete real web app with installation tests; not yet proven.
- Real owner-credentialed S2 smoke testing is still required.
- Remote hosting is deliberately out of scope; never expose 127.0.0.1 dashboard via reverse proxy.
