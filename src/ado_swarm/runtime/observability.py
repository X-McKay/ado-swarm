from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from time import perf_counter
from typing import Any
from uuid import uuid4


@dataclass
class RuntimeSpan:
    name: str
    span_id: str = field(default_factory=lambda: str(uuid4()))
    start_time: datetime = field(default_factory=lambda: datetime.now(UTC))
    end_time: datetime | None = None
    duration_ms: float | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@contextmanager
def span(name: str, **attributes: Any) -> Iterator[RuntimeSpan]:
    started = perf_counter()
    current = RuntimeSpan(name=name, attributes=dict(attributes))
    try:
        yield current
    except Exception as exc:
        current.error = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        current.end_time = datetime.now(UTC)
        current.duration_ms = (perf_counter() - started) * 1000
