from __future__ import annotations

import ast
from pathlib import Path

from ado_swarm.cli import scaffold


def test_scaffold_skill_uses_template_without_todos(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(scaffold, "SKILLS_DIR", tmp_path / "skills")

    path = scaffold.scaffold_skill("evidence-review", "Review evidence consistently")

    text = path.read_text(encoding="utf-8")
    assert "TODO" not in text
    assert "name: evidence-review" in text
    assert "Review evidence consistently" in text


def test_scaffold_tool_generates_valid_python_and_registers_catalog(
    tmp_path: Path, monkeypatch
) -> None:
    catalog_dir = tmp_path / "catalog"
    catalog_dir.mkdir()
    catalog_init = catalog_dir / "__init__.py"
    catalog_init.write_text(
        "from __future__ import annotations\n\n"
        "from typing import Any\n\n"
        "CATALOG: dict[str, Any] = {\n"
        "}\n\n\n"
        "def get_tools(names: list[str]) -> list[Any]:\n"
        "    return [CATALOG[name] for name in names]\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(scaffold, "CATALOG_DIR", catalog_dir)

    path = scaffold.scaffold_tool("inspect_payload", "generated")

    generated = path.read_text(encoding="utf-8")
    catalog_text = catalog_init.read_text(encoding="utf-8")
    ast.parse(generated)
    ast.parse(catalog_text)
    assert "TODO" not in generated
    assert "inspect_payload" in catalog_text
    assert "from ado_swarm.tools.catalog.generated import inspect_payload" in catalog_text


def test_scaffold_agent_generates_valid_python_without_todos(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(scaffold, "AGENTS_DIR", tmp_path / "agents")

    created = scaffold.scaffold_agent(
        "readiness_probe",
        section_field="readiness",
        tool="assess_readiness",
        section_model="ReadinessVerdict",
    )

    for path in created:
        text = path.read_text(encoding="utf-8")
        assert "TODO" not in text
        if path.suffix == ".py":
            ast.parse(text)
    assert {path.name for path in created} == {"metadata.yaml", "main.py", "eval.py"}
