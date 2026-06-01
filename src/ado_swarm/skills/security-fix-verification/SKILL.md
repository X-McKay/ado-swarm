---
name: security-fix-verification
description: Use this skill when verifying that an applied remediation actually closes the original vulnerability and does not reintroduce it, before declaring the finding fixed.
allowed-tools: propose_validation_checks score_severity adjudication_signals verify_file_location graphiti_search
metadata:
  pack: validation-submission
  maturity: base
---
# security-fix-verification

## Objective

Confirm, with evidence, that the change in `execution` eliminates the specific vulnerability in
`normalized_finding` — the security-correctness check, distinct from generic test/build.

## When to use

After a diff passes `remediation-diff-review`, prove the security property now holds.

## Inputs

- `normalized_finding`: `cwe`, `category`, `scanner`, `file_path`, `line`.
- `execution.diff_summary` and any existing `validation.recommended_checks`.

## Procedure

1. Restate the security property the fix must satisfy, derived from `cwe`/category
   (e.g. "user input is parameterized", "bucket is private", "package >= fixed version").
2. Call `propose_validation_checks` to enumerate concrete proofs — prefer re-running the
   originating `scanner` against the patched file plus a targeted negative test that the exploit
   path is closed.
3. Trace the diff to confirm the property holds at `file_path`:`line`.
4. Use `adjudication_signals` / `score_severity` to confirm residual severity dropped (ideally
   the finding no longer triggers; if it does, the fix is incomplete).
5. `graphiti_search` for how the same CWE was verified before to keep the bar consistent.

## Decision criteria

- VERIFIED only when the scanner no longer flags the finding AND a behavioral check shows the
  unsafe path is closed. A clean diff alone is insufficient.
- If the scanner still fires or the property can't be demonstrated, mark NOT verified.

## Checklist

- [ ] Originating scanner re-run shows the finding cleared.
- [ ] Negative/exploit test demonstrates closure.
- [ ] No equivalent variant of the bug remains nearby.

## Output expectations

Evidence references feeding `validation.recommended_checks` and the `readiness` decision.

## Safety

Verification is a governor: the model never self-certifies. Without passing scanner + check
evidence the fix is not "verified".

## Escalation

Scanner still flags, property undemonstrable, or partial fix → route to `needs_human`.
