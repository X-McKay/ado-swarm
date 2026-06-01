from __future__ import annotations

import asyncio
from typing import Any, Protocol, Self

import httpx

from ado_swarm.contracts.source_provider import (
    ProviderMutationResult,
    SourceBranch,
    SourceCommit,
    SourceFile,
    SourceIssue,
    SourceIssuePage,
    SourcePullRequest,
    SourceRepositoryRef,
)


class ProviderError(RuntimeError):
    """Domain error raised when a source provider HTTP call fails.

    Wraps both ``httpx.HTTPStatusError`` (non-2xx responses) and transport-level
    errors so callers never have to depend on ``httpx`` directly.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        provider: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.provider = provider


class SourceProvider(Protocol):
    provider_name: str

    async def get_issue(self, external_id: str) -> SourceIssue: ...

    async def search_issues(self, query: str, *, limit: int = 50) -> SourceIssuePage: ...

    async def add_issue_comment(self, external_id: str, body: str) -> ProviderMutationResult: ...

    async def get_repository(self, owner_or_project: str, name: str) -> SourceRepositoryRef: ...

    async def list_branches(
        self, repository: SourceRepositoryRef, *, limit: int = 100
    ) -> list[SourceBranch]: ...

    async def get_file(
        self, repository: SourceRepositoryRef, path: str, ref: str
    ) -> SourceFile: ...

    async def list_commits(
        self, repository: SourceRepositoryRef, path: str, *, ref: str = "main", limit: int = 20
    ) -> list[SourceCommit]: ...

    async def create_draft_pr(
        self,
        repository: SourceRepositoryRef,
        title: str,
        source_branch: str,
        target_branch: str,
        body: str,
    ) -> SourcePullRequest: ...

    async def add_pr_comment(
        self, repository: SourceRepositoryRef, pr_external_id: str, body: str
    ) -> ProviderMutationResult: ...


class HttpProviderMixin:
    """Shared lifecycle + request handling for httpx-backed providers.

    Subclasses must set ``self.client`` (an ``httpx.AsyncClient``) and
    ``provider_name`` during ``__init__``.
    """

    client: httpx.AsyncClient
    provider_name: str

    # Bounded retry policy for HTTP 429 responses.
    _max_retries: int = 3
    _default_retry_after: float = 1.0
    _max_retry_after: float = 30.0

    async def aclose(self) -> None:
        """Close the underlying HTTP client. Safe to call multiple times."""
        await self.client.aclose()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()

    def _retry_after_seconds(self, response: httpx.Response, attempt: int) -> float:
        header = response.headers.get("Retry-After")
        if header is not None:
            try:
                delay = float(header)
            except ValueError:
                delay = self._default_retry_after
        else:
            # Exponential backoff fallback when the server gives no hint.
            delay = self._default_retry_after * (2**attempt)
        return min(max(delay, 0.0), self._max_retry_after)

    async def _request(self, method: str, url: str, **kwargs: Any) -> Any:
        """Perform a request, retry bounded on 429, return parsed JSON.

        Raises ``ProviderError`` on persistent HTTP error or transport failure.
        """
        response = await self._raw_request(method, url, **kwargs)
        return self._json_or_raise(response, method, url)

    def _json_or_raise(self, response: httpx.Response, method: str, url: str) -> Any:
        """Validate ``response`` and return parsed JSON or raise ``ProviderError``.

        Exposed separately so paginated callers can read response headers
        (e.g. continuation tokens / Link) before decoding the body.
        """
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ProviderError(
                f"{self.provider_name} {method} {url} failed: {exc.response.status_code}",
                status_code=exc.response.status_code,
                provider=self.provider_name,
            ) from exc
        try:
            return response.json()
        except ValueError as exc:
            raise ProviderError(
                f"{self.provider_name} {method} {url} returned invalid JSON",
                status_code=response.status_code,
                provider=self.provider_name,
            ) from exc

    async def _raw_request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        """Send a request, retrying on HTTP 429. Returns the final response."""
        last_response: httpx.Response | None = None
        for attempt in range(self._max_retries + 1):
            try:
                response = await self.client.request(method, url, **kwargs)
            except httpx.TransportError as exc:
                raise ProviderError(
                    f"{self.provider_name} {method} {url} transport error: {exc}",
                    provider=self.provider_name,
                ) from exc
            if response.status_code != 429 or attempt == self._max_retries:
                return response
            last_response = response
            await asyncio.sleep(self._retry_after_seconds(response, attempt))
        # Unreachable in practice; the loop always returns on the final attempt.
        assert last_response is not None
        return last_response
