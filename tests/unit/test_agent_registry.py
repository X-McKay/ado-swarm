from ado_swarm.agents.registry import build_agent, list_agent_metadata


def test_agent_catalog_loads_all_initial_agents() -> None:
    metadata = list_agent_metadata()
    assert len(metadata) == 9
    assert {agent.id for agent in metadata} >= {"ticket_analyst", "risk_auditor"}


def test_build_agent_from_metadata() -> None:
    agent = build_agent("risk_auditor")
    assert agent.agent_id == "risk_auditor"
