---
name: git-history-investigation
description: Use this skill when reading commit and file history to decide if a finding was already fixed, moved, or deleted.
allowed-tools: verify_file_location provider_get_repo_metadata graphiti_search graphiti_add_episode
metadata:
  pack: repository-investigation
  maturity: base
---
# git-history-investigation

## Objective

Use the repository's history to explain *what happened* to a finding's code since it was reported:
was it remediated, refactored/moved, or deleted? Where presence-checking
(`code-location-verification`) tells you the location's current state, history-investigation tells
you the trajectory — which is what justifies a `stale` or `closed_with_evidence` disposition with
a defensible audit trail.

## When to use

- A finding's location was found absent or changed and you need to know whether that change was an
  actual fix versus an unrelated move.
- You need temporal evidence (commit, author, message) to support closing a finding.

## Inputs

- `NormalizedFinding.file_path` / `.line` — the location whose history you trace.
- `NormalizedFinding.cwe` / `.category` — to recognize a *fix* commit vs a cosmetic move.
- `RepositoryEvidence.repository` / `.ref` — the resolved repo and the ref you compare against.
- Scan ref/date (from resolution) — the "before" point in history.

## Procedure

1. Establish the two points in time: the ref/commit at scan time and the current resolved `ref`.
2. Use `provider_get_repo_metadata` to enumerate refs/tags and locate commits touching the
   `file_path` between those two points (read-only history inspection).
3. For each relevant commit, judge intent from the message and diff context: a fix removes the
   vulnerable sink/upgrades the package; a move/rename relocates it; a delete removes the file.
4. Re-verify the destination with `verify_file_location` when code appears moved — confirm the
   vulnerable pattern is gone, not just relocated.
5. Search `graphiti_search` for related prior episodes (same file/CWE) to avoid re-deriving history.
6. Record the conclusion as a new episode via `graphiti_add_episode` for future reuse.

## Heuristics

- A commit that bumps the affected `package_name` version past the fixed range => fixed (stale).
- A commit whose message references the CWE/CVE or "fix"/"security" near the line => likely a real fix.
- A pure rename/move with the vulnerable code intact => NOT fixed; treat as relocated, re-verify.
- File deleted AND no equivalent reintroduced elsewhere => removed (stale).
- Absence of any touching commit since the scan => finding is still live; do not call it stale.

## Output expectations

Adds history-based reasoning to `RepositoryEvidence.evidence` (commit ids, messages, before/after
refs) supporting a `stale` or `closed_with_evidence` disposition, and persists a knowledge episode.

## Escalation

If history is inconclusive (squashed/rewritten history, force-push, shallow clone, ambiguous
move) or a fix cannot be confirmed at the destination, present the evidence as-is and mark
`needs_human` instead of asserting the finding was fixed.
