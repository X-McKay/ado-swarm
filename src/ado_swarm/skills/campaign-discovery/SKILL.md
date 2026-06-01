---
name: campaign-discovery
description: Use this skill when grouping many related findings into a single coordinated remediation campaign (shared root cause, package, or pattern) for batch handling.
allowed-tools: summarize_findings graphiti_search provider_search_issues score_severity
metadata:
  pack: analytics
  maturity: base
---
# campaign-discovery

## Objective

Detect themes across a finding population — the same vulnerable package, the same CWE recurring
across repos, or a systemic misconfiguration — and propose a coordinated campaign so they are
fixed together rather than one ticket at a time. Read/analytics only.

## When to use

When a mission spans many findings and per-finding handling would be redundant or inconsistent.

## Inputs

- `normalized_finding` fields across the mission (package_name, cwe, category, scanner, file_path).
- Severity assessments and cross-mission history via `graphiti_search`.

## Procedure

1. `summarize_findings` to bucket findings by candidate campaign keys: `package_name`
   (fleet-wide dependency), `cwe` (recurring weakness), or IaC misconfig type.
2. `graphiti_search` for past campaigns on the same theme to reuse a proven fix template.
3. `provider_search_issues` to detect existing tickets/epics covering the theme (avoid duplicates).
4. `score_severity` across the cluster to prioritize by aggregate risk and breadth.
5. Define each campaign: theme, member finding ids, and one recommended action
   (e.g. "bump lodash to >=4.17.21 across 12 repos").

## Decision criteria

- Group only findings that share a genuine root cause and a common fix; do not force-fit.
- Prioritize campaigns by aggregate severity x reach x fix uniformity.

## Checklist

- [ ] Each campaign has a crisp theme and a single coherent remediation action.
- [ ] Members truly share root cause (not just superficial scanner overlap).
- [ ] Cross-checked against existing provider epics to prevent duplicate effort.

## Output expectations

Campaign insights (theme, description, member finding ids, recommended_action).

## Safety

Read-only. Discovery proposes batching; it does not itself apply changes or close tickets.

## Escalation

Org-wide or breaking-change campaigns → recommend human program-level coordination.
