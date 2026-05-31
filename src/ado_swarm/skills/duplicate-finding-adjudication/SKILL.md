---
name: duplicate-finding-adjudication
description: Use this skill when determining whether a finding duplicates one already tracked, and capturing the canonical finding id.
allowed-tools: adjudication_signals graphiti_search provider_search_issues
metadata:
  pack: adjudication
  maturity: base
---
# duplicate-finding-adjudication

## Objective

Determine whether the casefile's `normalized_finding` duplicates a finding already recorded
in the knowledge graph or issue tracker, and if so set `adjudication.duplicate_of` to the
canonical finding's id. Re-scans, per-branch runs, and overlapping scanners frequently emit
the same underlying issue more than once.

## When to use

The security_reviewer must populate `adjudication` for a finding that may already be tracked.

## Inputs

- `normalized_finding`: `finding_id`, `title`, `scanner`, `category`, `cwe`,
  `package_name`, `file_path`, `line`.
- `repository_evidence.repository`.

## Procedure

1. Build a fingerprint from the most stable identity dimensions, in priority order:
   (`cwe` + `file_path` + nearby `line`), then (`category` + `package_name`), then
   (normalized `title` + `scanner`).
2. Call `graphiti_search` with that fingerprint to retrieve prior findings/episodes for the
   same repository. Prefer `cwe`/`package_name`/`file_path` matches over title matches.
3. If the graph is sparse, call `provider_search_issues` for an existing tracked issue
   covering the same location/CWE/package.
4. Call `adjudication_signals` to compare candidates (same sink, package range, file region).
5. Pick the earliest/canonical match; set `duplicate_of` to its `finding_id`.

## Decision criteria

- **Duplicate** when a prior finding shares the same `cwe` AND the same `file_path` within a
  small line window, OR the same `cwe` AND same `package_name`.
- Cross-scanner matches (two SAST tools, same CWE + same sink line) -> duplicate; keep the
  earliest as canonical and point the current at it.
- Same file/package but **different CWE or different sink** -> NOT a duplicate.
- Never set `duplicate_of` to the finding's own `finding_id`.

## Output expectations

Populate `adjudication`: `duplicate_of=<canonical finding_id>`, `rationale` naming the
shared identity dimensions and matched id, and `confidence`. Leave `stale`/`false_positive`
unset unless separately true. The harness sets `final_disposition = "duplicate"` when
`duplicate_of` is present.

## Escalation

- An uncertain match (only `title` similarity, no CWE/path/package overlap) -> do not assert
  duplicate; set `confidence <= 0.4` and let downstream route to `needs_human`.
- If neither `graphiti_search` nor `provider_search_issues` returns usable results, treat as
  non-duplicate rather than guessing, and note the gap in `rationale`.
