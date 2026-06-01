from __future__ import annotations

import pytest

from ado_swarm.config import Settings
from ado_swarm.tools.catalog.provider import provider_get_issue_impl
from ado_swarm.tools.source_providers.providers import (
    close_source_provider,
    get_source_provider,
    set_source_provider,
    set_source_provider_factory,
)
from ado_swarm.tools.source_providers.stub import StubSourceProvider


@pytest.fixture(autouse=True)
async def _reset_source_provider_registry():
    await close_source_provider()
    set_source_provider_factory(None)
    yield
    await close_source_provider()
    set_source_provider_factory(None)


class CloseTrackingProvider(StubSourceProvider):
    def __init__(self) -> None:
        super().__init__()
        self.closed = False

    async def aclose(self) -> None:
        self.closed = True


def test_get_source_provider_uses_injected_provider() -> None:
    provider = StubSourceProvider()
    set_source_provider(provider)

    assert get_source_provider() is provider


def test_get_source_provider_uses_injected_factory() -> None:
    provider = StubSourceProvider()

    def factory(settings: Settings):
        assert settings.source_provider == "stub"
        return provider

    set_source_provider_factory(factory)

    assert get_source_provider(Settings()) is provider
    assert get_source_provider(Settings()) is provider


async def test_close_source_provider_closes_cached_provider() -> None:
    provider = CloseTrackingProvider()
    set_source_provider(provider)

    await close_source_provider()

    assert provider.closed is True
    assert get_source_provider() is not provider


async def test_provider_tools_use_injected_source_provider() -> None:
    provider = StubSourceProvider()
    set_source_provider(provider)

    issue = await provider_get_issue_impl("SEC-99")

    assert issue["external_id"] == "SEC-99"
