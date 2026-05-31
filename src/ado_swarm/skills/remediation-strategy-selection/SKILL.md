---
name: remediation-strategy-selection
description: Use this skill when choosing the high-level remediation strategy (the fix approach) for a confirmed finding.
allowed-tools: propose_remediation_strategy propose_validation_checks graphiti_search
metadata:
  pack: planning
  maturity: base
---
# remediation-strategy-selection

## Objective

Choose the single best high-level *strategy* to remediate a confirmed finding and record it
in `remediation_plan.strategy`. This is the "what approach" decision; the step-by-step "how"
belongs to the fix-plan-generation skill.

## When to use

The solutions_architect must populate `remediation_plan` for a real, risk-scored finding.
Run before drafting concrete steps.

## Inputs

- `normalized_finding`: `category`, `cwe`, `package_name`, `file_path`, `severity`.
- `risk`: `risk_level`, `automation_eligible`, `impact`.

## Procedure

1. Call `propose_remediation_strategy` with the finding + `risk` to get candidate approaches
   keyed by `normalized_finding.category`.
2. Optionally `graphiti_search` for how the same CWE/package was remediated before (proven
   canonical fixes beat novel ones).
3. Prefer the **most direct, smallest, reversible** strategy that fully addresses the
   `cwe`/root cause -- not just the symptom.
4. Sketch validation via `propose_validation_checks` so the choice is testable.
5. Record `strategy` and set `requires_human_approval` per risk.

## Decision criteria

Map category/CWE to strategy:
- **dependency**: upgrade to the lowest fixed version within a compatible range; prefer
  patch/minor over breaking major; if no compatible fix exists, propose pinning + a
  documented mitigation/exception.
- **secret**: rotate/revoke the credential and remove it from source + history; replace with
  a secrets-manager reference -- never just delete the line.
- **sast (injection/XSS/etc.)**: apply the canonical mitigation (parameterized query, output
  encoding, safe API) at the sink; avoid bespoke sanitizers.
- **iac/container**: correct the misconfiguration to the secure baseline (least privilege,
  pinned base image, disabled risky flag).
- Choose the strategy with the smallest `change_boundary` that still fixes the root cause;
  reject broad refactors when a contained fix exists.

## Output expectations

Populate `remediation_plan.strategy` (one clear phrase) and set `requires_human_approval`
(True for high/critical or non-automation-eligible). Leave detailed `steps` and final
`change_boundary` to fix-plan-generation and safe-change-boundary-definition.

## Escalation

- No safe/compatible fix (e.g. dependency with no fixed version) -> propose a documented
  mitigation/exception, set `requires_human_approval = True`, and route to
  `final_disposition = "needs_human"`.
- Multiple viable strategies with materially different risk -> escalate rather than silently
  picking.
