"""Model profile + gateway.

Model *invocation* is handled by the Strands model providers
(`model_gateway.strands_models.build_strands_model`); this module only carries the
provider-neutral `ModelProfile`. `ModelGateway` remains as a thin profile holder
so existing call sites (registry, evals) keep a stable seam.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ado_swarm.config import Settings


class ModelProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str = "fake"
    model_id: str = "fake-deterministic"
    base_url: str | None = None
    temperature: float = 0.0
    max_tokens: int = 2048
    api_key: str | None = None
    region: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)


class ModelGateway:
    def __init__(self, profile: ModelProfile) -> None:
        self.profile = profile


def build_model_gateway(settings: Settings) -> ModelGateway:
    return ModelGateway(
        ModelProfile(
            provider=settings.model_provider,
            model_id=settings.model_id,
            base_url=settings.model_base_url,
        )
    )
