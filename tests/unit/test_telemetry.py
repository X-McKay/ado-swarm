from __future__ import annotations

from ado_swarm.config import Settings
from ado_swarm.runtime.telemetry import (
    setup_telemetry,
    temporal_interceptors,
    trace_attributes,
)


def _settings(**overrides) -> Settings:
    return Settings(**overrides)  # type: ignore[arg-type]


def test_tracing_disabled_by_default_is_noop() -> None:
    s = _settings(tracing_enabled=False)
    assert setup_telemetry(s) is False
    assert temporal_interceptors(s) == []


def test_trace_attributes_carry_service_identity() -> None:
    attrs = trace_attributes(_settings(app_env="ci"))
    assert attrs["service.name"] == "ado-swarm"
    assert attrs["deployment.environment"] == "ci"


def test_interceptors_present_when_enabled() -> None:
    interceptors = temporal_interceptors(_settings(tracing_enabled=True))
    assert len(interceptors) == 1
