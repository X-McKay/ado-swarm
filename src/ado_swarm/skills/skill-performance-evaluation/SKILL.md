---
name: skill-performance-evaluation
description: Use this skill when evaluating how effective the swarm's skills have been across past remediations to recommend tuning, retirement, or new skills.
allowed-tools: summarize_findings graphiti_search graphiti_add_episode
metadata:
  pack: analytics
  maturity: base
---
# skill-performance-evaluation

## Objective

Measure each skill's real-world effectiveness from historical outcomes — invocation count,
success rate, and qualitative observations — and recommend concrete improvements. A
meta/analytics skill: read-only, never touches remediation code.

## When to use

Periodically, or after a batch of missions, to feed continuous improvement of the skill catalog.

## Inputs

- Outcome history across findings: `final_disposition`, `readiness`, review verdicts, and which
  skills were active (retrieved via `graphiti_search`).
- Aggregate finding outcomes via `summarize_findings`.

## Procedure

1. `graphiti_search` for episodes tagged with each skill name and their resulting dispositions
   (e.g. `closed_with_evidence` vs `needs_human` vs reverted PRs).
2. `summarize_findings` to compute per-skill invocations and a success rate
   (successful terminal disposition / total invocations).
3. Capture qualitative observations: common failure modes, scope-creep incidents, escalation rate.
4. Compare skills handling the same category to spot redundancy or gaps in the catalog.
5. Record the evaluation via `graphiti_add_episode` for trendability across periods.

## Decision criteria

- KEEP for high success + low escalation; TUNE when failures cluster on a fixable cause;
  RETIRE when consistently low value or superseded; PROPOSE-NEW when a category lacks an effective skill.
- Require enough invocations before judging; flag low-sample skills as "insufficient data".

## Checklist

- [ ] Success rate computed from real terminal dispositions, not self-reports.
- [ ] Observations cite specific findings/episodes.
- [ ] Recommendation is actionable (what to change and why).

## Output expectations

A per-skill report (skill name, invocations, success_rate, observations, recommendation).

## Safety

Read-only analytics. Recommendations are advisory inputs to humans maintaining the catalog; this
skill never edits, enables, or disables skills itself.

## Escalation

Evidence a skill is producing unsafe or out-of-boundary changes → flag urgently for human review.
