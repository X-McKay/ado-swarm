# ADR-0002: Provider-neutral source adapters

## Status

Accepted for the base architecture.

## Context

The system must support both Azure DevOps and GitHub. These platforms use different concepts and API shapes for issues, work items, repositories, branches, files, pull requests, comments, checks, and security findings.

## Decision

The runtime exposes provider-neutral ports and canonical contracts: `SourceIssue`, `SourceRepositoryRef`, `SourceFile`, `SourcePullRequest`, and `ProviderMutationResult`. Azure DevOps and GitHub integrations live behind adapter modules under `src/ado_swarm/tools/source_providers/`.

Agents and skills must use provider-neutral tool names such as `provider_get_issue` and `provider_get_repo_metadata`; they must not call platform-specific APIs directly.

## Consequences

This design keeps the agent workflow stable while allowing provider-specific behavior to evolve independently. It also makes local and CI testing possible with the `stub` provider and no external credentials.
