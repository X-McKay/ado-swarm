---
name: fix-plan-generation
description: Use this skill when expanding a chosen remediation strategy into concrete, ordered, verifiable fix steps.
allowed-tools: propose_remediation_strategy propose_validation_checks verify_file_location
metadata:
  pack: planning
  maturity: base
---
# fix-plan-generation

## Objective

Turn the selected `remediation_plan.strategy` into an ordered, concrete, *verifiable*
`remediation_plan.steps` list that a human reviewer (or an approved write path) can execute
exactly. The plan describes the change; this pipeline is read-only and does not apply it.

## When to use

After remediation-strategy-selection sets `strategy`, and after (or alongside)
safe-change-boundary-definition bounds the files in scope.

## Inputs

- `remediation_plan`: `strategy`, `change_boundary`.
- `normalized_finding`: `file_path`, `line`, `package_name`, `category`, `cwe`.
- `repository_evidence` (confirm target files exist).

## Procedure

1. Re-confirm each target file with `verify_file_location` so steps reference real paths.
2. Decompose `strategy` into the minimal ordered actions, each naming a specific file/
   manifest and the exact edit (old -> new), e.g. "bump `requests` 2.19.1 -> 2.31.0 in
   `requirements.txt`".
3. Stay strictly inside `remediation_plan.change_boundary`; if a needed step falls outside
   it, stop and revise the boundary -- never silently widen scope.
4. Append validation steps from `propose_validation_checks`: build, targeted tests, the
   scanner re-run that should now clear the finding, and any regression checks.
5. Set `requires_human_approval` per risk/eligibility.

## Decision criteria

- Each step must be **atomic, ordered, and independently checkable** -- no "fix the
  vulnerability" hand-waving.
- Every code/config step names a concrete file inside `change_boundary` and the precise edit.
- The plan **must include verification**: how to confirm the fix works and that the original
  finding no longer reproduces.
- Prefer the fewest steps that fully resolve the `cwe`; do not bundle unrelated cleanup.
- For dependency bumps, include lockfile regeneration and the compatibility check.

## Output expectations

Populate `remediation_plan.steps` (ordered: edit steps then validation steps) and keep
`strategy`/`change_boundary` consistent with them. `requires_human_approval` reflects the
risk gate. When automation-eligible and approved, this plan backs a `draft_pr_created`
disposition.

## Escalation

- A required step falls outside the safe boundary, or no validation can prove the fix -> set
  `requires_human_approval = True` and route to `final_disposition = "needs_human"`.
- Any step whose exact edit is uncertain -> record it as an open question rather than
  fabricating a precise diff.
