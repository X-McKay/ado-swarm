from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class BoundedSwarmConfig:
    swarm_id: str = "readonly-investigation"
    max_handoffs: int = 6
    max_iterations: int = 8
    execution_timeout_seconds: int = 900
    allowed_agents: tuple[str, ...] = ("ticket_analyst", "repo_analyst", "security_reviewer")
    read_only: bool = True


@dataclass
class SwarmStep:
    from_agent: str | None
    to_agent: str
    message: str
    context: dict[str, str] = field(default_factory=dict)


class BoundedSwarmExperiment:
    """Deterministic placeholder for future Strands Swarm experiments.

    This captures the governance constraints now, while richer autonomous handoff
    behavior can later be swapped in behind the same bounded configuration.
    """

    def __init__(self, config: BoundedSwarmConfig | None = None) -> None:
        self.config = config or BoundedSwarmConfig()

    def validate_step(self, step: SwarmStep, prior_steps: list[SwarmStep]) -> bool:
        if step.to_agent not in self.config.allowed_agents:
            return False
        if len(prior_steps) >= self.config.max_handoffs:
            return False
        return self.config.read_only
