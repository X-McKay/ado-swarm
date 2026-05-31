"""Remediation tools — deterministic strategy baseline for `solutions_architect`."""

from __future__ import annotations

from strands import tool

from ado_swarm.contracts.casefile import NormalizedFinding, RemediationPlan
from ado_swarm.sandbox.provider import LocalSandboxProvider


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


def apply_remediation_change_impl(finding: dict, remediation_plan: dict) -> dict:
    """WRITE: materialize the planned change in an isolated local sandbox (dry-run).

    This never touches a real repository; it records the intended change in a
    sandbox workspace for review. It is a write-capable tool and is policy-gated
    behind approval.
    """
    parsed = NormalizedFinding.model_validate(finding)
    plan = RemediationPlan.model_validate(remediation_plan)
    target = parsed.file_path or "PLANNED_CHANGE.md"
    session = LocalSandboxProvider().create(f"remediation:{parsed.finding_id}")
    note = session.root / "PLANNED_CHANGE.md"
    note.write_text(
        f"# Planned change for {parsed.finding_id}\n\n"
        f"Strategy: {plan.strategy}\nBoundary: {plan.change_boundary}\nTarget: {target}\n\n"
        + "\n".join(f"- {step}" for step in plan.steps)
        + "\n"
    )
    return {
        "applied": True,
        "sandbox_session_id": session.session_id,
        "changed_files": [target],
        "diff_summary": f"recorded {plan.strategy} for {target} in sandbox {session.session_id}",
        "rationale": "change materialized in an isolated sandbox for review (no repo mutation)",
    }


@tool
def apply_remediation_change(finding: dict, remediation_plan: dict) -> dict:
    """Apply a remediation change in an isolated sandbox (write, approval-gated).

    Args:
        finding: A NormalizedFinding JSON object.
        remediation_plan: A RemediationPlan JSON object.

    Returns:
        A JSON object with applied, sandbox_session_id, changed_files, diff_summary, rationale.
    """
    return apply_remediation_change_impl(finding, remediation_plan)
