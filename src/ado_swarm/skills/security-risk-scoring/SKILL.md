---
name: security-risk-scoring
description: Use this skill when scoring the real-world risk of a confirmed finding into a low/medium/high/critical RiskLevel.
allowed-tools: score_severity adjudication_signals graphiti_search
metadata:
  pack: risk-impact
  maturity: base
---
# security-risk-scoring

## Objective

Translate a confirmed (not stale/duplicate/false-positive) `normalized_finding` into a
calibrated `risk.risk_level` of `low | medium | high | critical`, with a concrete `impact`
statement. This drives prioritization and downstream automation gating.

## When to use

The risk_auditor must populate `risk`, after `adjudication` has left the finding open/real.

## Inputs

- `normalized_finding`: `severity`, `cwe`, `category`, `package_name`, `file_path`,
  `confidence`.
- `adjudication` (confirm the finding is real before scoring).
- `repository_evidence` (reachability / where the code lives).

## Procedure

1. Call `score_severity` with the finding to get a base technical severity normalized
   across scanners.
2. Adjust for the **CWE class**: RCE / injection / deserialization / auth bypass weigh up;
   info-leak / DoS-only weigh down.
3. Adjust for **exploitability & reachability**: reachable from untrusted input?
   internet-facing? behind auth / internal-only? Use `adjudication_signals` /
   `repository_evidence` for context.
4. Adjust for **blast radius**: live secret, data-store access, shared library, or widely
   imported module -> wider radius -> higher level.
5. Optionally `graphiti_search` for how similar findings were rated historically.

## Decision criteria

Combine base severity x CWE class x exploitability x blast radius:
- **critical**: RCE / injection / leaked live secret / auth bypass reachable from untrusted
  input on an internet-facing or shared path.
- **high**: serious weakness, reachable, but mitigated by auth, internal-only exposure, or
  limited radius; or a critical-class CWE with uncertain reachability.
- **medium**: real weakness with limited exploitability or contained blast radius (e.g.
  outdated dependency with no known reachable exploit).
- **low**: defense-in-depth / hardening / hygiene with negligible direct impact.
- Downgrade one level when scanner `confidence` is low AND reachability is unproven.

## Output expectations

Populate `risk` (`RiskClassification`): `risk_level`, a one-to-two sentence `impact` (what
an attacker gains and where), `rationale` naming the factors, and `confidence`. Treat
`automation_eligible` here as a preliminary hint; the automation-eligibility skill makes the
binding call.

## Escalation

- Critical or high with material uncertainty -> set `confidence <= 0.5`; downstream should
  treat as `needs_human` rather than auto-proceed.
- Never silently downgrade a critical-class CWE to medium without explicit reachability
  evidence recorded in `rationale`.
