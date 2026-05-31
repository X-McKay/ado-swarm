from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MissionSearchAttributes:
    run_id: str
    source_provider: str = "stub"
    repository: str | None = None
    severity: str | None = None
    mission_status: str = "created"
    agent_phase: str | None = None

    def as_keywords(self) -> dict[str, str]:
        values = {
            "RunId": self.run_id,
            "SourceProvider": self.source_provider,
            "MissionStatus": self.mission_status,
        }
        if self.repository:
            values["Repository"] = self.repository
        if self.severity:
            values["Severity"] = self.severity
        if self.agent_phase:
            values["AgentPhase"] = self.agent_phase
        return values
