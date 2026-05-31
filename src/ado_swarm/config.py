from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    log_level: str = "INFO"
    temporal_address: str = "localhost:7233"
    temporal_namespace: str = "default"
    temporal_task_queue: str = "ado-swarm"
    database_url: str = "postgresql://ado_swarm:ado_swarm@localhost:5432/ado_swarm"
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = Field(default="", repr=False)
    source_provider: Literal["stub", "azure_devops", "github"] = "stub"
    model_provider: Literal["fake", "ollama", "openai_compatible", "bedrock", "litellm"] = "fake"
    model_id: str = "fake-deterministic"
    model_base_url: str | None = None
    security_reviewer_use_swarm: bool = False
    adjudication_swarm_max_model_calls: int = 8
    ado_org_url: str | None = None
    ado_project: str | None = None
    ado_pat: str | None = Field(default=None, repr=False)
    github_token: str | None = Field(default=None, repr=False)
    github_owner: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
