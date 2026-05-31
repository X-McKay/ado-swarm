from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from ado_swarm.contracts.events import RiskLevel


class ApprovalState(StrEnum):
    NOT_REQUIRED = "not_required"
    REQUIRED = "required"
    APPROVED = "approved"
    REJECTED = "rejected"


class ToolRisk(StrEnum):
    READ = "read"
    WRITE = "write"
    MUTATION = "mutation"
    DESTRUCTIVE = "destructive"


@dataclass(frozen=True)
class ToolContext:
    run_id: str
    task_id: str | None = None
    agent_id: str | None = None
    phase: str | None = None
    risk_level: RiskLevel = RiskLevel.LOW
    approval_state: ApprovalState = ApprovalState.NOT_REQUIRED
    provider: str | None = None
    repository: str | None = None
    dry_run: bool = True


@dataclass(frozen=True)
class ToolDecision:
    allowed: bool
    reason: str
    requires_approval: bool = False
    metadata: dict[str, str] = field(default_factory=dict)


class ToolPolicy:
    def __init__(
        self,
        allowed_tools: list[str],
        *,
        write_tools: list[str] | None = None,
        destructive_tools: list[str] | None = None,
    ) -> None:
        self.allowed_tools = set(allowed_tools)
        self.write_tools = set(write_tools or [])
        self.destructive_tools = set(destructive_tools or [])

    def check(self, tool_name: str, context: ToolContext | None = None) -> ToolDecision:
        if tool_name not in self.allowed_tools:
            return ToolDecision(False, f"Tool {tool_name} is not allowed for this task")
        context = context or ToolContext(run_id="unknown")
        if tool_name in self.destructive_tools:
            return ToolDecision(False, f"Tool {tool_name} is destructive and disabled", True)
        if tool_name in self.write_tools and context.approval_state != ApprovalState.APPROVED:
            return ToolDecision(
                False,
                f"Tool {tool_name} requires approval before write execution",
                True,
            )
        if (
            context.risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL}
            and context.approval_state != ApprovalState.APPROVED
        ):
            return ToolDecision(False, "High-risk task requires approval", True)
        return ToolDecision(True, "allowed", False, {"dry_run": str(context.dry_run)})
