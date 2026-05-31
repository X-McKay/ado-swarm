from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field


class BudgetPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_agent_loops: int = 8
    max_tool_calls: int = 30
    max_model_calls: int = 12
    max_input_tokens: int | None = None
    max_output_tokens: int | None = None
    max_wall_seconds: int = 1800
    max_estimated_cost_usd: float | None = None


class BudgetUsage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_loops: int = 0
    tool_calls: int = 0
    model_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    elapsed_seconds: float = 0.0
    estimated_cost_usd: float = 0.0
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def within(self, policy: BudgetPolicy) -> bool:
        if self.agent_loops > policy.max_agent_loops:
            return False
        if self.tool_calls > policy.max_tool_calls:
            return False
        if self.model_calls > policy.max_model_calls:
            return False
        if policy.max_input_tokens is not None and self.input_tokens > policy.max_input_tokens:
            return False
        if policy.max_output_tokens is not None and self.output_tokens > policy.max_output_tokens:
            return False
        if self.elapsed_seconds > policy.max_wall_seconds:
            return False
        return not (
            policy.max_estimated_cost_usd is not None
            and self.estimated_cost_usd > policy.max_estimated_cost_usd
        )
