"""Concrete Strands model provider factory functions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ado_swarm.model_gateway.gateway import ModelProfile

if TYPE_CHECKING:
    from strands.models import Model as StrandsModel


def build_provider_model(profile: ModelProfile, *, fake_model_factory: Any) -> StrandsModel:
    """Build a concrete Strands model for a profile.

    ``fake_model_factory`` is injected so this module does not import the fake
    implementation, keeping provider construction independent of test streaming
    behavior.
    """
    provider = profile.provider

    if provider == "fake":
        return fake_model_factory(profile)

    if provider == "ollama":
        from strands.models.ollama import OllamaModel

        return OllamaModel(host=profile.base_url, model_id=profile.model_id)

    if provider in ("openai", "openai_compatible"):
        from strands.models.openai import OpenAIModel

        return OpenAIModel(
            client_args={
                "api_key": profile.api_key or "not-needed",
                "base_url": profile.base_url,
            },
            model_id=profile.model_id,
            params=profile.params
            or {"temperature": profile.temperature, "max_tokens": profile.max_tokens},
        )

    if provider == "litellm":
        from strands.models.litellm import LiteLLMModel

        return LiteLLMModel(model_id=profile.model_id)

    if provider == "bedrock":
        from strands.models import BedrockModel

        return BedrockModel(model_id=profile.model_id, region_name=profile.region)

    raise ValueError(f"Unsupported model provider: {provider}")
