"""Structural tool-policy enforcement at the Strands tool boundary.

This is the *only* place tool authorization is enforced (skills' ``allowed-tools``
is documentation, not enforcement). The hook fires on ``BeforeToolCallEvent`` and
maps each call to a PEP/PDP decision ALLOW | DENY | REQUIRE_APPROVAL, recording
denied/approval-required tools so the runtime can surface them on ``AgentResult``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from strands.hooks import BeforeToolCallEvent, HookProvider, HookRegistry

from ado_swarm.tools.policy import ToolContext, ToolPolicy

# Harness-internal tools (e.g. the AgentSkills `skills` tool) are not domain tools
# and must never be gated by the casefile tool policy.
HARNESS_TOOLS = frozenset({"skills"})


@dataclass
class PolicyOutcome:
    denied: list[str] = field(default_factory=list)
    approval_required: list[str] = field(default_factory=list)
    allowed: list[str] = field(default_factory=list)


class ToolPolicyHook(HookProvider):
    def __init__(self, policy: ToolPolicy, context: ToolContext) -> None:
        self.policy = policy
        self.context = context
        self.outcome = PolicyOutcome()

    def register_hooks(self, registry: HookRegistry, **kwargs: Any) -> None:
        registry.add_callback(BeforeToolCallEvent, self.gate)

    def gate(self, event: BeforeToolCallEvent) -> None:
        name = event.tool_use["name"]
        if name in HARNESS_TOOLS:
            return
        decision = self.policy.check(name, self.context)
        if decision.allowed:
            self.outcome.allowed.append(name)
            return
        if decision.requires_approval:
            self.outcome.approval_required.append(name)
            event.cancel_tool = f"approval-required: {decision.reason}"
        else:
            self.outcome.denied.append(name)
            event.cancel_tool = f"denied: {decision.reason}"
