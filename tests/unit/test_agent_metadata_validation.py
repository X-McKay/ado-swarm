"""Vocabulary guardrail (docs/concepts/agents-tools-skills.md §6.4).

Enforces that the agent catalog cannot drift away from the core rule: a
model-driven agent declares valid skills (from the SKILL.md catalog) and valid
tools (from the tool catalog), and emits a typed section. Skills are single-
sourced from metadata, so the metadata must reference real skills.
"""

from __future__ import annotations

import pytest

from ado_swarm.agents.casefile_agent import CasefileAgent
from ado_swarm.agents.eval_support import build_eval_model_gateway
from ado_swarm.agents.registry import build_agent, list_agent_metadata
from ado_swarm.skills.loader import list_skills
from ado_swarm.tools.catalog import tool_names

AGENT_IDS = [m.id for m in list_agent_metadata()]


@pytest.mark.parametrize("agent_id", AGENT_IDS)
def test_metadata_skills_exist_in_catalog(agent_id: str) -> None:
    metadata = next(m for m in list_agent_metadata() if m.id == agent_id)
    known_skills = set(list_skills())
    missing = [s for s in metadata.skills if s not in known_skills]
    assert not missing, f"{agent_id} references unknown skills: {missing}"


@pytest.mark.parametrize("agent_id", AGENT_IDS)
def test_model_driven_agents_declare_valid_tools_and_skills(agent_id: str) -> None:
    agent = build_agent(agent_id, model_gateway=build_eval_model_gateway("fake"))
    # The core rule: every agent is model-driven with ≥1 tool, all from the catalog.
    assert getattr(agent, "tool_names", None), f"{agent_id} declares no tools"
    unknown = [t for t in agent.tool_names if t not in tool_names()]
    assert not unknown, f"{agent_id} declares unknown tools: {unknown}"
    # Skills are single-sourced from metadata by the registry.
    assert agent.skill_names, f"{agent_id} resolved no skills from metadata"
    # Casefile agents additionally emit exactly one typed section.
    if isinstance(agent, CasefileAgent):
        assert agent.section_model is not None, f"{agent_id} declares no section_model"
        assert agent.section_field, f"{agent_id} declares no section_field"
