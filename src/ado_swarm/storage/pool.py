"""Shared asyncpg connection pool.

The Postgres stores (`storage.artifacts`, `storage.checkpoints`) acquire
connections from a process-wide pool keyed by ``database_url`` instead of
opening a fresh connection per call. Pools are created lazily on first use and
can be injected (for tests) or closed (on shutdown).
"""

from __future__ import annotations

import asyncpg

from ado_swarm.config import get_settings

# One pool per distinct database URL. Keyed so a process talking to multiple
# databases (or a test pointing at a throwaway one) does not share connections.
_pools: dict[str, asyncpg.Pool] = {}


def resolve_database_url(database_url: str | None = None) -> str:
    """Return the explicit URL or fall back to settings."""
    return database_url or get_settings().database_url


async def get_pool(database_url: str | None = None) -> asyncpg.Pool:
    """Return the shared pool for ``database_url``, creating it on first use."""
    url = resolve_database_url(database_url)
    pool = _pools.get(url)
    if pool is None:
        pool = await asyncpg.create_pool(dsn=url)
        _pools[url] = pool
    return pool


def set_pool(database_url: str | None, pool: asyncpg.Pool | None) -> None:
    """Inject (or clear) the pool for ``database_url``.

    Passing ``pool=None`` removes any cached pool without closing it; callers
    that own the pool are responsible for closing it.
    """
    url = resolve_database_url(database_url)
    if pool is None:
        _pools.pop(url, None)
    else:
        _pools[url] = pool


async def close_pools() -> None:
    """Close and forget every cached pool (call on shutdown)."""
    pools = list(_pools.values())
    _pools.clear()
    for pool in pools:
        await pool.close()
