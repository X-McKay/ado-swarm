# ADR-0011: Roadmap Hardening and Test Evidence

**Status:** Accepted  
**Date:** 2026-06-01

## Context

The post-review roadmap identified four implementation priorities: activate CI and provider lifecycle safety rails, simplify high-change code paths, decompose model-gateway responsibilities, and harden observability plus integration evidence. The project also needs a clear regression story so contributors can prove that agent, provider, workflow, and tool behavior continue to work after refactors.

## Decision

We will treat the local and CI validation suite as the primary evidence contract for roadmap changes. The active GitHub Actions workflow runs formatting, linting, type checking, unit tests, integration tests, and fake-profile agent evaluations. Integration tests must be deterministic and must not require live Azure DevOps, GitHub, Temporal, Postgres, or Neo4j services unless explicitly marked in a future service-backed job.

We introduced lifecycle-managed source-provider accessors so provider-backed tools can be tested through injected providers and so HTTP client lifecycle is centralized. Migration execution now validates checksums for already-applied SQL files before applying new migrations, preventing silent schema drift. Manifest parsing is format-specific and library-backed for common ecosystems instead of broad regex scanning. Supervisor scheduling decisions are extracted into pure helpers for unit coverage outside Temporal.

The model gateway now separates structured-output synthesis and provider construction from fake-model stream behavior. CLI and API mission controls share one mission service, which also attaches Temporal search attributes when starting mission workflows. Knowledge-store degradation now records operation-level telemetry for health checks, add-episode, and search failures.

## Consequences

The codebase gains stronger evidence for ongoing change safety. Developers can run the same checks locally and in CI, while targeted unit tests cover the formerly embedded behaviors. The tradeoff is a small increase in module count, but each new module isolates a previously mixed responsibility and improves independent testability.

## Validation Evidence

The roadmap implementation added unit tests for source-provider registry behavior, settings validation, migration checksum drift detection, manifest parsing, supervisor scheduling, scaffold template generation, structured-output helpers, mission service behavior, and knowledge-store telemetry. It also added deterministic integration tests for provider-backed tool runtime and mocked real-provider HTTP contracts.
