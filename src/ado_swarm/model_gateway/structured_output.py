"""Structured-output resolution helpers for deterministic model tests."""

from __future__ import annotations

import datetime as _dt
import enum
from collections.abc import Callable, Sequence
from typing import Any, TypeVar

from pydantic import BaseModel
from pydantic.fields import FieldInfo

T = TypeVar("T", bound=BaseModel)
StructuredResponder = Callable[[type[BaseModel], object], BaseModel]

_FIXED_EPOCH = _dt.datetime(2020, 1, 1, 0, 0, 0, tzinfo=_dt.UTC)


def resolve_structured_instance(
    output_model: type[T],
    messages: object,
    *,
    structured_outputs: dict[type[BaseModel], BaseModel],
    structured_responder: StructuredResponder | None = None,
) -> T:
    """Resolve an output instance using responder, mapping, then synthesis."""
    if structured_responder is not None:
        instance = structured_responder(output_model, messages)
    elif output_model in structured_outputs:
        instance = structured_outputs[output_model]
    else:
        instance = synthesize_model(output_model)

    if not isinstance(instance, output_model):
        raise TypeError(
            f"Structured output for {output_model.__name__} is "
            f"{type(instance).__name__}, expected an instance of {output_model.__name__}"
        )
    return instance


def synthesize_model(output_model: type[T]) -> T:
    """Build a valid instance filling required fields with deterministic zero-values."""
    values: dict[str, Any] = {}
    for name, field in output_model.model_fields.items():
        if not field.is_required():
            continue
        values[name] = synthesize_field(field)
    return output_model(**values)


def synthesize_field(field: FieldInfo) -> Any:
    """Synthesize a deterministic, type-appropriate value for a Pydantic field."""
    return synthesize_value(field.annotation)


def synthesize_value(annotation: Any) -> Any:
    """Return a deterministic zero-value for the given type annotation."""
    import types
    import typing

    origin = typing.get_origin(annotation)
    args = typing.get_args(annotation)

    if origin in (typing.Union,) or isinstance(annotation, types.UnionType):
        non_none = [arg for arg in args if arg is not type(None)]
        if not non_none:
            return None
        return synthesize_value(non_none[0])

    if origin in (list, set, tuple, frozenset):
        return [] if origin is not tuple else ()
    if origin is dict:
        return {}

    if isinstance(annotation, type):
        if issubclass(annotation, enum.Enum):
            return next(iter(annotation))
        if issubclass(annotation, BaseModel):
            return synthesize_model(annotation)
        if issubclass(annotation, bool):
            return False
        if issubclass(annotation, int):
            return 0
        if issubclass(annotation, float):
            return 0.0
        if issubclass(annotation, str):
            return ""
        if issubclass(annotation, bytes):
            return b""
        if issubclass(annotation, _dt.datetime):
            return _FIXED_EPOCH
        if issubclass(annotation, _dt.date):
            return _FIXED_EPOCH.date()
        if issubclass(annotation, (list, set, frozenset)):
            return []
        if issubclass(annotation, dict):
            return {}

    if annotation in (list, Sequence):
        return []
    if annotation is dict:
        return {}
    return None
