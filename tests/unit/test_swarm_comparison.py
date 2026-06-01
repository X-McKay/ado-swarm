from __future__ import annotations

from ado_swarm.evals.swarm_comparison import _disposition_open, compare_modes


def test_disposition_open_logic() -> None:
    assert _disposition_open({"stale": False, "false_positive": False}) is True
    assert _disposition_open({"stale": True}) is False
    assert _disposition_open({"duplicate_of": "finding-x"}) is False
    assert _disposition_open(None) is False


async def test_compare_modes_runs_both_and_recommends() -> None:
    report = await compare_modes("fake")
    assert set(report) >= {"single_agent", "swarm", "recommendation"}
    assert report["single_agent"]["cases"] >= 1
    assert report["swarm"]["cases"] >= 1
    # On the deterministic fake model both modes agree with the expected disposition,
    # so the tie-breaker keeps the cheaper single-agent mode.
    assert report["recommendation"] == "keep_single_agent"
