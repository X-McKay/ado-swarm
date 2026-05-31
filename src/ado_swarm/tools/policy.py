from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ToolDecision:
    allowed: bool
    reason: str


class ToolPolicy:
    def __init__(self, allowed_tools: set[str] | None = None) -> None:
        self.allowed_tools = allowed_tools or set()

    def check(self, tool_name: str) -> ToolDecision:
        if tool_name in self.allowed_tools:
            return ToolDecision(True, "tool allowed by agent metadata and phase policy")
        return ToolDecision(False, f"tool {tool_name!r} is not allowed in this context")
