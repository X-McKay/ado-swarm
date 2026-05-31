---
name: dependency-remediation-execution
description: Use this skill when remediating a vulnerable third-party dependency (finding category=dependency) by bumping a package version inside an approved, sandboxed change boundary.
allowed-tools: resolve_repository verify_file_location propose_remediation_strategy apply_remediation_change graphiti_search
metadata:
  pack: remediation
  maturity: base
---
# dependency-remediation-execution

## Objective

Resolve a `normalized_finding.category == "dependency"` finding by upgrading the offending
package (`normalized_finding.package_name`) to the nearest non-vulnerable version with the
smallest possible blast radius — a manifest/lockfile edit only, never a code refactor.

## When to use

The finding's category is `dependency` and `remediation_plan.strategy` describes a version
bump. Do NOT use this for sast/iac findings.

## Inputs

- `normalized_finding`: `package_name`, `severity`, `cwe`, `file_path` (the manifest).
- `remediation_plan`: `strategy`, `change_boundary`, `steps`, `requires_human_approval`.
- `repository_evidence.repository` and the sandbox working copy root.

## Procedure

1. Confirm `remediation_plan.requires_human_approval` is satisfied — the ToolContext must be
   approved (`constraints["approved"]`) before any write. If unapproved, stop and emit no change.
2. Call `resolve_repository` / `verify_file_location` to confirm the manifest path
   (`package.json`, `requirements.txt`, `pom.xml`, `go.mod`) exists and is within `change_boundary`.
3. Use `graphiti_search` for prior bumps of the same `package_name` to reuse a known-good target.
4. Pick the minimum fixed version (advisory/CWE-driven), preferring patch/minor over major.
5. For each in-boundary file only, call `apply_remediation_change` with an exact `find`/`replace`
   on the version pin; update the matching lockfile entry if it is in the boundary.
6. Record the diff in `execution` (`changed_files`, `diff_summary`, `applied=true`).

## Decision criteria

- Prefer the lowest version that clears the advisory; avoid major bumps unless required.
- A major bump with breaking API changes is no longer "dependency-only" — escalate.
- If no upstream fixed version exists, do not invent one.

## Checklist

- [ ] ToolContext approved before any `apply_remediation_change`.
- [ ] `changed_files` limited to manifest (+ lockfile), all within `change_boundary`.
- [ ] Diff touches only version strings.

## Output expectations

`ExecutionResult` with `applied=true`, a minimal `diff_summary`, and `sandbox_session_id` set.

## Safety

- `apply_remediation_change` is a WRITE tool: approval-gated and sandbox-bounded; it refuses
  out-of-boundary or out-of-sandbox paths. No hand-editing of vendored/transitive code, no
  scope creep into source files.

## Escalation

Major breaking bump, missing upstream fix, or lockfile conflict → leave unapplied and set
`readiness.blocking_reasons`, routing to `needs_human`.
