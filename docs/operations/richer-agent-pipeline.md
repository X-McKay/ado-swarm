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
