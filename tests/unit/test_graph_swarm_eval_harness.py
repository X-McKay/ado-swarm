from __future__ import annotations

from ado_swarm.evals.backtesting import reliability_report
from ado_swarm.runtime.graph_templates import triage_readonly_graph
from ado_swarm.runtime.swarm_experiment import BoundedSwarmExperiment, SwarmStep
from ado_swarm.temporal.search_attributes import MissionSearchAttributes


def test_triage_graph_template_order_is_dependency_safe() -> None:
    graph = triage_readonly_graph()
    order = [node.node_id for node in graph.execution_order()]
    assert order == [
        "ticket_analyst",
        "repo_analyst",
        "security_reviewer",
        "risk_auditor",
        "solutions_architect",
        "test_engineer",
        "submission_engineer",
    ]
    # The submission stage is approval-gated.
    submission = next(n for n in graph.nodes if n.node_id == "submission_engineer")
    assert submission.requires_approval is True


def test_bounded_swarm_experiment_rejects_unknown_agents() -> None:
    swarm = BoundedSwarmExperiment()
    assert swarm.validate_step(SwarmStep(None, "ticket_analyst", "start"), [])
    assert not swarm.validate_step(SwarmStep(None, "software_engineer", "write code"), [])


def test_reliability_report_uses_pass_k_semantics() -> None:
    assert reliability_report([True, True, True])["recommendation"] == "promote"
    assert reliability_report([True, False, True])["recommendation"] == "hold"


def test_search_attributes_are_keyword_mapping() -> None:
    attrs = MissionSearchAttributes(run_id="run-1", repository="acme/api").as_keywords()
    assert attrs["RunId"] == "run-1"
    assert attrs["Repository"] == "acme/api"
