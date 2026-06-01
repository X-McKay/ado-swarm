"""Dependency manifest parsing helpers.

The repository investigation tool needs deterministic dependency evidence, but a
single regex over arbitrary manifest text is too brittle. This module dispatches
to small, pure, format-specific parsers that lean on structured parsers where
available.
"""

from __future__ import annotations

import json
import tomllib
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from defusedxml.ElementTree import fromstring
from packaging.requirements import InvalidRequirement, Requirement

Dependency = dict[str, str]

PYPROJECT_DEPENDENCY_TABLES = (
    ("project", "dependencies"),
    ("project", "optional-dependencies"),
    ("tool", "poetry", "dependencies"),
    ("tool", "poetry", "group"),
)

PACKAGE_JSON_SECTIONS = (
    "dependencies",
    "devDependencies",
    "peerDependencies",
    "optionalDependencies",
    "overrides",
    "resolutions",
)


def _dedupe(dependencies: Iterable[Dependency]) -> list[Dependency]:
    seen: set[tuple[str, str]] = set()
    deduped: list[Dependency] = []
    for dep in dependencies:
        key = (dep["name"], dep.get("version", ""))
        if key not in seen:
            seen.add(key)
            deduped.append(dep)
    return deduped


def _requirement_to_dep(value: str) -> Dependency | None:
    try:
        req = Requirement(value)
    except InvalidRequirement:
        return None
    version = str(req.specifier)
    if not version:
        return None
    return {"name": req.name, "version": version}


def parse_requirements_txt(content: str) -> list[Dependency]:
    """Parse pip requirement lines using ``packaging.requirements.Requirement``."""
    deps: list[Dependency] = []
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith(("-", "--")):
            continue
        line = line.split(" #", 1)[0].strip()
        dep = _requirement_to_dep(line)
        if dep is not None:
            deps.append(dep)
    return _dedupe(deps)


def _walk_package_versions(prefix: str, value: Any) -> list[Dependency]:
    deps: list[Dependency] = []
    if isinstance(value, str):
        deps.append({"name": prefix, "version": value})
    elif isinstance(value, dict):
        # package.json overrides/resolutions can be nested. Preserve nested names
        # when the leaf is a version string.
        for key, child in value.items():
            child_name = key if not prefix else f"{prefix}/{key}"
            deps.extend(_walk_package_versions(child_name, child))
    return deps


def parse_package_json(content: str) -> list[Dependency]:
    data = json.loads(content)
    deps: list[Dependency] = []
    for section in PACKAGE_JSON_SECTIONS:
        values = data.get(section, {})
        if isinstance(values, dict):
            for name, version in values.items():
                deps.extend(_walk_package_versions(str(name), version))
    return _dedupe(deps)


def _poetry_dependency_to_dep(name: str, value: Any) -> Dependency | None:
    if name.lower() == "python":
        return None
    if isinstance(value, str):
        return {"name": name, "version": value}
    if isinstance(value, dict):
        version = value.get("version") or value.get("git") or value.get("path") or ""
        return {"name": name, "version": str(version)}
    return None


def _parse_poetry_group_dependencies(group_data: dict[str, Any]) -> list[Dependency]:
    deps: list[Dependency] = []
    for group in group_data.values():
        if not isinstance(group, dict):
            continue
        dependencies = group.get("dependencies", {})
        if isinstance(dependencies, dict):
            for name, value in dependencies.items():
                dep = _poetry_dependency_to_dep(str(name), value)
                if dep is not None:
                    deps.append(dep)
    return deps


def parse_pyproject_toml(content: str) -> list[Dependency]:
    data = tomllib.loads(content)
    deps: list[Dependency] = []

    project = data.get("project", {})
    if isinstance(project, dict):
        dependencies = project.get("dependencies", [])
        if isinstance(dependencies, list):
            deps.extend(dep for item in dependencies if (dep := _requirement_to_dep(str(item))))
        optional = project.get("optional-dependencies", {})
        if isinstance(optional, dict):
            for group in optional.values():
                if isinstance(group, list):
                    deps.extend(dep for item in group if (dep := _requirement_to_dep(str(item))))

    poetry = data.get("tool", {}).get("poetry", {}) if isinstance(data.get("tool"), dict) else {}
    if isinstance(poetry, dict):
        dependencies = poetry.get("dependencies", {})
        if isinstance(dependencies, dict):
            for name, value in dependencies.items():
                dep = _poetry_dependency_to_dep(str(name), value)
                if dep is not None:
                    deps.append(dep)
        group = poetry.get("group", {})
        if isinstance(group, dict):
            deps.extend(_parse_poetry_group_dependencies(group))

    return _dedupe(deps)


def _xml_local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_xml_dependencies(content: str) -> list[Dependency]:
    root = fromstring(content)
    deps: list[Dependency] = []
    for elem in root.iter():
        if _xml_local_name(elem.tag) == "PackageReference":
            name = elem.attrib.get("Include") or elem.attrib.get("Update")
            version = elem.attrib.get("Version") or ""
            if name:
                deps.append({"name": name, "version": version})
        if _xml_local_name(elem.tag) == "dependency":
            child_values = {
                _xml_local_name(child.tag): (child.text or "").strip() for child in elem
            }
            group_id = child_values.get("groupId")
            artifact_id = child_values.get("artifactId")
            version = child_values.get("version", "")
            if artifact_id:
                name = f"{group_id}:{artifact_id}" if group_id else artifact_id
                deps.append({"name": name, "version": version})
    return _dedupe(deps)


def parse_manifest(content: str, path: str) -> list[Dependency]:
    """Parse dependency hints from a known manifest path.

    Unsupported files intentionally return an empty list rather than falling back
    to broad regex matching; no evidence is better than misleading evidence.
    """
    name = Path(path).name.lower()
    suffix = Path(path).suffix.lower()
    if name in {"requirements.txt", "constraints.txt"} or name.endswith("-requirements.txt"):
        return parse_requirements_txt(content)
    if name == "package.json":
        return parse_package_json(content)
    if name == "pyproject.toml":
        return parse_pyproject_toml(content)
    if suffix in {".csproj", ".props", ".targets"} or name == "pom.xml":
        return parse_xml_dependencies(content)
    return []
