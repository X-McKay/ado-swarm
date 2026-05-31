---
name: finding-type-classification
description: Use this skill when deciding the scanner, vulnerability class, CWE, and severity tier of a finding.
allowed-tools: normalize_finding score_severity adjudication_signals graphiti_search
metadata:
  pack: triage-readonly
  maturity: base
---
# finding-type-classification

## Objective

Decide what *kind* of finding you are looking at and how serious it is. Concretely: infer
the `scanner`, the `category` (vulnerability class), the `cwe`, and a calibrated `severity`
on the canonical scale. This is the analytical step that sits between raw normalization and
fingerprinting — it gives the finding its taxonomy.

## When to use

- A `NormalizedFinding` exists but `category`, `cwe`, or `severity` is missing or unreliable.
- The provider's stated severity needs sanity-checking against the actual class of issue.

## Inputs

- `NormalizedFinding.title` / `.description` — class signals (e.g. "SQL injection", "hardcoded secret").
- `NormalizedFinding.scanner` — narrows the category space (a secrets scanner emits secret findings).
- `NormalizedFinding.cwe` — if already set, it largely determines category.
- `NormalizedFinding.package_name` / `.file_path` / `.line` — SCA vs SAST vs IaC discriminators.

## Procedure

1. Identify the scanner family from `scanner` and payload artifacts; if absent, infer it from
   the shape of the evidence (package+version => SCA; file+line+rule => SAST; entropy/regex
   match => secrets; `.tf`/`.yaml`/Dockerfile rule => IaC).
2. Derive `category` from CWE first, then scanner family, then prose keywords. Be specific
   (e.g. "Path Traversal", "Cleartext Storage of Secret"), not just "security".
3. Call `score_severity` to produce a defensible `severity` (critical/high/medium/low/informational)
   and reconcile it with the provider's claim; downgrade informational-only lint, upgrade
   RCE/auth-bypass classes.
4. Call `adjudication_signals` to gather corroborating context (reachability hints, fix
   availability, exploit maturity) that should move severity within a tier.
5. Re-emit via `normalize_finding` so the updated `category`/`cwe`/`severity` land on the typed contract.
6. Use `graphiti_search` to check how findings of this class were dispositioned historically.

## Decision criteria

- CWE present and recognized => trust it for category; let it cap or floor severity
  (e.g. CWE-89 SQLi is never "low").
- Conflicting class signals (title says XSS, CWE says SSRF) => prefer the CWE, lower confidence.
- A SAST finding with no reachable sink and no `line` is a candidate for downgrade, not closure.
- Map any provider tier into the canonical five; never emit a non-canonical severity string.

## Output expectations

Updates the casefile `NormalizedFinding` with authoritative `scanner`, `category`, `cwe`,
and `severity`, plus an adjusted `confidence` reflecting classification certainty.

## Escalation

If the class genuinely cannot be determined (no CWE, ambiguous prose, unknown scanner) or
severity hinges on business context you cannot see, classify conservatively and mark for
`needs_human` rather than guessing a high-stakes tier.
