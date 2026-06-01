"""Validation tools — deterministic validation-checklist baseline for `test_engineer`."""

from __future__ import annotations

from strands import tool

from ado_swarm.contracts.casefile import NormalizedFinding, RemediationPlan


def propose_validation_checks_impl(finding: dict, remediation_plan: dict | None = None) -> dict:
    parsed = NormalizedFinding.model_validate(finding)
    plan = RemediationPlan.model_validate(remediation_plan) if remediation_plan else None
    checks: list[str] = []
    if parsed.file_path:
        checks.append(f"targeted test or scanner coverage for {parsed.file_path}")
    if parsed.package_name:
        checks.append(f"dependency resolution check for {parsed.package_name}")
    checks.append("full project quality gate before PR creation")
    ready = bool(plan and not plan.requires_human_approval)
    return {
        "recommended_checks": checks,
        "ready_for_review": ready,
        "rationale": (
            "validation passes and remediation needs no human approval"
            if ready
            else "human approval is required before this finding is ready for review"
        ),
    }


@tool
def propose_validation_checks(finding: dict, remediation_plan: dict | None = None) -> dict:
    """Propose validation/build checks and readiness for a finding (read-only).

    Args:
        finding: A NormalizedFinding JSON object.
        remediation_plan: Optional RemediationPlan JSON object (its approval flag matters).

    Returns:
        A JSON object with recommended_checks, ready_for_review, and rationale.
    """
    return propose_validation_checks_impl(finding, remediation_plan)
