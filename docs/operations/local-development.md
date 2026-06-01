# Local Development

The local development workflow is intentionally simple and repeatable. Use `mise` to install tool versions, `uv` to synchronize Python dependencies, and `just` as the command surface.

## Setup

```bash
cp .env.example .env
mise install
just setup
just check
```

## Local services

```bash
just up
just smoke
just logs
```

The default stack starts Temporal, Postgres, Neo4j, the API, and worker containers. The default source provider is `stub`, so no Azure DevOps or GitHub credentials are required for the smoke path.

## Agent iteration

Each agent can be evaluated independently. For example:

```bash
just eval-agent risk_auditor
just eval-agents
```

This allows a developer to change one agent's `main.py`, `metadata.yaml`, or `eval.py` and verify it in isolation before running the full test suite.

## Quality checks

```bash
just format
just check
```

The `check` target runs linting, type checking, unit tests, and all current agent evaluations with the deterministic fake model profile.
