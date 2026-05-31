"""Remediation tools — deterministic strategy baseline for `solutions_architect`."""

from __future__ import annotations

from strands import tool

from ado_swarm.contracts.casefile import NormalizedFinding


def propose_remediation_strategy_impl(finding: dict) -> dict:
    parsed = NormalizedFinding.model_validate(finding)
    if parsed.category == "dependency":
        strategy = "dependency_version_update"
        steps = [
            f"Locate dependency declaration for {parsed.package_name or 'the affected package'}.",
            "Select the smallest non-vulnerable version that satisfies project constraints.",
            "Run dependency resolution and targeted tests in an isolated sandbox.",
        ]
    elif parsed.category == "sast":
        strategy = "localized_code_fix"
        steps = [
            f"Inspect {parsed.file_path or 'the affected file'} around the reported location.",
            "Apply the smallest code change that removes the unsafe data flow.",
            "Run targeted security and unit tests before preparing review output.",
        ]
    else:
        strategy = "manual_investigation"
        steps = [
            "Collect additional evidence for the finding type.",
            "Define a bounded remediation before enabling write actions.",
        ]
    return {
        "strategy": strategy,
        "change_boundary": f"single finding {parsed.finding_id}",
        "steps": steps,
    }


@tool
def propose_remediation_strategy(finding: dict) -> dict:
    """Propose a bounded remediation strategy and steps for a finding (planning only).

    Args:
        finding: A NormalizedFinding JSON object.

    Returns:
        A JSON object with strategy, change_boundary, and steps — a baseline plan.
    """
    return propose_remediation_strategy_impl(finding)
