from __future__ import annotations

from ado_swarm.config import get_settings
from ado_swarm.model_gateway.gateway import ModelGateway, ModelProfile


def build_eval_model_gateway(model_profile: str = "fake") -> ModelGateway:
    """Build eval gateway from the requested provider and environment settings.

    Agent eval entrypoints accept a short provider name for CLI ergonomics. For
    non-fake providers, the concrete model id and base URL must come from the
    normal runtime settings so local OpenAI-compatible, Ollama, LiteLLM, and
    Bedrock profiles work during E2E validation.
    """
    settings = get_settings()
    if model_profile == "fake":
        return ModelGateway(ModelProfile(provider="fake"))
    return ModelGateway(
        ModelProfile(
            provider=model_profile,
            model_id=settings.model_id,
            base_url=settings.model_base_url,
        )
    )
