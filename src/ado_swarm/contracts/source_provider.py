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
    # ``external_id`` is the provider's canonical, round-trippable identifier for the
    # issue/work item — the exact value that ``get_issue(external_id)`` accepts back.
    #   - azure_devops: the numeric work-item id (e.g. "4821").
    #   - github: a repo-qualified id "{owner}/{repo}#{number}" when the repository is
    #     known, otherwise the bare issue number. ``add_issue_comment`` accepts either.
    #   - stub: an opaque echo id.
    # Always pass ``SourceIssue.external_id`` back to provider methods verbatim; never
    # re-derive an id from other fields.
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


class SourceIssuePage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: SourceProviderKind
    items: list[SourceIssue]
    query: str
    limit: int


class SourceFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    repository: SourceRepositoryRef
    path: str
    ref: str
    content: str
    sha: str | None = None
    url: str | None = None


class SourceBranch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    repository: SourceRepositoryRef
    name: str
    sha: str | None = None
    protected: bool = False
    provider_payload: dict[str, Any] = Field(default_factory=dict)


class SourceCommit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    repository: SourceRepositoryRef
    sha: str
    message: str
    author: str | None = None
    committed_at: datetime | None = None
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
    state: str = "open"
    provider_payload: dict[str, Any] = Field(default_factory=dict)


class MutationResultKind(StrEnum):
    """What ``ProviderMutationResult.external_id`` identifies for a mutation."""

    ISSUE_COMMENT = "issue_comment"
    PR_COMMENT = "pr_comment"
    PULL_REQUEST = "pull_request"


class ProviderMutationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: SourceProviderKind
    ok: bool
    # ``result_kind`` pins what ``external_id`` refers to (the created comment, the
    # created PR, ...), so callers don't have to guess per-provider. ``external_id``
    # is the id of the *thing created* by the mutation, not its parent.
    result_kind: MutationResultKind
    external_id: str | None = None
    url: str | None = None
    message: str
    provider_payload: dict[str, Any] = Field(default_factory=dict)
