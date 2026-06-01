# ADR-0010: OpenTelemetry GenAI tracing and provider-contract semantics pinning

**Status:** Accepted
**Date:** 2026-05-31
**Relates to:** ADR-0002 (provider-neutral adapters), ADR-0008 (model-driven agents).

## Context

Two loose ends from the codebase review (`docs/codebase-review-2026-05.md` §7, §8):

1. **Observability.** Agents reason with a model and call tools through Temporal, but there was no end-to-end tracing — the hand-rolled `runtime/observability.py` span computed a duration string with no exporter. The harness literature treats traces as queryable analytical data and recommends the OTel GenAI semantic conventions.
2. **Provider-contract leaks.** `SourceIssue.external_id` was non-uniform (GitHub used a bare number *or* `{repo}#{number}`), and `ProviderMutationResult.external_id` meant different things across methods/providers (the created comment id, or — in the stub — the parent issue id). Callers had to guess.

## Decision

### OTel GenAI tracing (config-gated)
- A single `runtime/telemetry.py` owns setup. `setup_telemetry()` configures Strands `StrandsTelemetry` (OTLP HTTP by default, or console) **only when `tracing_enabled` is true**; it is idempotent and a no-op otherwise, so tests/offline runs emit nothing and pay no cost.
- The agent runtime (`run_model_agent`) calls `setup_telemetry()` and attaches `trace_attributes` (service identity + `ado_swarm.agent_id`) to every Strands `Agent`, so GenAI spans (model/tool calls, token usage) are attributable to a specific agent.
- `build_temporal_client` installs the Temporal `TracingInterceptor` (via `temporal_interceptors()`) when tracing is enabled, so workflow/activity spans share trace context with the agent spans. Endpoint comes from the standard `OTEL_EXPORTER_OTLP_ENDPOINT` env var.

### Provider-contract semantics pinning
- `SourceIssue.external_id` is documented on the contract as the provider's canonical, **round-trippable** id — exactly what `get_issue(external_id)` accepts back. Callers must pass it verbatim and never re-derive an id from other fields.
- `ProviderMutationResult` gains a **required** `result_kind: MutationResultKind` (`issue_comment` | `pr_comment` | `pull_request`). `external_id` is always the id of the *thing created* by the mutation, never its parent. The stub was corrected to return a distinct comment id (with the parent id moved to `provider_payload`), matching the real adapters.

## Consequences

- Operators can trace a mission operator → workflow → activity → agent → model/tool in any OTel backend, with zero overhead when disabled.
- Tool/agent code can rely on `result_kind` + `external_id` without per-provider special-casing; the stub now models the same semantics as ADO/GitHub, so tests exercise the real contract.
- New settings: `tracing_enabled` (default `false`), `otel_exporter` (`otlp` | `console`).

## Validation

`tests/unit/test_telemetry.py` (no-op when disabled, interceptors present when enabled, service-identity attributes), `tests/unit/test_provider_semantics.py` (mutation `result_kind`/id meaning, `external_id` round-trip). The OTel enable path is exercised via the console exporter. All hermetic.
