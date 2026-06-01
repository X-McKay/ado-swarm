---
name: false-positive-pattern-mining
description: Use this skill when mining historical adjudication outcomes to find recurring false-positive patterns that can pre-empt wasted remediation effort.
allowed-tools: summarize_findings graphiti_search graphiti_add_episode adjudication_signals
metadata:
  pack: analytics
  maturity: base
---
# false-positive-pattern-mining

## Objective

Identify recurring classes of findings that consistently resolve to `false_positive`, so future
findings matching the pattern can be fast-tracked to adjudication instead of remediation.
Read/analytics only — this skill never edits code.

## When to use

When analyzing outcomes across many findings/missions to improve triage efficiency.

## Inputs

- Historical adjudication outcomes (`adjudication.false_positive`, `rationale`, `confidence`).
- `normalized_finding` metadata (scanner, category, cwe, file_path globs, package_name).
- Knowledge-graph history via `graphiti_search`.

## Procedure

1. `summarize_findings` to aggregate findings by `scanner` x `cwe` x `category`.
2. `graphiti_search` for prior false-positive episodes and their signals.
3. Cluster recurring FP drivers: test/fixture/vendor paths, generated code, known-safe sinks,
   sanitizer-wrapped inputs, dev-only configs.
4. For each candidate, compute the FP rate and confidence; correlate with `adjudication_signals`.
5. Persist durable, generalizable patterns via `graphiti_add_episode` so adjudication can reuse them.

## Decision criteria

- Promote a pattern only with a high FP rate and enough samples (avoid overfitting to one or two).
- A pattern must be expressible as concrete, checkable signals — not a vague heuristic.

## Checklist

- [ ] Pattern backed by multiple independent findings.
- [ ] Clear scoping rule (path/scanner/cwe) to avoid suppressing true positives.
- [ ] Recorded with evidence so it is auditable and reversible.

## Output expectations

Summarized patterns + recorded episodes describing the FP pattern, affected finding ids, and a
recommended triage shortcut.

## Safety

Read-only analytics. A mined pattern is a hint for adjudication, never an auto-suppression —
true positives must never be silenced by an over-broad rule.

## Escalation

A pattern that would suppress security-relevant findings → flag for human policy review.
