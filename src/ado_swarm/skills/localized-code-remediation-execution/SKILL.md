---
name: localized-code-remediation-execution
description: Use this skill when remediating a SAST/source-code finding (category=sast) with a small, localized code edit inside an approved, sandboxed change boundary.
allowed-tools: resolve_repository verify_file_location propose_remediation_strategy apply_remediation_change graphiti_search
metadata:
  pack: remediation
  maturity: base
---
# localized-code-remediation-execution

## Objective

Fix a `normalized_finding.category == "sast"` weakness (injection, XSS, insecure
deserialization, weak crypto) with a single well-scoped source edit at the flagged location —
the smallest change that closes the `cwe` class without altering behavior elsewhere.

## When to use

The finding is a source-code weakness with a concrete `file_path`/`line` and a
`remediation_plan` describing a localized code change. Not for dependency/iac.

## Inputs

- `normalized_finding`: `cwe`, `file_path`, `line`, `title`.
- `remediation_plan`: `strategy` (the fix pattern), `change_boundary`, `steps`.
- Sandbox working copy root + `repository_evidence.repository`.

## Procedure

1. Verify the ToolContext is approved and `requires_human_approval` honored before any write.
2. `verify_file_location` on `file_path`; confirm it is listed in `change_boundary`.
3. Read the region around `line`; map the `cwe` to a concrete safe pattern (parameterized query
   for CWE-89, output encoding for CWE-79, constant-time compare, safe deserializer).
4. `graphiti_search` for the same CWE in this repo to reuse an accepted fix idiom.
5. Apply via `apply_remediation_change` with an exact `find`/`replace` touching only the
   vulnerable expression — preserve surrounding logic, signatures, and formatting.
6. Record the diff in `execution`.

## Decision criteria / Checklist

- [ ] Addresses the CWE root cause, not just the scanner's pattern match.
- [ ] No public API/signature change; no behavior change on valid inputs.
- [ ] Diff is small (~<15 lines) and confined to the flagged file(s).
- [ ] No new dependency introduced (that is a different skill).

## Output expectations

`ExecutionResult` with `applied=true` and `changed_files` strictly within `change_boundary`.

## Safety

`apply_remediation_change` is WRITE + approval-gated and sandbox-contained; it rejects paths
outside `change_boundary`. Never edit unapproved files or widen scope to "nearby cleanups".

## Escalation

Cross-module refactor, ambiguous root cause, or a test-breaking change required → leave
unapplied and route to `needs_human` via the readiness stage.
