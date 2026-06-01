"""Lifecycle-managed source-provider accessors.

Tool catalog functions should resolve source providers through this module rather
than constructing concrete HTTP providers directly from global settings. This
creates a single test seam, centralizes provider lifecycle management, and keeps
provider-backed tools focused on deterministic domain behavior.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import cast

from ado_swarm.config import Settings, get_settings
from ado_swarm.tools.source_providers.base import SourceProvider
from ado_swarm.tools.source_providers.factory import build_source_provider

ProviderFactory = Callable[[Settings], SourceProvider]

_provider: SourceProvider | None = None
_provider_factory: ProviderFactory = build_source_provider


def get_source_provider(settings: Settings | None = None) -> SourceProvider:
    """Return the process-local source provider, constructing it on first use."""
    global _provider
    if _provider is None:
        _provider = _provider_factory(settings or get_settings())
    return _provider


def set_source_provider(provider: SourceProvider | None) -> None:
    """Inject or clear the process-local source provider.

    Passing ``None`` clears the cached provider without closing it. Tests that own
    an injected provider remain responsible for its lifecycle.
    """
    global _provider
    _provider = provider


def set_source_provider_factory(factory: ProviderFactory | None) -> None:
    """Inject the provider factory used by ``get_source_provider``.

    Passing ``None`` restores the default settings-backed factory. The cached
    provider is cleared so the new factory is observed on the next access.
    """
    global _provider_factory
    _provider_factory = factory or build_source_provider
    set_source_provider(None)


async def close_source_provider() -> None:
    """Close and forget the cached source provider when it supports ``aclose``."""
    global _provider
    provider = _provider
    _provider = None
    close = getattr(provider, "aclose", None)
    if close is not None:
        await cast(Callable[[], Awaitable[None]], close)()
