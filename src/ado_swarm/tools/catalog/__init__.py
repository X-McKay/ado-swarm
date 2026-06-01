"""Tool catalog — the deterministic capabilities agents call.

Agents declare the tools they need by name; `get_tools` resolves them. Keeping a
single registry (rather than importing tools ad hoc in each agent) makes the
available surface discoverable and lets the policy layer reason about it.
"""

from __future__ import annotations

from typing import Any

from ado_swarm.tools.catalog.adjudication import adjudication_signals
from ado_swarm.tools.catalog.analytics import summarize_findings
from ado_swarm.tools.catalog.knowledge import graphiti_add_episode, graphiti_search
from ado_swarm.tools.catalog.provider import (
    provider_get_issue,
    provider_get_repo_metadata,
    provider_search_issues,
)
from ado_swarm.tools.catalog.provider_write import (
    provider_add_issue_comment,
    provider_add_pr_comment,
    provider_create_draft_pr,
)
from ado_swarm.tools.catalog.readiness import assess_readiness
from ado_swarm.tools.catalog.remediation import (
    apply_remediation_change,
    propose_remediation_strategy,
)
from ado_swarm.tools.catalog.repository import (
    repo_grep,
    repo_parse_manifest,
    resolve_repository,
    verify_file_location,
)
from ado_swarm.tools.catalog.risk import score_severity
from ado_swarm.tools.catalog.triage import normalize_finding
from ado_swarm.tools.catalog.validation import propose_validation_checks
from ado_swarm.tools.catalog.verification import run_validation_command

CATALOG: dict[str, Any] = {
    "normalize_finding": normalize_finding,
    "resolve_repository": resolve_repository,
    "verify_file_location": verify_file_location,
    "repo_grep": repo_grep,
    "repo_parse_manifest": repo_parse_manifest,
    "score_severity": score_severity,
    "adjudication_signals": adjudication_signals,
    "propose_remediation_strategy": propose_remediation_strategy,
    "propose_validation_checks": propose_validation_checks,
    "assess_readiness": assess_readiness,
    "summarize_findings": summarize_findings,
    "apply_remediation_change": apply_remediation_change,
    # Verification governor (sandboxed, allowlisted command execution)
    "run_validation_command": run_validation_command,
    # Knowledge (graph-memory) tools
    "graphiti_search": graphiti_search,
    "graphiti_add_episode": graphiti_add_episode,
    # Provider read tools
    "provider_get_issue": provider_get_issue,
    "provider_search_issues": provider_search_issues,
    "provider_get_repo_metadata": provider_get_repo_metadata,
    # Provider write tools (approval-gated; declare in an agent's write_tool_names)
    "provider_create_draft_pr": provider_create_draft_pr,
    "provider_add_issue_comment": provider_add_issue_comment,
    "provider_add_pr_comment": provider_add_pr_comment,
}


def get_tools(names: list[str]) -> list[Any]:
    """Resolve tool names to their callable tool objects.

    Raises KeyError on an unknown tool so a misconfigured agent fails loudly.
    """
    missing = [name for name in names if name not in CATALOG]
    if missing:
        raise KeyError(f"Unknown tools requested: {missing}. Known: {sorted(CATALOG)}")
    return [CATALOG[name] for name in names]


def tool_names() -> list[str]:
    return sorted(CATALOG)


__all__ = ["CATALOG", "get_tools", "tool_names"]
