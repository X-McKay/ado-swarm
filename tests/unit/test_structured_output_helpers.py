from __future__ import annotations

import datetime
import enum

import pytest
from pydantic import BaseModel

from ado_swarm.model_gateway.structured_output import (
    resolve_structured_instance,
    synthesize_model,
)


class Severity(enum.Enum):
    LOW = "low"
    HIGH = "high"


class Nested(BaseModel):
    enabled: bool


class Output(BaseModel):
    title: str
    count: int
    severity: Severity
    nested: Nested
    created_at: datetime.datetime
    optional_note: str | None = None


def test_synthesize_model_builds_deterministic_zero_values() -> None:
    output = synthesize_model(Output)

    assert output.title == ""
    assert output.count == 0
    assert output.severity is Severity.LOW
    assert output.nested.enabled is False
    assert output.created_at == datetime.datetime(2020, 1, 1, tzinfo=datetime.UTC)
    assert output.optional_note is None


def test_resolve_structured_instance_prefers_responder() -> None:
    mapped = synthesize_model(Output)
    exact = Output(
        title="responder",
        count=1,
        severity=Severity.HIGH,
        nested=Nested(enabled=True),
        created_at=datetime.datetime(2024, 1, 1, tzinfo=datetime.UTC),
    )

    resolved = resolve_structured_instance(
        Output,
        [],
        structured_outputs={Output: mapped},
        structured_responder=lambda output_model, messages: exact,
    )

    assert resolved is exact


def test_resolve_structured_instance_rejects_wrong_responder_type() -> None:
    with pytest.raises(TypeError, match="expected an instance"):
        resolve_structured_instance(
            Output,
            [],
            structured_outputs={},
            structured_responder=lambda output_model, messages: Nested(enabled=True),
        )
