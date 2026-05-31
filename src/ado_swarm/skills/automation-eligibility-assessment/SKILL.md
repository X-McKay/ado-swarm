---
name: automation-eligibility-assessment
description: Use this skill when deciding whether a remediation is safe to automate without human authorship.
allowed-tools: score_severity assess_readiness adjudication_signals
metadata:
  pack: risk-impact
  maturity: base
---
# automation-eligibility-assessment

## Objective

Make the binding call on `risk.automation_eligible`: whether this fix is *bounded,
well-understood, and low-enough risk* to be generated and proposed by the swarm (as a draft
PR), versus requiring a human to author or approve the change.

## When to use

After risk scoring and change-impact classification, before remediation planning commits to
an automatable path.

## Inputs

- `risk`: `risk_level`, `impact`.
- `normalized_finding`: `category`, `package_name`, `severity`, `confidence`.
- `adjudication`: must show the finding is real (not stale/duplicate/false-positive).
- Readiness via `assess_readiness`.

## Procedure

1. Confirm the finding is real and confidently scored (`adjudication`, `risk`).
2. Call `assess_readiness` to check inputs are complete and the change is well-specified
   enough to mechanize.
3. Apply the eligibility gate below.
4. Set `risk.automation_eligible` and name the deciding factor in `risk.rationale`.

## Decision criteria

Automation-eligible **only when ALL hold**:
- `risk.risk_level` is `low` or `medium` (never `high`/`critical`).
- The change is **bounded** to a known, small file/config set (contained impact).
- The fix type is **well-understood** -- strongly favor dependency version bumps within a
  compatible range; also simple config/IaC corrections with a canonical fix.
- Evidence is clear: real finding, high adjudication/risk `confidence`, no ambiguity about
  the correct fix.

Mark **not eligible** when ANY holds:
- `risk_level` is `high` or `critical`.
- Breaking change, major-version upgrade, cross-module refactor, or public-API change.
- Ambiguous root cause or multiple plausible fixes.
- Low confidence anywhere upstream (adjudication or risk).
- Touches shared/critical-path code or secrets handling.

## Output expectations

Set `risk.automation_eligible` (bool) and extend `risk.rationale` with the deciding factor.
Eligible findings flow toward a `draft_pr_created` disposition under approval; ineligible
ones stay human-authored.

## Escalation

- Any uncertainty defaults to **not eligible** -- bias strongly toward human authorship.
- When ineligible, ensure downstream sets `remediation_plan.requires_human_approval = True`
  and routes to `final_disposition = "needs_human"` where appropriate.
