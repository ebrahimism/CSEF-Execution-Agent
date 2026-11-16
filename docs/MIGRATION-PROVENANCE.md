# Pinned source migration — CSEF Execution Agent

**Source:** https://github.com/ebrahimism/csef-builder  
**Pinned source commit:** `87eae612cd38a85fdaac095993d9b9adc370da32`  
**Destination:** https://github.com/ebrahimism/CSEF-Execution-Agent  
**Migration branch:** `migration/provider-agnostic-bootstrap`

## Inventory verification

The complete source Git tree had **247 regular files**. The destination migration branch was inspected after import: **247/247 source paths were present and every corresponding Git blob SHA matched** the source tree at the pinned commit. The destination's pre-existing `LICENSE` (Apache-2.0) and `SECURITY.md` were preserved during import. Its README is updated to clarify the new direction, while the original README is preserved byte-for-byte as `docs/SOURCE-README.md`.

The imported files include `src/`, `tests/`, `schemas/`, `examples/`, `compatibility/`, `verification_step5/`, `experiments/`, `integrations/`, `plugins/`, `tools/`, and all historical `docs/` files. Prior Codex tooling is retained as an optional future adapter candidate, **not claimed independent today**.

## Evidence and limitations

- Historical reports in `docs/progress/` report T001–T007 completed and 237 repository tests passing at T007.
- The migration verified file identity, **not** execution of the destination test suite, live API compatibility, sandbox isolation or independent release authorization.
- Historical reports are not rewritten or promoted to new project acceptance records. Their names, source hashes and claims remain historical.
- The existing control layer still uses Codex in CLI/model/execution integration. No claim of live provider-agnostic operation is made by transferring code.
- The Windows host network boundary remains unverified; `--measure-only` reports REVIEW and never issues checkpoints.
- The old repository remains unchanged. The new branch can be discarded without losing any original work.

## Next proof

Rerun repository tests on a pinned destination commit, separate provider contracts from Codex, introduce two direct API adapters with independent integration tests, finish resume/reconciliation, validate an isolated execution guest, and then let a frozen controller create a scoped PR against a candidate copy of CSEF. Compare end-to-end cost/quality against direct model execution rather than equate task count with savings.

See https://github.com/ebrahimism/CSEF-Execution-Agent/issues/1 for acceptance requirements.
