# Richer Agent Pipeline Operations

The richer-agent wave converts the first read-only security workflow into a deterministic casefile enrichment pipeline. The pipeline remains safe because all provider interactions are read-only and all mutation-oriented outcomes are represented as plans, checklists, or approval requirements rather than direct writes.

| Agent | Casefile ownership | Output field |
|---|---|---|
| `ticket_analyst` | Normalize provider issue into canonical finding. | `normalized_finding`, initial `repository_evidence`, `audit.ticket_analyst` |
| `repo_analyst` | Resolve repository and verify the referenced file path when available. | `repository_evidence`, `audit.repo_analyst` |
| `security_reviewer` | Adjudicate stale, false-positive, duplicate, and already-fixed signals. | `adjudication`, `final_disposition`, `audit.security_reviewer` |
| `risk_auditor` | Classify risk and automation eligibility. | `risk`, `final_disposition`, `audit.risk_auditor` |
| `solutions_architect` | Generate bounded remediation strategy and steps. | `remediation_plan`, `audit.solutions_architect` |
| `test_engineer` | Generate validation checklist and review readiness. | `audit.test_engineer`, optional `ready_for_review` disposition |

## Input and output convention

Agents accept a casefile from `TaskSpec.constraints["casefile"]`, a source issue from `TaskSpec.constraints["source_issue"]`, or a prior artifact containing `metadata.casefile`. Agents emit a new artifact reference with the updated casefile in `metadata.casefile`. This lets Temporal tasks pass typed casefile state without depending on filesystem side effects.

## Safety posture

The current pipeline does not modify repositories, source-provider tickets, branches, or pull requests. Risky or write-capable work remains behind `ToolPolicy`, approval state, and future sandboxed remediation flows.


## Temporal execution model

The default mission planner now emits the full six-agent linear DAG. `ticket_analyst` receives the configured source provider's initial source issue, and each downstream task receives the artifact references emitted by its dependency through `TaskSpec.input_refs`. The supervisor workflow also records all emitted casefile artifacts in `RunSnapshot.artifact_refs`, so operators can inspect the progressive casefile state across the mission.

| Stage | Dependency | Handoff mechanism |
|---|---|---|
| `ticket_analyst` | None | `constraints.source_issue` from the configured source provider. |
| `repo_analyst` | `ticket_analyst` | Casefile artifact in `input_refs`. |
| `security_reviewer` | `repo_analyst` | Enriched casefile artifact in `input_refs`. |
| `risk_auditor` | `security_reviewer` | Adjudicated casefile artifact in `input_refs`. |
| `solutions_architect` | `risk_auditor` | Risk-classified casefile artifact in `input_refs`. |
| `test_engineer` | `solutions_architect` | Remediation-plan casefile artifact in `input_refs`. |

This execution model keeps the workflow deterministic while still preserving a complete audit trail of each agent's state transition. Provider reads remain inside activities or agent execution, and write-capable operations remain disabled unless `ToolPolicy` and approval state explicitly allow them.
