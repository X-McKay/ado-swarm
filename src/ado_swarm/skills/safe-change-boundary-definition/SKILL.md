---
name: safe-change-boundary-definition
description: Use this skill when defining the minimal, safe set of files and lines a remediation is permitted to touch.
allowed-tools: propose_remediation_strategy verify_file_location provider_get_repo_metadata
metadata:
  pack: planning
  maturity: base
---
# safe-change-boundary-definition

## Objective

Define `remediation_plan.change_boundary`: the *minimal* explicit set of files, lines, and
config a fix may modify. The boundary is the contract for any approved write path -- anything
outside it requires human approval. Tight boundaries are what make automation safe.

## When to use

Alongside remediation-strategy-selection / fix-plan-generation, before any plan is treated as
automation-eligible or proposed as a draft PR.

## Inputs

- `normalized_finding`: `file_path`, `line`, `package_name`, `category`.
- `remediation_plan.strategy`.
- `risk`: `risk_level`, `automation_eligible`.
- Repo shape via `provider_get_repo_metadata`.

## Procedure

1. Start from the smallest unit the `strategy` needs: the specific manifest/lockfile for a
   dependency bump, the specific sink line(s) for a SAST fix, the specific config key for
   IaC/container.
2. Confirm each candidate path with `verify_file_location`.
3. Add only files *causally required* by the fix (e.g. a lockfile that must be regenerated
   when a manifest changes). Use `provider_get_repo_metadata` to detect ripple effects you
   must either include or escalate.
4. Write the boundary as an explicit, enumerable list -- never "the codebase" or a glob
   broader than necessary.

## Decision criteria

- **In scope**: the exact file(s)/line(s)/config keys the fix names, plus mechanically
  coupled artifacts (lockfile for a manifest bump, generated file from a regenerated source).
- **Out of scope (-> human approval)**: anything broader than the minimal set -- extra
  modules, public-API/interface signatures, build scripts, CI config, secrets, schema
  migrations, or "while we're here" edits.
- A boundary that cannot be enumerated as a concrete file/line set is **not safe** -> default
  to human approval.
- The narrower the boundary, the higher the confidence the change is automatable.

## Output expectations

Populate `remediation_plan.change_boundary` with the explicit list (files, and where useful,
line ranges/config keys). Keep it consistent with `remediation_plan.steps`. Set
`requires_human_approval = True` whenever the true minimal boundary exceeds what can be safely
auto-applied.

## Escalation

- If the fix genuinely must touch shared/critical-path code, public APIs, secrets, or
  migrations -> the boundary is unsafe to automate; set `requires_human_approval = True` and
  route to `final_disposition = "needs_human"`.
- If you cannot bound the change to a known file set, escalate rather than approximating.
