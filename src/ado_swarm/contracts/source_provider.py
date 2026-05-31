from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SourceProviderKind(StrEnum):
    AZURE_DEVOPS = "azure_devops"
    GITHUB = "github"
    STUB = "stub"


class SourceRepositoryRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: SourceProviderKind
    external_id: str
    owner_or_project: str
    name: str
    default_branch: str | None = None
    clone_url: str | None = None
    web_url: str | None = None


class SourceIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: SourceProviderKind
    external_id: str
    url: str
    title: str
    body: str | None = None
    state: str = "open"
    labels: list[str] = Field(default_factory=list)
    repository: SourceRepositoryRef | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    provider_payload: dict[str, Any] = Field(default_factory=dict)


class SourceFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    repository: SourceRepositoryRef
    path: str
    ref: str
    content: str
    sha: str | None = None
    url: str | None = None


class SourcePullRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: SourceProviderKind
    external_id: str
    url: str
    title: str
    source_branch: str
    target_branch: str
    is_draft: bool = True
    provider_payload: dict[str, Any] = Field(default_factory=dict)


class ProviderMutationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: SourceProviderKind
    ok: bool
    external_id: str | None = None
    url: str | None = None
    message: str
    provider_payload: dict[str, Any] = Field(default_factory=dict)
