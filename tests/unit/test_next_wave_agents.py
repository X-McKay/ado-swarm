from __future__ import annotations

import pytest

from ado_swarm.agents.data_analyst.eval import run_eval as data_analyst_eval
from ado_swarm.agents.qa_lead.eval import run_eval as qa_lead_eval
from ado_swarm.agents.repo_analyst.eval import run_eval as repo_analyst_eval
from ado_swarm.agents.risk_auditor.eval import run_eval as risk_auditor_eval
from ado_swarm.agents.security_reviewer.eval import run_eval as security_reviewer_eval
from ado_swarm.agents.software_engineer.eval import run_eval as software_engineer_eval
from ado_swarm.agents.solutions_architect.eval import run_eval as solutions_architect_eval
from ado_swarm.agents.submission_engineer.eval import run_eval as submission_engineer_eval
from ado_swarm.agents.test_engineer.eval import run_eval as test_engineer_eval
from ado_swarm.agents.ticket_analyst.eval import run_eval as ticket_analyst_eval

# Each model-driven agent's eval drives the real Strands agent loop with a scripted
# FakeModel and asserts the tool was called through the policy gate and a typed
# casefile section was produced. Running them here keeps that coverage in pytest.
MODEL_DRIVEN_EVALS = {
    "ticket_analyst": ticket_analyst_eval,
    "repo_analyst": repo_analyst_eval,
    "security_reviewer": security_reviewer_eval,
    "risk_auditor": risk_auditor_eval,
    "solutions_architect": solutions_architect_eval,
    "test_engineer": test_engineer_eval,
    "qa_lead": qa_lead_eval,
    "data_analyst": data_analyst_eval,
    "software_engineer": software_engineer_eval,
    "submission_engineer": submission_engineer_eval,
}


@pytest.mark.parametrize("agent_id", sorted(MODEL_DRIVEN_EVALS))
async def test_model_driven_agent_eval_passes(agent_id: str) -> None:
    result = await MODEL_DRIVEN_EVALS[agent_id]("fake")
    assert result["agent_id"] == agent_id
    assert result["passed"], result
