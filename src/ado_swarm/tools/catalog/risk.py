"""Risk tools — deterministic severity/eligibility heuristics for `risk_auditor`.

The agent decides; this tool supplies a reproducible baseline mapping the model
can adopt, adjust, or override with rationale.
"""

from __future__ import annotations

from strands import tool

from ado_swarm.contracts.casefile import NormalizedFinding
from ado_swarm.contracts.events import RiskLevel

SEVERITY_TO_RISK = {
    "critical": RiskLevel.CRITICAL,
    "high": RiskLevel.HIGH,
    "medium": RiskLevel.MEDIUM,
    "moderate": RiskLevel.MEDIUM,
    "low": RiskLevel.LOW,
    "informational": RiskLevel.LOW,
    "info": RiskLevel.LOW,
}

# Categories where a bounded, well-understood fix is usually safe to automate.
AUTOMATABLE_CATEGORIES = {"dependency"}


def score_severity_impl(finding: dict) -> dict:
    parsed = NormalizedFinding.model_validate(finding)
    severity = (parsed.severity or "").lower()
    risk = SEVERITY_TO_RISK.get(severity, RiskLevel.MEDIUM)
    automation_eligible = (
        risk in (RiskLevel.LOW, RiskLevel.MEDIUM) and parsed.category in AUTOMATABLE_CATEGORIES
    )
    return {
        "risk_level": risk.value,
        "automation_eligible": automation_eligible,
        "rationale": (
            f"severity '{severity or 'unknown'}' maps to {risk.value}; "
            f"category={parsed.category or 'unknown'}; "
            f"automation_eligible={automation_eligible}"
        ),
    }


@tool
def score_severity(finding: dict) -> dict:
    """Map a normalized finding to a baseline risk level and automation eligibility.

    Args:
        finding: A NormalizedFinding JSON object (needs at least severity and category).

    Returns:
        A JSON object: risk_level (low|medium|high|critical), automation_eligible (bool),
        and a rationale string.
    """
    return score_severity_impl(finding)
