from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from ado_swarm.config import Settings


class ModelProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str = "fake"
    model_id: str = "fake-deterministic"
    base_url: str | None = None
    temperature: float = 0.0
    max_tokens: int = 2048


class ModelGateway:
    def __init__(self, profile: ModelProfile) -> None:
        self.profile = profile

    async def complete(self, prompt: str) -> str:
        if self.profile.provider == "fake":
            return f"[fake:{self.profile.model_id}] {prompt[:500]}"
        raise NotImplementedError(
            f"Model provider {self.profile.provider!r} is configured "
            "but not enabled in the base runtime yet."
        )


def build_model_gateway(settings: Settings) -> ModelGateway:
    return ModelGateway(
        ModelProfile(
            provider=settings.model_provider,
            model_id=settings.model_id,
            base_url=settings.model_base_url,
        )
    )
