from __future__ import annotations

from ado_swarm.evals.manifest import summarize_trials


def reliability_report(outcomes: list[bool], latencies_ms: list[float] | None = None) -> dict:
    summary = summarize_trials(outcomes, latencies_ms)
    summary["reliability_mode"] = "pass^k"
    summary["recommendation"] = "promote" if summary["pass_k"] else "hold"
    return summary
