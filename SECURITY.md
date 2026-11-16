# Security Policy

## Current support status

**Pre-release migration only. No production-ready version is supported yet.** The imported CSEF gate is a limited local pilot, not a general secure execution environment.

The existing Windows-native Codex sandbox failed the localhost TCP isolation probe. Without a fully verified execution boundary, normal evaluation must fail closed as `BLOCKED`. The reviewed `--measure-only` mode returns `REVIEW`, never a checkpoint. Do not use it to run hostile/untrusted code, handle sensitive workloads, or authorize deployment.

## Reporting vulnerabilities

Open a private GitHub security advisory using the repository's **Security** tab and **Report a vulnerability** when available. If private reporting is unavailable, contact the maintainers through a trusted private channel rather than publishing exploit details, secrets or credentials in an issue.

## Security invariants

- The coding model proposes; only the trusted controller and independent verifier can authorize acceptance.
- Proposed code must not write controller state, policy, approval gates, or protected acceptance tests.
- Execution providers must prove the required isolation properties with positive and negative probes; unsupported environments fail closed.
- A result of unknown, timed out, incomplete, spoofed, stale or REVIEW is never a PASS.
- Any migration or restoration retains historical evidence but does not reuse stale acceptance authority.
- Do not log or commit API keys, authentication material, private application data or host secrets.

See [docs/GATE.md](docs/GATE.md) and [migration provenance](docs/MIGRATION-PROVENANCE.md).