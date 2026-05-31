---
name: pull-request-preparation
description: Use this skill when assembling a DRAFT pull request for a verified, validated remediation so a human can review and merge it.
allowed-tools: resolve_repository provider_get_repo_metadata summarize_findings graphiti_search
metadata:
  pack: validation-submission
  maturity: base
---
# pull-request-preparation

## Objective

Produce a clear, reviewable DRAFT pull request that packages a remediation whose diff has been
reviewed, security-verified, and test/build-validated — for human review, never auto-merge.

## When to use

The finding has a passing review, security verification, and validation, and
`readiness.ready == true`. Do not prepare a PR for unverified or blocked work.

## Inputs

- `normalized_finding`, `execution.diff_summary`, `validation`, `readiness`.
- `repository_evidence.repository` and `provider_get_repo_metadata` (default branch, conventions, labels).

## Procedure

1. Confirm upstream gates are green (review approved, verification passed, `validation` clean,
   `readiness.ready`). If any gate is unmet, do not draft a PR.
2. `resolve_repository` + `provider_get_repo_metadata` to get the base (default) branch and
   naming/label conventions.
3. Compose a branch name like `remediation/<finding_id>-<short-slug>`.
4. Write a title referencing the finding and a body covering: the vulnerability
   (cwe/category/severity), the fix summary, evidence (scanner-clean + test/build results), and
   the change boundary. Use `summarize_findings` to keep multi-finding PRs coherent.
5. Apply security/triage labels per repo metadata.

## Decision criteria

- One logical remediation per PR; group only tightly related findings sharing a change boundary.
- The body must let a reviewer approve without re-deriving context — link all evidence.

## Checklist

- [ ] base = default branch; branch name unique and descriptive.
- [ ] Body cites verification + validation evidence (no unsupported "this is safe").
- [ ] Labels set; PR marked DRAFT.

## Output expectations

A pull-request draft (title, body, branch, base, labels); set `final_disposition` toward
`draft_pr_created`.

## Safety

Draft only — never merge, never enable auto-merge, never push without human review. Do not
include secrets or raw exploit payloads in the PR body.

## Escalation

Missing upstream evidence or conflicting branch state → do not draft; route to `needs_human`.
