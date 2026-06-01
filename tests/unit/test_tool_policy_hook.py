from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, cast

from strands.hooks import BeforeToolCallEvent

from ado_swarm.contracts.events import RiskLevel
from ado_swarm.tools.policy import ApprovalState, ToolContext, ToolPolicy
from ado_swarm.tools.policy_hook import ToolPolicyHook


@dataclass
class _Event:
    """Minimal stand-in for BeforeToolCallEvent (gate only reads tool_use, sets cancel_tool)."""

    tool_use: dict[str, Any]
    cancel_tool: Any = field(default=None)


def _gate(hook: ToolPolicyHook, name: str) -> _Event:
    event = _Event(tool_use={"name": name})
    hook.gate(cast(BeforeToolCallEvent, event))
    return event


def test_allowed_tool_passes() -> None:
    hook = ToolPolicyHook(ToolPolicy(["normalize_finding"]), ToolContext(run_id="r1"))
    event = _gate(hook, "normalize_finding")
    assert event.cancel_tool is None
    assert hook.outcome.allowed == ["normalize_finding"]


def test_unlisted_tool_is_denied() -> None:
    hook = ToolPolicyHook(ToolPolicy(["normalize_finding"]), ToolContext(run_id="r1"))
    event = _gate(hook, "git_write")
    assert isinstance(event.cancel_tool, str) and event.cancel_tool.startswith("denied:")
    assert hook.outcome.denied == ["git_write"]


def test_write_tool_requires_approval() -> None:
    policy = ToolPolicy(["provider_create_draft_pr"], write_tools=["provider_create_draft_pr"])
    hook = ToolPolicyHook(policy, ToolContext(run_id="r1", approval_state=ApprovalState.REQUIRED))
    event = _gate(hook, "provider_create_draft_pr")
    assert event.cancel_tool.startswith("approval-required:")
    assert hook.outcome.approval_required == ["provider_create_draft_pr"]


def test_write_tool_allowed_after_approval() -> None:
    policy = ToolPolicy(["provider_create_draft_pr"], write_tools=["provider_create_draft_pr"])
    hook = ToolPolicyHook(policy, ToolContext(run_id="r1", approval_state=ApprovalState.APPROVED))
    event = _gate(hook, "provider_create_draft_pr")
    assert event.cancel_tool is None


def test_high_risk_requires_approval() -> None:
    hook = ToolPolicyHook(
        ToolPolicy(["score_severity"]),
        ToolContext(run_id="r1", risk_level=RiskLevel.HIGH),
    )
    event = _gate(hook, "score_severity")
    assert event.cancel_tool.startswith("approval-required:")


def test_harness_skills_tool_bypasses_policy() -> None:
    # The AgentSkills `skills` tool must never be gated by the casefile policy.
    hook = ToolPolicyHook(ToolPolicy([]), ToolContext(run_id="r1"))
    event = _gate(hook, "skills")
    assert event.cancel_tool is None
    assert hook.outcome.denied == []
