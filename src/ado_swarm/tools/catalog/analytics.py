"""Analytics tools — deterministic cross-finding aggregation for `data_analyst`."""

from __future__ import annotations

from strands import tool

from ado_swarm.contracts.casefile import NormalizedFinding


def summarize_findings_impl(findings: list[dict]) -> dict:
    by_category: dict[str, int] = {}
    by_severity: dict[str, int] = {}
    for raw in findings:
        finding = NormalizedFinding.model_validate(raw)
        if finding.category:
            by_category[finding.category] = by_category.get(finding.category, 0) + 1
        if finding.severity:
            by_severity[finding.severity] = by_severity.get(finding.severity, 0) + 1
    return {
        "total": len(findings),
        "by_category": by_category,
        "by_severity": by_severity,
    }


@tool
def summarize_findings(findings: list[dict]) -> dict:
    """Aggregate a set of normalized findings by category and severity.

    Args:
        findings: A list of NormalizedFinding JSON objects.

    Returns:
        A JSON object with total, by_category, and by_severity counts.
    """
    return summarize_findings_impl(findings)
