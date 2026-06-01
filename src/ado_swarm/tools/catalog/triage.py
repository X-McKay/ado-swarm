"""Triage tools — deterministic normalization exposed to model-driven agents.

Per `docs/concepts/agents-tools-skills.md`, the deterministic normalizer is a
*tool* the `ticket_analyst` agent calls; the agent supplies the judgment on
messy/ambiguous issues. The underlying logic is the well-tested
`normalize_source_issue` domain function.
"""

from __future__ import annotations

from strands import tool

from ado_swarm.agents.ticket_analyst.normalization import normalize_source_issue
from ado_swarm.contracts.source_provider import SourceIssue


def normalize_finding_impl(issue: dict) -> dict:
    source_issue = SourceIssue.model_validate(issue)
    return normalize_source_issue(source_issue).model_dump(mode="json")


@tool
def normalize_finding(issue: dict) -> dict:
    """Deterministically normalize a provider security issue into a canonical finding.

    Args:
        issue: A SourceIssue as a JSON object with fields like provider, external_id,
            title, body, labels, and provider_payload.

    Returns:
        A NormalizedFinding JSON object: finding_id, title, severity, scanner, category,
        cwe, package_name, file_path, line, and a confidence score.
    """
    return normalize_finding_impl(issue)
