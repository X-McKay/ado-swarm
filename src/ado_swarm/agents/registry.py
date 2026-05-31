from __future__ import annotations

import importlib
from collections.abc import Callable
from pathlib import Path

import yaml

from ado_swarm.agents.schemas import AgentMetadata
from ado_swarm.config import get_settings
from ado_swarm.model_gateway.gateway import build_model_gateway

AGENTS_DIR = Path(__file__).parent


def list_agent_metadata() -> list[AgentMetadata]:
    metadata: list[AgentMetadata] = []
    for path in sorted(AGENTS_DIR.glob("*/metadata.yaml")):
        metadata.append(AgentMetadata.model_validate(yaml.safe_load(path.read_text())))
    return metadata


def get_agent_metadata(agent_id: str) -> AgentMetadata:
    for metadata in list_agent_metadata():
        if metadata.id == agent_id:
            return metadata
    raise KeyError(f"Unknown agent: {agent_id}")


def build_agent(agent_id: str):
    metadata = get_agent_metadata(agent_id)
    module_path, func_name = metadata.entrypoint.split(":", 1)
    module = importlib.import_module(module_path)
    factory: Callable = getattr(module, func_name)
    return factory(build_model_gateway(get_settings()))
