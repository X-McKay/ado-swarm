from __future__ import annotations

from ado_swarm.tools.manifest_parsers import parse_manifest


def _deps_by_name(content: str, path: str) -> dict[str, str]:
    return {dep["name"]: dep["version"] for dep in parse_manifest(content, path)}


def test_parse_requirements_txt_uses_packaging_requirement_semantics() -> None:
    content = """
# comment
requests[security]>=2.31; python_version >= "3.11"
flask==3.0.0  # inline comment
-r nested.txt
not a requirement
"""

    deps = _deps_by_name(content, "requirements.txt")

    assert deps["requests"] == ">=2.31"
    assert deps["flask"] == "==3.0.0"
    assert "not" not in deps


def test_parse_package_json_dependency_sections() -> None:
    content = """{
      "dependencies": {"lodash": "^4.17.21"},
      "devDependencies": {"vitest": "1.5.0"},
      "overrides": {"express": {"qs": "6.11.0"}}
    }"""

    deps = _deps_by_name(content, "package.json")

    assert deps["lodash"] == "^4.17.21"
    assert deps["vitest"] == "1.5.0"
    assert deps["express/qs"] == "6.11.0"


def test_parse_pyproject_toml_pep621_and_poetry_groups() -> None:
    content = """
[project]
dependencies = ["fastapi>=0.111", "pydantic==2.7.1"]

[project.optional-dependencies]
dev = ["pytest>=8"]

[tool.poetry.dependencies]
python = "^3.11"
httpx = "^0.27"

[tool.poetry.group.lint.dependencies]
ruff = "^0.8"
"""

    deps = _deps_by_name(content, "pyproject.toml")

    assert deps["fastapi"] == ">=0.111"
    assert deps["pydantic"] == "==2.7.1"
    assert deps["pytest"] == ">=8"
    assert deps["httpx"] == "^0.27"
    assert deps["ruff"] == "^0.8"
    assert "python" not in deps


def test_parse_csproj_package_references() -> None:
    content = """
<Project Sdk="Microsoft.NET.Sdk">
  <ItemGroup>
    <PackageReference Include="Newtonsoft.Json" Version="13.0.3" />
  </ItemGroup>
</Project>
"""

    deps = _deps_by_name(content, "app.csproj")

    assert deps["Newtonsoft.Json"] == "13.0.3"


def test_parse_pom_dependencies() -> None:
    content = """
<project>
  <dependencies>
    <dependency>
      <groupId>org.slf4j</groupId>
      <artifactId>slf4j-api</artifactId>
      <version>2.0.13</version>
    </dependency>
  </dependencies>
</project>
"""

    deps = _deps_by_name(content, "pom.xml")

    assert deps["org.slf4j:slf4j-api"] == "2.0.13"


def test_unsupported_manifest_returns_no_dependencies() -> None:
    assert parse_manifest('"lodash": "4.17.21"', "README.md") == []
