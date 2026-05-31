---
name: scanner-finding-fingerprinting
description: Use this skill when detecting whether a finding duplicates an existing one via a stable fingerprint.
allowed-tools: graphiti_search graphiti_add_episode provider_search_issues normalize_finding
metadata:
  pack: triage-readonly
  maturity: base
---
# scanner-finding-fingerprinting

## Objective

Produce a stable, location-tolerant identity for a finding so the same underlying vulnerability
reported by different scanners, tickets, or scan runs collapses into one. The fingerprint drives
the `duplicate` disposition and prevents re-triaging the same issue. It must be deterministic and
resistant to noise (line drift, path renames, scanner version bumps).

## When to use

- A `NormalizedFinding` is classified and you need to know if it is novel or a repeat.
- Multiple tickets in the casefile may describe the same defect.

## Inputs

- `NormalizedFinding.scanner`, `.cwe`, `.category` — the *class* axis of identity.
- `NormalizedFinding.package_name` — for SCA, the dominant identity key.
- `NormalizedFinding.file_path` (path, not line) — for SAST/IaC, the *location* axis.
- `NormalizedFinding.finding_id` — provider id; useful but NOT sufficient for cross-source dedup.

## Procedure

1. Build the fingerprint from stable fields only. Recommended composition:
   - SCA: `cwe` + normalized `package_name` (case-folded, ecosystem-qualified). Exclude version.
   - SAST/IaC: `cwe`/rule + repo-relative `file_path` + a normalized symbol/sink from the title.
   - Secrets: `cwe` + `file_path` + secret-type. Never include the secret value.
   Exclude `line`, scanner version, and timestamps — they cause false uniqueness.
2. Query prior episodes with `graphiti_search` using the fingerprint components to find matches.
3. Cross-check live tickets with `provider_search_issues` (by CWE/package/path) for open duplicates
   the knowledge graph may not have captured.
4. If novel, persist it via `graphiti_add_episode` so future runs can match against it.
5. If matched, mark the finding for the `duplicate` disposition and reference the canonical finding_id.

## Heuristics

- Two findings match when class axis AND location axis agree; differing `line` alone is still a match.
- A renamed file with identical sink + CWE is likely the same finding (location drift) — match it.
- Same CWE in two unrelated files are DISTINCT findings; do not over-collapse on class alone.
- For SCA, the same CVE/CWE on the same package in different manifests is one logical finding.
- Fingerprints must be reproducible: identical inputs => identical fingerprint, every run.

## Output expectations

Contributes a stable fingerprint and a dedup verdict; sets disposition to `duplicate` (with the
canonical finding_id) when matched, or records a new episode when novel.

## Escalation

If two findings partially match (same path, conflicting CWE; or same package, different ecosystem)
and you cannot confidently call duplicate vs distinct, keep them separate and flag `needs_human`
rather than collapsing and losing a real finding.
