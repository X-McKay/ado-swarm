from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from ado_swarm.contracts.events import RiskLevel
from ado_swarm.contracts.source_provider import SourceIssue, SourceRepositoryRef


class NormalizedFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    finding_id: str
    title: str
    description: str | None = None
    scanner: str | None = None
    category: str | None = None
    severity: str | None = None
    cwe: str | None = None
    package_name: str | None = None
    file_path: str | None = None
    line: int | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class RepositoryEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    repository: SourceRepositoryRef | None = None
    ref: str | None = None
    file_exists: bool | None = None
    evidence: list[str] = Field(default_factory=list)


class FindingAdjudication(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stale: bool = False
    duplicate_of: str | None = None
    false_positive: bool = False
    already_fixed: bool = False
    rationale: str
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class RiskClassification(BaseModel):
    model_config = ConfigDict(extra="forbid")

    risk_level: RiskLevel
    impact: str
    automation_eligible: bool
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    rationale: str


class RemediationPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strategy: str
    change_boundary: str
    steps: list[str]
    requires_human_approval: bool = True


class SecurityCasefile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    casefile_id: str
    run_id: str
    source_issue: SourceIssue
    normalized_finding: NormalizedFinding | None = None
    repository_evidence: RepositoryEvidence | None = None
    adjudication: FindingAdjudication | None = None
    risk: RiskClassification | None = None
    remediation_plan: RemediationPlan | None = None
    audit: dict[str, Any] = Field(default_factory=dict)
    final_disposition: Literal[
        "open",
        "stale",
        "duplicate",
        "false_positive",
        "needs_human",
        "draft_pr_created",
        "ready_for_review",
    ] = "open"
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
