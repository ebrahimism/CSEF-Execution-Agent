# DEC-004 — Internal software factory (owner decision)

Date: 2026-11-17. Status: owner direction recorded, not an automatic acceptance verdict.

CSEF is the owner's **private development tool**, not the product to sell.
It exists to turn plain-language briefs into complete, testable applications
for a low-capital software business.

Priority: reliable and complete deliverable; security and preservation of
owner requirements; minimal manual intervention; reuse open-source tools
where a tested integration exists; bounded and transparent total cost.
Being cheaper than one direct model invocation is NOT an acceptance condition.

Preserve the existing Gate, shared SQLite, ProjectBook, lifecycle, tests,
audit, permissions and resume controls. Reuse the existing Spec Kit bridge
for spec/plan/tasks before building new planning infrastructure.
Only the destination CSEF-Execution-Agent repository may be changed.
Older csef-builder and historical owner-goals/backlog/evidence are read-only.

Execution requires controlled independent verification. A model-generated
task graph is only a proposal: the owner must authorize material decisions;
only a trusted controller may produce PASS, checkpoints or deployment.
Do not run untrusted code without an independently verified isolation boundary.
Do not spend on API calls or deploy without explicit authorization.

This record documents the new owner intention without modifying prior
ProjectBook database revisions or asserting that release gates have passed.
Accepted requirements for each future user project must be versioned using
the existing ProjectBook lifecycle.

References: issue #6, issue #7, PR #8.
