"""OpenTelemetry GenAI tracing — centralized, config-gated setup.

Wiring is opt-in via ``tracing_enabled`` so tests and offline runs emit nothing.
When enabled:
- ``setup_telemetry()`` configures Strands' OTLP exporter so the agent loop emits
  GenAI-semantic-convention spans (model calls, tool calls, token usage).
- ``temporal_interceptors()`` returns the Temporal OpenTelemetry ``TracingInterceptor``
  so workflow/activity spans share trace context with the agent spans.

Both are no-ops (or empty) when tracing is disabled, and import of the OTel SDK
is deferred so the optional dependency never hard-fails an import.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ado_swarm.config import Settings, get_settings

if TYPE_CHECKING:
    from temporalio.client import Interceptor

_TELEMETRY_CONFIGURED = False


def setup_telemetry(settings: Settings | None = None) -> bool:
    """Configure Strands OTLP tracing if enabled. Returns True if configured.

    Idempotent: safe to call from every worker/process entry point.
    """
    global _TELEMETRY_CONFIGURED
    settings = settings or get_settings()
    if not settings.tracing_enabled or _TELEMETRY_CONFIGURED:
        return _TELEMETRY_CONFIGURED
    from strands.telemetry import StrandsTelemetry

    telemetry = StrandsTelemetry()
    if settings.otel_exporter == "console":
        telemetry.setup_console_exporter()
    else:
        # OTLP HTTP exporter; endpoint comes from OTEL_EXPORTER_OTLP_ENDPOINT env.
        telemetry.setup_otlp_exporter()
    _TELEMETRY_CONFIGURED = True
    return True


def trace_attributes(settings: Settings | None = None) -> dict[str, Any]:
    """Common span attributes attached to every agent (service identity)."""
    settings = settings or get_settings()
    return {"service.name": "ado-swarm", "deployment.environment": settings.app_env}


def temporal_interceptors(settings: Settings | None = None) -> list[Interceptor]:
    """Return Temporal OTel interceptors when tracing is enabled, else an empty list."""
    settings = settings or get_settings()
    if not settings.tracing_enabled:
        return []
    from temporalio.contrib.opentelemetry import TracingInterceptor

    return [TracingInterceptor()]
