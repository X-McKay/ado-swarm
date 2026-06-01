---
name: ticket-disposition-update
description: Use this skill when setting the final disposition of a finding (open/stale/duplicate/false_positive/needs_human/draft_pr_created/ready_for_review/closed_with_evidence) with supporting evidence.
allowed-tools: assess_readiness summarize_findings provider_get_issue provider_search_issues graphiti_add_episode
metadata:
  pack: validation-submission
  maturity: base
---
# ticket-disposition-update

## Objective

Assign the correct terminal `final_disposition` to the casefile and attach the evidence that
justifies it, so the source-of-record ticket reflects an auditable outcome.

## When to use

At the end of a finding's lifecycle, once readiness/verification/PR stages have produced an outcome.

## Inputs

- `readiness`, `adjudication`, `validation`, `execution`, and `normalized_finding`.
- `source_issue` (the provider work item).

## Procedure

1. `assess_readiness` (or read existing `readiness`) for the gating outcome and blockers.
2. Map outcome to the disposition vocabulary:
   - `false_positive` — `adjudication.false_positive` with rationale and signals.
   - `duplicate` — `provider_search_issues`/`adjudication.duplicate_of` finds the same root cause.
   - `stale` — `adjudication.stale`; finding no longer present in current code.
   - `draft_pr_created` — a draft PR exists awaiting review.
   - `ready_for_review` — fix verified + validated, queued for human review.
   - `closed_with_evidence` — fix merged/confirmed with scanner-clean evidence.
   - `needs_human` — blocked, ambiguous, or high-risk.
   - `open` — nothing actionable yet (default).
3. Collect evidence refs (PR link, scanner output, validation results, duplicate ticket id).
4. `provider_get_issue` to align with the existing ticket; record an episode via `graphiti_add_episode`.

## Decision criteria / Checklist

- [ ] `final_disposition` is exactly one value from the allowed vocabulary.
- [ ] `closed_with_evidence` requires concrete passing evidence, not assertion.
- [ ] `needs_human` chosen whenever confidence is low or risk is high.

## Output expectations

`final_disposition` set with evidence references recorded in `audit` / a knowledge episode.

## Safety

Read-only against the provider here (get/search). Do not auto-close without evidence; never
downgrade to `false_positive`/`closed_with_evidence` to clear backlog without proof.

## Escalation

Conflicting signals or insufficient evidence → `needs_human` with notes.
