from __future__ import annotations

import json
from pathlib import Path

import pytest

from ado_swarm.contracts.source_provider import SourceIssue
from ado_swarm.tools.catalog import CATALOG, get_tools, tool_names
from ado_swarm.tools.catalog.repository import (
    resolve_repository_impl,
    verify_file_location_impl,
)
from ado_swarm.tools.catalog.risk import score_severity_impl
from ado_swarm.tools.catalog.triage import normalize_finding_impl

FIXTURE = Path(__file__).parent.parent / "fixtures" / "source_issues" / "codeql_sast.json"


def _issue() -> dict:
    return json.loads(FIXTURE.read_text())


def test_catalog_registry_resolves_and_rejects() -> None:
    assert set(tool_names()) == set(CATALOG)
    resolved = get_tools(["normalize_finding", "score_severity"])
    assert len(resolved) == 2
    with pytest.raises(KeyError):
        get_tools(["does_not_exist"])


def test_normalize_finding_tool_is_deterministic() -> None:
    issue = _issue()
    first = normalize_finding_impl(issue)
    second = normalize_finding_impl(issue)
    assert first == second
    assert first["finding_id"].startswith("finding-")
    # The @tool wrapper is directly callable and returns the same payload.
    assert CATALOG["normalize_finding"](issue) == first


def test_resolve_repository_tool() -> None:
    issue = _issue()
    result = resolve_repository_impl(issue)
    src = SourceIssue.model_validate(issue)
    if src.repository is None:
        assert result["resolved"] is False
    else:
        assert result["resolved"] is True
        assert result["repository"]["name"] == src.repository.name


def test_score_severity_tool_maps_levels() -> None:
    high = score_severity_impl({"finding_id": "f1", "title": "t", "severity": "high"})
    assert high["risk_level"] == "high"
    low_dep = score_severity_impl(
        {"finding_id": "f2", "title": "t", "severity": "low", "category": "dependency"}
    )
    assert low_dep["risk_level"] == "low"
    assert low_dep["automation_eligible"] is True
    unknown = score_severity_impl({"finding_id": "f3", "title": "t"})
    assert unknown["risk_level"] == "medium"
    assert unknown["automation_eligible"] is False


async def test_verify_file_location_tool_uses_stub_provider() -> None:
    # Default settings use the stub provider, which returns a deterministic file.
    repo = {
        "provider": "stub",
        "external_id": "repo-1",
        "owner_or_project": "acme",
        "name": "service",
        "default_branch": "main",
    }
    result = await verify_file_location_impl(repo, "src/app.py", "main")
    assert "file_exists" in result
    assert isinstance(result["evidence"], list) and result["evidence"]
