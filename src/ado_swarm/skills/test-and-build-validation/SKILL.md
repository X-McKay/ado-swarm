---
name: test-and-build-validation
description: Use this skill when defining and interpreting the build/test/lint checks that must pass before a remediation is considered safe to ship.
allowed-tools: propose_validation_checks assess_readiness verify_file_location graphiti_search
metadata:
  pack: validation-submission
  maturity: base
---
# test-and-build-validation

## Objective

Ensure the remediated working copy still builds, passes its test suite, and lints cleanly — the
functional-regression governor that runs alongside security verification.

## When to use

After a fix is applied and security-verified, before readiness/PR. Distinct from
`security-fix-verification` (which proves the vuln is closed); this proves nothing else broke.

## Inputs

- `repository_evidence.repository` (to infer toolchain) and `execution.changed_files`.
- Any existing `validation.recommended_checks` for the finding.

## Procedure

1. Infer the project's commands from the repo manifest (`npm test`/`build`, `uv run pytest`,
   `mvn verify`, `go build ./...`, `terraform validate` for IaC).
2. Call `propose_validation_checks` to record the exact gating commands and their rationale.
3. Scope tests to the impacted area when possible, but always include the full build + lint.
4. Interpret results deterministically: a non-zero exit, failing test, or lint error is a HARD
   block — never explain away a failure.
5. `assess_readiness` only after collecting outcomes; surface failures as `blocking_reasons`.

## Decision criteria

- PASS requires: build succeeds, relevant + regression tests pass, lint/format clean.
- Flaky or pre-existing failures must be identified explicitly, not assumed.

## Checklist

- [ ] Build/compile succeeds on the patched tree.
- [ ] Test suite (at least impacted + smoke) green.
- [ ] Linter/formatter clean.
- [ ] For IaC: provider `validate`/`plan` succeeds with no new drift.

## Output expectations

`validation.recommended_checks` (commands + rationale) and outcomes feeding `readiness`.

## Safety

Validation is a governor; the model does not declare success without actual passing results.
Run checks only in the sandbox; never deploy or run against production resources.

## Escalation

Genuine failures caused by the fix, or inability to run the toolchain → block readiness and
escalate to `needs_human`.
