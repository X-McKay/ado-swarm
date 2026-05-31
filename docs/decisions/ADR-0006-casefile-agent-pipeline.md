# ADR-0006: Deterministic casefile enrichment pipeline for richer agents

**Status:** Accepted

The next wave of richer `ado-swarm` behavior uses the `SecurityCasefile` as the primary handoff object between specialist agents. `ticket_analyst` creates the casefile from a provider-neutral source issue. `repo_analyst` enriches repository evidence. `security_reviewer` adjudicates stale, false-positive, already-fixed, and duplicate signals. `risk_auditor` classifies risk and automation eligibility. `solutions_architect` creates a bounded remediation plan. `test_engineer` creates a validation checklist and determines whether the casefile is ready for draft-review preparation.

This approach keeps the system deterministic, testable, and auditable while richer Strands-powered reasoning is introduced behind stable contracts. Each agent may still use the harness runtime and model gateway for open-ended reasoning, but casefile fields are updated through explicit typed models first.

## Decision drivers

The agent swarm needs a durable collaboration surface that works across Temporal workflow boundaries, provider adapters, local LLM tests, and future UI/API surfaces. A single typed casefile avoids implicit prompt-only handoffs and gives evals a clear state object to assert against.

## Consequences

Agents now share common `casefile_utils` helpers for extracting casefiles from task constraints or artifact metadata and for emitting updated casefile artifacts. New agent behavior must add deterministic unit tests and eval assertions against the casefile state it owns.
