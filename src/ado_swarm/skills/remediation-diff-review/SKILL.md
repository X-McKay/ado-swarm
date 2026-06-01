---
name: remediation-diff-review
description: Use this skill when reviewing an applied remediation diff for correctness, scope, and risk before it advances toward a pull request.
allowed-tools: verify_file_location score_severity adjudication_signals graphiti_search
metadata:
  pack: validation-submission
  maturity: base
---
# remediation-diff-review

## Objective

Act as a critical reviewer of the `execution` diff: confirm it actually fixes the finding,
stays within scope, and introduces no new risk — yielding an explicit approve/reject with
specific comments.

## When to use

`execution.applied == true` and the diff must be gated before validation/PR.

## Inputs

- `execution`: `diff_summary`, `changed_files`, `sandbox_session_id`.
- `normalized_finding` (cwe, category, file_path) and `remediation_plan.change_boundary`.

## Procedure

1. Cross-check every path in `execution.changed_files` against `remediation_plan.change_boundary`;
   `verify_file_location` to confirm files exist. Any out-of-boundary file is an automatic reject.
2. Read the diff hunk-by-hunk: does it address the `cwe` root cause, or merely silence the scanner?
3. Look for collateral edits (formatting churn, unrelated lines, commented-out code, secrets,
   debug statements) and flag each.
4. Use `adjudication_signals` / `score_severity` to sanity-check that residual risk is reduced.
5. `graphiti_search` for prior reviews of similar diffs to apply consistent standards.

## Decision criteria

- APPROVE only if in-boundary, minimal, root-cause-correct, behavior-preserving, no secrets.
- REJECT on scope creep, partial fix, likely regression, or a diff that doesn't map to the CWE.

## Checklist

- [ ] All `changed_files` within `change_boundary`.
- [ ] Diff size proportionate to the fix.
- [ ] No new secrets, no disabled checks, no `# nosec`/suppression hacks.

## Output expectations

A review verdict (approved bool + specific comments + risk flags) feeding the readiness stage.

## Safety

Read-only review — never edit the diff here; rejection routes back to the execution skill. The
model does not self-certify correctness; tests/build/scanners still govern downstream.

## Escalation

High-risk flags (auth, crypto, IAM, data handling) or uncertainty → reject and recommend
`needs_human`.
