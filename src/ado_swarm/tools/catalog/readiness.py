"""Readiness tools — deterministic phase-readiness signals for `qa_lead`."""

from __future__ import annotations

from strands import tool

from ado_swarm.contracts.casefile import SecurityCasefile


def assess_readiness_impl(casefile: dict) -> dict:
    parsed = SecurityCasefile.model_validate(casefile)
    blocking: list[str] = []
    if parsed.normalized_finding is None:
        blocking.append("missing normalized finding")
    if parsed.repository_evidence is None:
        blocking.append("missing repository evidence")
    if parsed.adjudication is None:
        blocking.append("missing adjudication")
    if parsed.risk is None:
        blocking.append("missing risk classification")
    ready = not blocking
    next_phase = "remediation-planning" if ready else "triage"
    return {
        "ready": ready,
        "next_phase": next_phase,
        "blocking_reasons": blocking,
        "rationale": (
            "all read-only triage sections are populated"
            if ready
            else f"{len(blocking)} casefile section(s) still missing"
        ),
    }


@tool
def assess_readiness(casefile: dict) -> dict:
    """Assess whether a casefile has the sections needed to advance to the next phase.

    Args:
        casefile: A SecurityCasefile JSON object.

    Returns:
        A JSON object with ready (bool), next_phase, blocking_reasons, and rationale.
    """
    return assess_readiness_impl(casefile)
