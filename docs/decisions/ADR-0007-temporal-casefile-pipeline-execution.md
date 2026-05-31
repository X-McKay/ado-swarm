# ADR-0007: Temporal execution of the full casefile agent pipeline

**Status:** Accepted

`ado-swarm` now executes the read-only security triage workflow as a six-agent Temporal pipeline: `ticket_analyst → repo_analyst → security_reviewer → risk_auditor → solutions_architect → test_engineer`. The planner emits the full dependency chain, and the supervisor workflow passes each completed task's casefile artifact to its dependent task through `TaskSpec.input_refs`.

## Context

The previous mission plan only executed `ticket_analyst` and `risk_auditor`, which proved the orchestration path but did not exercise the richer `SecurityCasefile` collaboration model. The next wave of agents introduced deterministic casefile enrichment, so Temporal needed to pass updated casefile artifacts between child workflows rather than relying on in-process state or prompt-only handoffs.

## Decision

The planning activity now creates all six tasks in a linear DAG. The first task receives a provider-neutral `source_issue` constraint from the configured source provider. Each downstream task receives the artifact references emitted by its direct dependencies. The richer agents use `casefile_from_invocation()` to read either `constraints.casefile`, `constraints.source_issue`, or prior artifact metadata, and emit updated casefile artifacts with `casefile_artifact()`.

## Consequences

This preserves Temporal determinism because provider reads happen in the planning activity and agent execution happens inside child workflows/activities. It also makes the workflow state auditable: `RunSnapshot.artifact_refs` now contains the casefile artifacts emitted by every pipeline stage, while `RunSnapshot.run_artifacts` retains the immutable plan artifact. The approach remains read-only and safe because write-capable actions are still represented as plans, validation checklists, or approval requirements rather than direct repository mutations.

## Validation

The pipeline is covered by unit tests that assert the planner emits the six-agent dependency chain and that casefile artifacts can be carried into downstream task inputs. It is also validated through the Docker-backed Temporal/Postgres/Neo4j/llama.cpp E2E path.
