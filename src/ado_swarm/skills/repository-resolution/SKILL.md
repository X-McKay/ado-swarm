---
name: repository-resolution
description: Resolve repository identity, provider metadata, default branch, clone URL, and relevant refs.
allowed-tools: provider_get_issue provider_get_repo_metadata casefile_read blackboard_append graphiti_search policy_check_action
metadata:
  pack: repository-investigation
  maturity: base
---
# repository-resolution

## Objective

Resolve repository identity, provider metadata, default branch, clone URL, and relevant refs.

## Required inputs

A canonical casefile or task context, provider metadata, available repository evidence, prior audit events, and applicable policy constraints.

## Procedure

1. Confirm that the task objective matches this skill and identify missing evidence.
2. Work only from canonical contracts and explicitly referenced evidence.
3. Request only tools allowed by the active runtime policy; `allowed-tools` is descriptive, not enforcement.
4. Produce structured, audit-friendly output with confidence, rationale, evidence references, and stop conditions.
5. Escalate rather than guess when evidence is missing, ambiguous, sensitive, or outside the safe change boundary.

## Output expectations

Return concise findings suitable for inclusion in `AgentResult`, casefile sections, and task audit events. Include activated skill name `repository-resolution` in audit metadata.
