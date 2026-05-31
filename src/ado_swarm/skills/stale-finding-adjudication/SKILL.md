---
name: stale-finding-adjudication
description: Use this skill when deciding whether a finding is stale because the code, file, line, or dependency it references no longer exists at the current ref.
allowed-tools: adjudication_signals verify_file_location graphiti_search
metadata:
  pack: adjudication
  maturity: base
---
# stale-finding-adjudication

## Objective

Decide whether the casefile's `normalized_finding` is *stale*: it points at code, a file,
a line, or a dependency that no longer exists at `repository_evidence.ref`. Stale means
real-but-obsolete (the issue was removed or moved). It is NOT the same as false-positive
(scanner was wrong about a still-present pattern) or duplicate (tracked elsewhere).

## When to use

The security_reviewer must populate `adjudication` and you suspect the referenced location
has changed since the scan ran.

## Inputs

- `normalized_finding`: `file_path`, `line`, `package_name`, `cwe`, `scanner`, `title`.
- `repository_evidence`: `repository`, `ref`, `file_exists`, `evidence`.

## Procedure

1. Call `verify_file_location` with `normalized_finding.file_path` (and `line`) against
   `repository_evidence.ref`; this sets/confirms `file_exists` and appends to `evidence`.
2. Call `adjudication_signals` to check whether the specific symbol/line/package the
   finding names is still present (line drift, deleted function, removed dependency).
3. If gone, optionally `graphiti_search` to confirm the code was intentionally removed
   (refactor/feature deletion) rather than relocated.
4. Write `FindingAdjudication`: set `stale`, `rationale`, `confidence`.

## Decision criteria

- `repository_evidence.file_exists is False` -> **stale** (confidence >= 0.8).
- File exists but `normalized_finding.line` no longer holds the flagged construct AND it is
  not found elsewhere in the file -> **stale**.
- `package_name` is no longer in the dependency manifest at `ref` -> **stale**.
- Code merely *moved* but still exists -> **not stale**; leave `stale=False` for normal
  triage / false-positive review.
- A present-but-harmless pattern is `false_positive`, not stale. Do not conflate them.

## Output expectations

Populate `adjudication` (`FindingAdjudication`): `stale=True/False`, `rationale` citing the
concrete evidence (path, ref, what was missing), `confidence`. Leave `duplicate_of`,
`false_positive`, `already_fixed` unset unless separately true. When stale with confidence,
the harness sets `final_disposition = "stale"`.

## Escalation

- If `file_exists is None` (could not verify) and you cannot otherwise confirm removal, do
  not assert `stale`; set low `confidence` so downstream sets `final_disposition = "needs_human"`.
- Conflicting signals (file present, line drifted, symbol ambiguous) -> `confidence <= 0.4`
  and prefer `needs_human` over a false stale disposition.
