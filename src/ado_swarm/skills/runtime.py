"""Bind the on-disk skill catalog to a Strands agent via the AgentSkills plugin.

This is what makes skills *load-bearing*: the `SKILL.md` bodies are progressively
disclosed into the agent's context (not just listed as labels). Which skills an
agent gets is driven by its `metadata.yaml` (single source of truth).
"""

from __future__ import annotations

from pathlib import Path

from strands import AgentSkills, Skill

from ado_swarm.skills.loader import SKILLS_DIR, list_skills, load_pack


def resolve_skill_names(
    *, skills: list[str] | None = None, packs: list[str] | None = None
) -> list[str]:
    """Expand packs into skill names and merge with explicit skills, de-duped and ordered."""
    resolved: list[str] = []
    for pack in packs or []:
        resolved.extend(load_pack(pack))
    resolved.extend(skills or [])
    seen: set[str] = set()
    ordered: list[str] = []
    for name in resolved:
        if name not in seen:
            seen.add(name)
            ordered.append(name)
    return ordered


def build_skills_plugin(skill_names: list[str], *, strict: bool = True) -> AgentSkills | None:
    """Build an AgentSkills plugin scoped to the given skills, or None if empty.

    Raises KeyError if a requested skill is not present in the catalog so a
    misconfigured agent fails loudly rather than silently dropping expertise.
    """
    if not skill_names:
        return None
    # AgentSkills(strict=True) validates SKILL.md *content* but silently SKIPS a
    # missing skill directory (it only warns). This guard fails loudly so a
    # misconfigured agent never silently loses expertise. Skill loading and
    # validation themselves are left to the SDK (AgentSkills / Skill.from_*).
    known = set(list_skills())
    missing = [name for name in skill_names if name not in known]
    if missing:
        raise KeyError(f"Unknown skills requested: {missing}")
    dirs: list[str | Path | Skill] = [str(SKILLS_DIR / name) for name in skill_names]
    return AgentSkills(skills=dirs, strict=strict)
