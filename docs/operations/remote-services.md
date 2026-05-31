# Remote Services

The runtime is designed so local Docker services can be replaced by hosted services through environment variables rather than code changes.

| Capability | Local default | Remote configuration |
|---|---|---|
| Temporal | `localhost:7233` | `TEMPORAL_ADDRESS`, `TEMPORAL_NAMESPACE`, and future TLS/API-key settings. |
| Runtime database | Docker Postgres | `DATABASE_URL`. |
| Knowledge graph | Docker Neo4j | `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`. |
| Source provider | `SOURCE_PROVIDER=stub` | `SOURCE_PROVIDER=azure_devops` or `SOURCE_PROVIDER=github`. |
| Azure DevOps | Disabled by default | `ADO_ORG_URL`, `ADO_PROJECT`, `ADO_PAT`. |
| GitHub | Disabled by default | `GITHUB_TOKEN`, `GITHUB_OWNER`. |
| Model inference | `MODEL_PROVIDER=fake` | `MODEL_PROVIDER=ollama`, `openai_compatible`, `bedrock`, or `litellm` as adapters are enabled. |

The source-provider boundary is the important design constraint. Agents should not call GitHub or Azure DevOps APIs directly. They request canonical operations such as `provider_get_issue`, `provider_get_repo_metadata`, and `provider_create_draft_pr`; the configured provider adapter maps those calls to the appropriate backend.

The first production-like deployment should keep write operations disabled until approval gates, redaction, and audit policies are validated with read-only traffic.
