---
name: code-location-verification
description: Use this skill when checking whether a finding's cited file, line, or manifest still exists at the ref.
allowed-tools: verify_file_location resolve_repository graphiti_search
metadata:
  pack: repository-investigation
  maturity: base
---
# code-location-verification

## Objective

Determine whether the code location a finding points at actually exists at the resolved ref, and
gather the evidence that proves it. This is the ground-truth check that decides whether a finding
is still live, has moved, or is `stale`. You verify presence; you do not judge exploitability.

## When to use

- A repository and ref are already resolved (see `repository-resolution`) and the finding cites a
  `file_path` (and optionally `line`, a manifest, or a symbol).
- You need to set `RepositoryEvidence.file_exists`.

## Inputs

- `NormalizedFinding.file_path` — the path to confirm at the ref.
- `NormalizedFinding.line` — secondary; a path can exist while the line drifted.
- `NormalizedFinding.package_name` — for SCA, verify the manifest entry, not a source line.
- `RepositoryEvidence.repository` / `.ref` — the resolved context to check against.

## Procedure

1. Confirm a repo/ref is resolved; if not, call `resolve_repository` first.
2. Call `verify_file_location` with the repository, ref, and `file_path`. Capture its result as
   the authoritative existence signal.
3. Interpret the result into `file_exists`: True (path present at ref), False (definitively absent),
   or None (could not determine — access/timeout/ambiguity). Never coerce None into False.
4. For SCA findings, verify the dependency manifest contains the `package_name`, not a code line —
   the file_path is often `package.json`/`requirements.txt`/`*.csproj`.
5. Append concrete proof to `RepositoryEvidence.evidence`: the path checked, the ref, and what was
   found (e.g. "path present at <ref>", "file deleted between scan and <ref>", "manifest no longer lists pkg").
6. Use `graphiti_search` to compare against prior verifications of the same location.

## Decision criteria

- `file_exists=True` => finding location is live; proceed to severity/remediation downstream.
- `file_exists=False` => strong signal the finding is `stale` (fixed/removed); cite the absence.
- `file_exists=None` => insufficient evidence; do NOT assert stale. This is an evidence gap.
- A present file with a moved line is still `file_exists=True`; line drift alone is not staleness.
- Evidence is "sufficient" only when it names the exact path AND the exact ref it was checked at.

## Output expectations

Sets `RepositoryEvidence.file_exists` and adds verification details to `RepositoryEvidence.evidence`
(repo_analyst section).

## Escalation

If verification returns None on a high/critical finding, or the path resolves ambiguously
(multiple matches, symlink, generated file), record the gap and mark `needs_human` rather than
guessing existence.
