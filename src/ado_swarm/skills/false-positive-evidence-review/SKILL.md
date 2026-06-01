---
name: false-positive-evidence-review
description: Use this skill when reviewing evidence to decide whether a finding is a false positive that is not actually exploitable or reachable.
allowed-tools: adjudication_signals verify_file_location graphiti_search
metadata:
  pack: adjudication
  maturity: base
---
# false-positive-evidence-review

## Objective

Decide whether the casefile's `normalized_finding` is a *false positive*: the flagged
pattern exists but is **not actually exploitable or reachable** (sanitized input, guarded
path, test-only code, a non-sink, or an inapplicable rule). Distinct from *stale* (code
removed) and *duplicate* (tracked elsewhere).

## When to use

`verify_file_location` confirms the code still exists, the finding is not a duplicate, and
you must judge whether the reported vulnerability is real before risk scoring.

## Inputs

- `normalized_finding`: `category`, `cwe`, `severity`, `file_path`, `line`, `scanner`,
  `confidence`.
- `repository_evidence`: `file_exists`, `evidence`.

## Procedure

1. Confirm the location is live with `verify_file_location` (do not mark FP on missing code
   -- that is stale).
2. Call `adjudication_signals` for reachability/exploitability context around
   `normalized_finding.line`: real sink? input sanitized/validated upstream? file is
   test/fixture/generated? rule applicable to this language/framework?
3. Use `graphiti_search` for prior adjudications of the same rule/CWE in this repo accepted
   as false positives (institutional memory).
4. Write `FindingAdjudication.false_positive` with a precise, evidence-backed rationale.

## Decision criteria

- **False positive** when ANY holds with clear evidence:
  - Tainted value is sanitized/escaped/parameterized before reaching the sink.
  - The flagged call is not a real sink here (constant argument, no untrusted input flows in).
  - Code is test-only, example, fixture, or generated and never ships/executes in prod.
  - The scanner rule does not apply to this language/framework/version.
- Low scanner `confidence` is a prompt to investigate, not by itself proof of FP.
- If exploitability is plausible or you cannot trace the data flow -> **not** false
  positive; leave it open for risk scoring.

## Output expectations

Populate `adjudication`: `false_positive=True/False`, `rationale` describing the specific
mitigating evidence (sanitizer location, why not a sink, test-only path), and `confidence`.
The harness sets `final_disposition = "false_positive"` when established with high confidence.

## Escalation

- Asserting false positive on a `high`/`critical` finding needs strong, specific evidence;
  if uncertain set `confidence <= 0.5` so downstream routes to `needs_human`.
- Cannot follow the data flow to a definite conclusion -> do not mark FP; let downstream set
  `final_disposition = "needs_human"`.
