"""Tool catalog — the deterministic capabilities agents call.

Agents declare the tools they need by name; `get_tools` resolves them. Keeping a
single registry (rather than importing tools ad hoc in each agent) makes the
available surface discoverable and lets the policy layer reason about it.
"""

from __future__ import annotations

from typing import Any

from ado_swarm.tools.catalog.adjudication import adjudication_signals
from ado_swarm.tools.catalog.remediation import propose_remediation_strategy
from ado_swarm.tools.catalog.repository import resolve_repository, verify_file_location
from ado_swarm.tools.catalog.risk import score_severity
from ado_swarm.tools.catalog.triage import normalize_finding
from ado_swarm.tools.catalog.validation import propose_validation_checks

CATALOG: dict[str, Any] = {
    "normalize_finding": normalize_finding,
    "resolve_repository": resolve_repository,
    "verify_file_location": verify_file_location,
    "score_severity": score_severity,
    "adjudication_signals": adjudication_signals,
    "propose_remediation_strategy": propose_remediation_strategy,
    "propose_validation_checks": propose_validation_checks,
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
