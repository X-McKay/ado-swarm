from __future__ import annotations

from ado_swarm.contracts.artifacts import ArtifactKind, RunArtifact
from ado_swarm.contracts.budget import BudgetPolicy, BudgetUsage
from ado_swarm.contracts.checkpoints import AgentCheckpoint
from ado_swarm.contracts.events import RiskLevel
from ado_swarm.tools.policy import ApprovalState, ToolContext, ToolPolicy


def test_budget_policy_guardrails() -> None:
    policy = BudgetPolicy(max_tool_calls=2, max_model_calls=1)
    assert BudgetUsage(tool_calls=2, model_calls=1).within(policy)
    assert not BudgetUsage(tool_calls=3, model_calls=1).within(policy)


def test_tool_policy_requires_approval_for_write_tools() -> None:
    policy = ToolPolicy(["provider_create_draft_pr"], write_tools=["provider_create_draft_pr"])
    denied = policy.check(
        "provider_create_draft_pr",
        ToolContext(run_id="run-1", approval_state=ApprovalState.REQUIRED),
    )
    assert not denied.allowed
    assert denied.requires_approval
    allowed = policy.check(
        "provider_create_draft_pr",
        ToolContext(run_id="run-1", approval_state=ApprovalState.APPROVED),
    )
    assert allowed.allowed


def test_high_risk_task_requires_approval() -> None:
    policy = ToolPolicy(["scanner_run_targeted"])
    decision = policy.check(
        "scanner_run_targeted",
        ToolContext(run_id="run-1", risk_level=RiskLevel.HIGH),
    )
    assert not decision.allowed
    assert decision.requires_approval


def test_artifact_and_checkpoint_contracts_are_json_serializable() -> None:
    artifact = RunArtifact(
        run_id="run-1", kind=ArtifactKind.PLAN, name="plan", content={"ok": True}
    )
    checkpoint = AgentCheckpoint(run_id="run-1", task_id="task-1", agent_id="agent")
    assert artifact.model_dump(mode="json")["kind"] == "plan"
    assert checkpoint.model_dump(mode="json")["position"] == "activity_boundary"
