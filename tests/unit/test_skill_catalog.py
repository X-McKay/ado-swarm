from ado_swarm.skills.loader import list_skills, load_pack, validate_packs


def test_skill_catalog_contains_full_initial_set() -> None:
    skills = set(list_skills())
    assert len(skills) >= 26
    assert "security-ticket-normalization" in skills
    assert "skill-performance-evaluation" in skills


def test_skill_packs_reference_existing_skills() -> None:
    assert validate_packs() == {}
    assert "security-risk-scoring" in load_pack("risk-impact")
