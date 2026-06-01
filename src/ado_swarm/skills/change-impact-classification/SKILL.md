---
name: change-impact-classification
description: Use this skill when classifying the blast radius and disruption of a proposed remediation change.
allowed-tools: score_severity propose_remediation_strategy provider_get_repo_metadata
metadata:
  pack: risk-impact
  maturity: base
---
# change-impact-classification

## Objective

Classify the *impact of the fix itself* (not the vulnerability): how disruptive and how
wide-reaching the proposed remediation would be. This feeds `risk.impact` and informs both
automation eligibility and the safe change boundary.

## When to use

After a remediation direction exists (or is being proposed) and before deciding whether it
can be automated. Distinguishes a one-line dependency bump from a cross-cutting refactor.

## Inputs

- `normalized_finding`: `category`, `package_name`, `file_path`.
- `risk`: `risk_level` (vulnerability-severity context).
- `remediation_plan` (if drafted): `strategy`, `change_boundary`, `steps`.
- Repository shape via `provider_get_repo_metadata`.

## Procedure

1. Identify the change shape from `normalized_finding.category` and the candidate
   `strategy` (`propose_remediation_strategy`): dependency bump, config edit, localized
   code change, or broad refactor.
2. Estimate the surface: files/modules touched, public-API/interface changes, build or
   schema/migration changes, runtime-behavior changes.
3. Use `provider_get_repo_metadata` to gauge how widely the touched module is imported and
   whether it sits on a critical path (entry points, shared libs).
4. Pick an impact class and record the reasoning.

## Decision criteria

- **Contained / low-impact**: a single dependency bump within a compatible range, or a
  single-file localized edit with no public-API change and no migration.
- **Moderate impact**: multi-file but cohesive change, config/IaC change affecting one
  service, additive API change.
- **High / broad impact**: major-version dependency upgrade with breaking changes,
  cross-module refactor, public-API/interface change, schema migration, or anything
  touching shared/critical-path code.
- A change that *cannot be bounded to a known file set* is high-impact by default.

## Output expectations

Reflect the classification in `risk.impact` (and the `remediation_plan.change_boundary`
narrative): state the change shape, approximate surface, and breaking-change risk. This is
the evidence base the automation-eligibility and safe-change-boundary skills consume.

## Escalation

- Broad/high-impact changes, breaking upgrades, or shared/critical-path edits -> set
  `remediation_plan.requires_human_approval = True` and route to
  `final_disposition = "needs_human"`; never auto-apply.
- If the change surface cannot be estimated, treat as high-impact and escalate.
