from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

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
    params: dict[str, Any] = {}


class ModelGateway:
    def __init__(self, profile: ModelProfile) -> None:
        self.profile = profile

    async def complete(self, prompt: str) -> str:
        if self.profile.provider == "fake":
            return f"[fake:{self.profile.model_id}] {prompt[:500]}"
        if self.profile.provider == "ollama":
            return await self._complete_ollama(prompt)
        if self.profile.provider == "openai_compatible":
            return await self._complete_openai_compatible(prompt)
        if self.profile.provider == "litellm":
            return await self._complete_litellm(prompt)
        if self.profile.provider == "bedrock":
            return await self._complete_bedrock(prompt)
        raise ValueError(f"Unsupported model provider: {self.profile.provider}")

    async def _complete_ollama(self, prompt: str) -> str:
        import ollama

        client = ollama.AsyncClient(host=self.profile.base_url)
        response = await client.chat(
            model=self.profile.model_id,
            messages=[{"role": "user", "content": prompt}],
            options={
                "temperature": self.profile.temperature,
                "num_predict": self.profile.max_tokens,
            },
        )
        return response["message"]["content"]

    async def _complete_openai_compatible(self, prompt: str) -> str:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key="not-needed", base_url=self.profile.base_url)
        response = await client.chat.completions.create(
            model=self.profile.model_id,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.profile.temperature,
            max_tokens=self.profile.max_tokens,
        )
        return response.choices[0].message.content or ""

    async def _complete_litellm(self, prompt: str) -> str:
        import litellm

        kwargs: dict[str, Any] = {}
        if self.profile.base_url:
            kwargs["api_base"] = self.profile.base_url
        response = await litellm.acompletion(
            model=self.profile.model_id,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.profile.temperature,
            max_tokens=self.profile.max_tokens,
            **kwargs,
        )
        return response["choices"][0]["message"]["content"]

    async def _complete_bedrock(self, prompt: str) -> str:
        import asyncio

        import boto3

        def invoke() -> str:
            client = boto3.client("bedrock-runtime")
            response = client.converse(
                modelId=self.profile.model_id,
                messages=[{"role": "user", "content": [{"text": prompt}]}],
                inferenceConfig={
                    "temperature": self.profile.temperature,
                    "maxTokens": self.profile.max_tokens,
                },
            )
            return response["output"]["message"]["content"][0]["text"]

        return await asyncio.to_thread(invoke)


def build_model_gateway(settings: Settings) -> ModelGateway:
    return ModelGateway(
        ModelProfile(
            provider=settings.model_provider,
            model_id=settings.model_id,
            base_url=settings.model_base_url,
        )
    )
