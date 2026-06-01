"""Scaffolders for the model-driven agent/tool/skill pattern.

Used by the `ado-swarm scaffold ...` CLI and `just new-*` recipes so a new
agent/tool/skill starts from the correct shape (see `CLAUDE.md` and
`docs/concepts/agents-tools-skills.md`) rather than copy-paste.
"""

from __future__ import annotations

import ast
from pathlib import Path
from string import Template

SRC = Path(__file__).resolve().parents[1]
AGENTS_DIR = SRC / "agents"
CATALOG_DIR = SRC / "tools" / "catalog"
SKILLS_DIR = SRC / "skills"
TEMPLATES_DIR = Path(__file__).parent / "templates"


def _title(identifier: str) -> str:
    return " ".join(part.capitalize() for part in identifier.replace("-", "_").split("_"))


def _render(template_name: str, **values: str) -> str:
    template = Template((TEMPLATES_DIR / template_name).read_text(encoding="utf-8"))
    rendered = template.substitute(**values)
    if "TODO" in rendered:
        raise ValueError(f"Template {template_name} rendered with unresolved TODO text")
    return rendered


def _validate_python(path: Path) -> None:
    ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def scaffold_skill(
    name: str, description: str = "Use this skill for repository-specific work"
) -> Path:
    """Create skills/<name>/SKILL.md from a validated template."""
    skill_dir = SKILLS_DIR / name
    path = skill_dir / "SKILL.md"
    if path.exists():
        raise FileExistsError(path)
    skill_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(
        _render(
            "skill.md.tpl",
            name=name,
            title=_title(name),
            description=description,
            description_lower=description[:1].lower() + description[1:],
        ),
        encoding="utf-8",
    )
    return path


def _register_tool_in_catalog(name: str, area: str) -> None:
    catalog = CATALOG_DIR / "__init__.py"
    text = catalog.read_text(encoding="utf-8")
    import_line = f"from ado_swarm.tools.catalog.{area} import {name}\n"
    entry_line = f'    "{name}": {name},\n'
    if import_line not in text:
        marker = "from typing import Any\n"
        text = text.replace(marker, marker + "\n" + import_line, 1)
    if entry_line not in text:
        text = text.replace("}\n\n\ndef get_tools", entry_line + "}\n\n\ndef get_tools", 1)
    catalog.write_text(text, encoding="utf-8")
    _validate_python(catalog)


def scaffold_tool(name: str, area: str) -> Path:
    """Create or append tools/catalog/<area>.py and register the tool in CATALOG."""
    path = CATALOG_DIR / f"{area}.py"
    snippet = _render("tool.py.tpl", name=name)
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if f"def {name}(" in existing or f"def {name}_impl(" in existing:
            raise FileExistsError(f"Tool {name} already exists in {path}")
        if "from strands import tool" not in existing:
            existing = "from strands import tool\n" + existing
        path.write_text(existing.rstrip() + "\n" + snippet, encoding="utf-8")
    else:
        path.write_text(
            "from __future__ import annotations\n\nfrom strands import tool\n" + snippet,
            encoding="utf-8",
        )
    _validate_python(path)
    _register_tool_in_catalog(name, area)
    return path


def scaffold_agent(
    agent_id: str,
    section_field: str = "readiness",
    tool: str = "assess_readiness",
    section_model: str = "ReadinessVerdict",
) -> list[Path]:
    """Create agents/<agent_id>/ with metadata.yaml, main.py, eval.py, __init__.py."""
    agent_dir = AGENTS_DIR / agent_id
    if agent_dir.exists():
        raise FileExistsError(agent_dir)
    agent_dir.mkdir(parents=True)
    display = _title(agent_id)
    cls = display.replace(" ", "") + "Agent"

    init_py = agent_dir / "__init__.py"
    init_py.write_text("", encoding="utf-8")
    metadata = agent_dir / "metadata.yaml"
    metadata.write_text(
        _render(
            "agent_metadata.yaml.tpl",
            agent_id=agent_id,
            display=display,
            section_field=section_field,
            tool=tool,
        ),
        encoding="utf-8",
    )
    main = agent_dir / "main.py"
    main.write_text(
        _render(
            "agent_main.py.tpl",
            agent_id=agent_id,
            display=display,
            class_name=cls,
            section_field=section_field,
            section_model=section_model,
            tool=tool,
        ),
        encoding="utf-8",
    )
    eval_py = agent_dir / "eval.py"
    eval_py.write_text(
        _render("agent_eval.py.tpl", agent_id=agent_id, display=display),
        encoding="utf-8",
    )
    for path in (main, eval_py):
        _validate_python(path)
    return [metadata, main, eval_py]
