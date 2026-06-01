---
name: security-ticket-normalization
description: Use this skill when turning a raw provider issue, work item, or scanner alert into a single canonical NormalizedFinding.
allowed-tools: provider_get_issue provider_search_issues normalize_finding graphiti_search
metadata:
  pack: triage-readonly
  maturity: base
---
# security-ticket-normalization

## Objective

Convert one messy, human- or tool-authored security ticket into exactly one canonical
`NormalizedFinding`. You are mapping free-text and provider-specific payloads onto a typed
contract so downstream agents can reason deterministically. You do not classify deeply
(see `finding-type-classification`) or fingerprint for dedup (see `scanner-finding-fingerprinting`);
your job is faithful, lossless field extraction with honest confidence.

## When to use

- A `SourceIssue` (provider, external_id, url, title, body, state, labels, repository,
  provider_payload) needs to become a `NormalizedFinding`.
- The ticket is the unit of triage and has not yet been normalized in this casefile.

## Inputs

- `SourceIssue.title` / `SourceIssue.body` — primary free text.
- `SourceIssue.labels` — strong hints for scanner, severity, and category.
- `SourceIssue.provider_payload` — the richest source; scanner exports often embed
  rule ids, CWE, file/line, and package version here as structured keys.
- `SourceIssue.repository` — carry through; do not invent a repo.

## Procedure

1. If you only have an `external_id`, hydrate the full ticket with `provider_get_issue`
   before extracting anything. Never normalize from a title alone.
2. Read `provider_payload` first, then `body`, then `labels`. Prefer structured payload
   keys over prose when they conflict; prose is the fallback.
3. Call `normalize_finding` with everything you extracted: title, description, scanner,
   category, severity, cwe, package_name, file_path, line. Let the tool produce the typed
   `NormalizedFinding` rather than hand-building it.
4. Set `confidence` (0..1) to reflect extraction certainty, not exploitability: structured
   payload with explicit fields => high (>=0.8); inferred from prose => mid (0.4-0.7);
   guessed from a label alone => low (<0.4).
5. Optionally call `graphiti_search` on the title/CWE/package to see whether a prior
   episode already described this finding — useful context, not a dedup decision here.

## Heuristics

- Map provider severity vocab onto critical/high/medium/low/informational; never leave it
  null when any signal exists. "warning" => low/medium, "error"/"blocker" => high/critical.
- `cwe` is gold when present (e.g. `CWE-79`); copy it verbatim including the `CWE-` prefix.
- For dependency alerts the package and version live in payload, not the title — extract
  `package_name` even if `file_path` is the manifest.
- Strip provider boilerplate (auto-generated remediation banners, "scanned by" footers)
  from `description`; keep the substantive finding text.

## Output expectations

Contributes one `NormalizedFinding` to the casefile's findings (ticket_analyst section)
with all fields populated that the source supports, and a calibrated `confidence`.

## Escalation

If the ticket conflates multiple distinct vulnerabilities, or `provider_payload` and prose
disagree on a load-bearing field (file vs package, severity by two tiers) with no tiebreaker,
do not silently pick one — record the lower confidence and flag for `needs_human`.
