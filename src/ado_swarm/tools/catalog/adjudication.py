"""Adjudication tools — deterministic stale/false-positive signals for `security_reviewer`."""

from __future__ import annotations

from strands import tool

from ado_swarm.contracts.casefile import NormalizedFinding, RepositoryEvidence


def adjudication_signals_impl(finding: dict, repository_evidence: dict | None = None) -> dict:
    parsed = NormalizedFinding.model_validate(finding)
    evidence = (
        RepositoryEvidence.model_validate(repository_evidence) if repository_evidence else None
    )
    stale = bool(parsed.file_path and evidence and evidence.file_exists is False)
    false_positive = parsed.confidence < 0.5
    already_fixed = stale
    reasons: list[str] = []
    if stale:
        reasons.append("repository evidence indicates the referenced file is absent")
    if false_positive:
        reasons.append("normalization confidence is below the adjudication threshold")
    if not reasons:
        reasons.append("repository evidence does not prove the finding is stale or false positive")
    confidence = 0.85 if stale or false_positive else min(0.9, max(0.55, parsed.confidence))
    return {
        "stale": stale,
        "false_positive": false_positive,
        "already_fixed": already_fixed,
        "duplicate_of": None,
        "rationale": "; ".join(reasons),
        "confidence": confidence,
    }


@tool
def adjudication_signals(finding: dict, repository_evidence: dict | None = None) -> dict:
    """Compute deterministic stale / false-positive / already-fixed signals for a finding.

    Args:
        finding: A NormalizedFinding JSON object.
        repository_evidence: Optional RepositoryEvidence JSON object (file_exists matters).

    Returns:
        A JSON object with stale, false_positive, already_fixed, duplicate_of, rationale,
        and confidence — a baseline the reviewer can adopt or override.
    """
    return adjudication_signals_impl(finding, repository_evidence)
