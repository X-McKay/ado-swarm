from __future__ import annotations

from pathlib import Path

SKILLS_DIR = Path(__file__).parent
PACKS_DIR = SKILLS_DIR / "packs"


def list_skills() -> list[str]:
    return sorted(path.name for path in SKILLS_DIR.iterdir() if (path / "SKILL.md").exists())


def load_pack(pack_name: str) -> list[str]:
    pack_file = PACKS_DIR / f"{pack_name}.txt"
    return [line.strip() for line in pack_file.read_text().splitlines() if line.strip()]


def validate_packs() -> dict[str, list[str]]:
    known = set(list_skills())
    invalid: dict[str, list[str]] = {}
    for pack_file in sorted(PACKS_DIR.glob("*.txt")):
        missing = [skill for skill in load_pack(pack_file.stem) if skill not in known]
        if missing:
            invalid[pack_file.stem] = missing
    return invalid
