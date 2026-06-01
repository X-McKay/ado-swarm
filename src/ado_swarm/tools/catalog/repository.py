"""Repository tools — read-only repo/file evidence for the `repo_analyst` agent.

These are the agent's *hands*: the model decides what to inspect, these tools do
the deterministic, policy-gated provider reads.
"""

from __future__ import annotations

import re

from strands import tool

from ado_swarm.config import get_settings
from ado_swarm.contracts.source_provider import SourceIssue, SourceRepositoryRef
from ado_swarm.tools.source_providers.factory import build_source_provider


def resolve_repository_impl(source_issue: dict) -> dict:
    issue = SourceIssue.model_validate(source_issue)
    repo = issue.repository
    if repo is None:
        return {"resolved": False, "repository": None, "ref": None, "evidence": []}
    return {
        "resolved": True,
        "repository": repo.model_dump(mode="json"),
        "ref": repo.default_branch,
        "evidence": ["repository resolved from source issue context"],
    }


async def verify_file_location_impl(repository: dict, path: str, ref: str = "main") -> dict:
    repo = SourceRepositoryRef.model_validate(repository)
    provider = build_source_provider(get_settings())
    try:
        source_file = await provider.get_file(repo, path, ref)
    except Exception as exc:  # provider read failure is evidence, not a crash
        return {
            "file_exists": False,
            "ref": ref,
            "sha": None,
            "evidence": [f"file {path} could not be read: {type(exc).__name__}: {exc}"],
        }
    return {
        "file_exists": True,
        "ref": source_file.ref,
        "sha": source_file.sha,
        "evidence": [f"file {path} exists at {source_file.ref} with sha {source_file.sha}"],
    }


@tool
def resolve_repository(source_issue: dict) -> dict:
    """Resolve the repository context for a finding from its source issue (read-only).

    Args:
        source_issue: A SourceIssue JSON object.

    Returns:
        A JSON object: resolved (bool), repository (SourceRepositoryRef or null),
        ref (default branch or null), and evidence strings.
    """
    return resolve_repository_impl(source_issue)


@tool
async def verify_file_location(repository: dict, path: str, ref: str = "main") -> dict:
    """Check whether a file path exists in a repository at a ref (read-only).

    Args:
        repository: A SourceRepositoryRef JSON object.
        path: The file path to verify.
        ref: The git ref/branch to check (defaults to "main").

    Returns:
        A JSON object: file_exists (bool), ref, sha, and evidence strings.
    """
    return await verify_file_location_impl(repository, path, ref)


MAX_GREP_MATCHES = 50


async def repo_grep_impl(repository: dict, path: str, pattern: str, ref: str = "main") -> dict:
    """Search a single file's content for a regex pattern (read-only)."""
    repo = SourceRepositoryRef.model_validate(repository)
    provider = build_source_provider(get_settings())
    try:
        source_file = await provider.get_file(repo, path, ref)
    except Exception as exc:
        return {"found": False, "matches": [], "error": f"{type(exc).__name__}: {exc}"}
    try:
        regex = re.compile(pattern)
    except re.error as exc:
        return {"found": False, "matches": [], "error": f"invalid pattern: {exc}"}
    matches: list[dict] = []
    for lineno, line in enumerate(source_file.content.splitlines(), start=1):
        if regex.search(line):
            matches.append({"line": lineno, "text": line.strip()[:200]})
            if len(matches) >= MAX_GREP_MATCHES:
                break
    return {
        "found": bool(matches),
        "path": path,
        "ref": source_file.ref,
        "match_count": len(matches),
        "matches": matches,
    }


def parse_manifest_impl(content: str, path: str) -> dict:
    """Extract dependency-ish (name, version) hints from a manifest's text (deterministic)."""
    deps: list[dict] = []
    lower = path.lower()
    if lower.endswith(("requirements.txt", ".txt")):
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            m = re.match(r"^([A-Za-z0-9._-]+)\s*(==|>=|<=|~=|>|<)\s*([0-9][\w.+-]*)", line)
            if m:
                deps.append({"name": m.group(1), "version": m.group(3)})
    else:
        # Generic "name": "version" / name = "version" pairs (package.json, toml, etc.)
        for m in re.finditer(
            r'["\']?([A-Za-z0-9._@/-]+)["\']?\s*[:=]\s*["\']([\^~>=<]*[0-9][\w.+-]*)["\']',
            content,
        ):
            deps.append({"name": m.group(1), "version": m.group(2)})
    return {"path": path, "dependency_count": len(deps), "dependencies": deps[:200]}


async def repo_parse_manifest_impl(repository: dict, path: str, ref: str = "main") -> dict:
    repo = SourceRepositoryRef.model_validate(repository)
    provider = build_source_provider(get_settings())
    try:
        source_file = await provider.get_file(repo, path, ref)
    except Exception as exc:
        return {"path": path, "dependency_count": 0, "dependencies": [], "error": str(exc)}
    return parse_manifest_impl(source_file.content, path)


@tool
async def repo_grep(repository: dict, path: str, pattern: str, ref: str = "main") -> dict:
    """Search a repository file's content for a regex pattern (read-only).

    Use this to confirm a flagged code pattern is actually present at a location
    (evidence for adjudication), or to locate a symbol/usage.

    Args:
        repository: A SourceRepositoryRef JSON object.
        path: The file path to search.
        pattern: A Python regular expression.
        ref: The git ref/branch (defaults to "main").

    Returns:
        A JSON object: found (bool), match_count, and matches [{line, text}].
    """
    return await repo_grep_impl(repository, path, pattern, ref)


@tool
async def repo_parse_manifest(repository: dict, path: str, ref: str = "main") -> dict:
    """Parse a dependency manifest into (name, version) pairs (read-only).

    Use this on a manifest (requirements.txt, package.json, pyproject.toml, etc.)
    to confirm the vulnerable package/version a dependency finding refers to.

    Args:
        repository: A SourceRepositoryRef JSON object.
        path: The manifest path.
        ref: The git ref/branch (defaults to "main").

    Returns:
        A JSON object: path, dependency_count, dependencies [{name, version}].
    """
    return await repo_parse_manifest_impl(repository, path, ref)
