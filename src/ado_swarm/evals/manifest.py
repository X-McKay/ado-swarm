from __future__ import annotations

from enum import StrEnum
from statistics import mean
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EvalCaseCategory(StrEnum):
    GOLDEN = "golden"
    EDGE = "edge"
    ADVERSARIAL = "adversarial"
    REGRESSION = "regression"


class EvalCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    category: EvalCaseCategory = EvalCaseCategory.GOLDEN
    input: dict[str, Any] = Field(default_factory=dict)
    expected: dict[str, Any] = Field(default_factory=dict)


class EvalManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    manifest_id: str
    description: str
    pass_k: int = 3
    cases: list[EvalCase]
    model_profiles: list[str] = Field(default_factory=lambda: ["fake"])


def pass_k(successes: list[bool]) -> bool:
    return all(successes)


def summarize_trials(
    successes: list[bool], latencies_ms: list[float] | None = None
) -> dict[str, Any]:
    latencies_ms = latencies_ms or []
    return {
        "trials": len(successes),
        "passes": sum(1 for item in successes if item),
        "pass_rate": sum(1 for item in successes if item) / len(successes) if successes else 0.0,
        "pass_k": pass_k(successes),
        "avg_latency_ms": mean(latencies_ms) if latencies_ms else None,
    }
