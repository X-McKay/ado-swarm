from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CampaignReport(BaseModel):
    """Cross-casefile analytics output produced by the data_analyst agent.

    Unlike the other agent outputs this is not a casefile section; it summarizes
    patterns across many findings/casefiles for the learning loop.
    """

    model_config = ConfigDict(extra="forbid")

    total_findings: int = 0
    by_category: dict[str, int] = Field(default_factory=dict)
    by_severity: dict[str, int] = Field(default_factory=dict)
    recommendations: list[str] = Field(default_factory=list)
    rationale: str = ""
