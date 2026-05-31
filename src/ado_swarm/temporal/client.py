from __future__ import annotations

from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter

from ado_swarm.config import Settings, get_settings


async def build_temporal_client(settings: Settings | None = None) -> Client:
    """Create the canonical Temporal client used by API, CLI, workers, and tests."""
    settings = settings or get_settings()
    return await Client.connect(
        settings.temporal_address,
        namespace=settings.temporal_namespace,
        data_converter=pydantic_data_converter,
    )
