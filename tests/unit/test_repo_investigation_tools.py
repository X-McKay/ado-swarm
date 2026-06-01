from __future__ import annotations

from ado_swarm.tools.catalog import CATALOG
from ado_swarm.tools.catalog.repository import (
    git_log_path_impl,
    parse_manifest_impl,
    repo_grep_impl,
    repo_parse_manifest_impl,
)

# Default settings use the stub provider, whose get_file returns "stub content\n".
STUB_REPO = {
    "provider": "stub",
    "external_id": "repo-1",
    "owner_or_project": "acme",
    "name": "service",
    "default_branch": "main",
}


def test_new_repo_tools_registered() -> None:
    assert "repo_grep" in CATALOG
    assert "repo_parse_manifest" in CATALOG
    assert "git_log_path" in CATALOG


async def test_git_log_path_returns_commits_from_stub() -> None:
    out = await git_log_path_impl(STUB_REPO, "src/app.py", "main", 20)
    assert out["commit_count"] == 1
    commit = out["commits"][0]
    assert commit["sha"] == "stub-sha-1"
    assert "src/app.py" in commit["message"]
    assert commit["author"] == "stub-author"


async def test_git_log_path_respects_limit() -> None:
    out = await git_log_path_impl(STUB_REPO, "src/app.py", "main", 0)
    assert out["commit_count"] == 0


async def test_repo_grep_matches_pattern() -> None:
    hit = await repo_grep_impl(STUB_REPO, "any.py", r"stub", "main")
    assert hit["found"] is True
    assert hit["match_count"] >= 1
    assert hit["matches"][0]["line"] == 1


async def test_repo_grep_no_match() -> None:
    miss = await repo_grep_impl(STUB_REPO, "any.py", r"definitely-not-present", "main")
    assert miss["found"] is False
    assert miss["matches"] == []


async def test_repo_grep_invalid_pattern_is_reported() -> None:
    bad = await repo_grep_impl(STUB_REPO, "any.py", r"(unclosed", "main")
    assert bad["found"] is False
    assert "invalid pattern" in bad["error"]


def test_parse_manifest_requirements_txt() -> None:
    content = "# comment\nrequests==2.31.0\nflask>=2.0\nnot-a-dep\n"
    out = parse_manifest_impl(content, "requirements.txt")
    names = {d["name"]: d["version"] for d in out["dependencies"]}
    assert names["requests"] == "==2.31.0"
    assert names["flask"] == ">=2.0"
    assert "not-a-dep" not in names


def test_parse_manifest_package_json_style() -> None:
    content = '{"dependencies": {"lodash": "^4.17.21", "express": "4.18.2"}}'
    out = parse_manifest_impl(content, "package.json")
    names = {d["name"] for d in out["dependencies"]}
    assert "lodash" in names
    assert "express" in names


async def test_repo_parse_manifest_via_provider() -> None:
    # Stub get_file returns "stub content\n" (no deps) — should parse to zero cleanly.
    out = await repo_parse_manifest_impl(STUB_REPO, "requirements.txt", "main")
    assert out["dependency_count"] == 0
    assert out["dependencies"] == []
