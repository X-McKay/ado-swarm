"""Eval-gated swarm decision: compare single-agent vs bounded-swarm adjudication.

The bounded adjudication swarm (ADR-0009) is opt-in and only worth defaulting on
if it measurably beats the single agent. This harness runs `security_reviewer` in
both modes over golden adjudication cases and reports per-mode agreement with the
expected disposition, so the decision is data-driven rather than architectural
faith. On the deterministic `fake` model both modes return the injected decision
(so agreement is 1.0); the comparison is meaningful against a real model (ollama).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from ado_swarm.agents.eval_support import build_eval_model_gateway, eval_invocation
from ado_swarm.agents.registry import build_agent
from ado_swarm.agents.ticket_analyst.normalization import build_casefile
from ado_swarm.contracts.events import TaskState
from ado_swarm.contracts.mission import AgentResult
from ado_swarm.contracts.source_provider import SourceIssue

GOLDEN_DIR = Path("tests/fixtures/source_issues")


@dataclass
class GoldenCase:
    """A golden adjudication case: a source-issue fixture + the expected disposition."""

    fixture: str
    expected_open: bool  # True if the finding should remain open (not stale/fp/dup)


# Minimal golden set; extend with more fixtures as they are added.
GOLDEN_CASES = [GoldenCase(fixture="codeql_sast.json", expected_open=True)]


@dataclass
class ModeOutcome:
    mode: str
    cases: int = 0
    agreements: int = 0
    failures: int = 0
    details: list[dict] = field(default_factory=list)

    @property
    def agreement_rate(self) -> float:
        return self.agreements / self.cases if self.cases else 0.0


def _disposition_open(adjudication: dict | None) -> bool:
    if not adjudication:
        return False
    return not (
        adjudication.get("stale")
        or adjudication.get("false_positive")
        or adjudication.get("already_fixed")
        or adjudication.get("duplicate_of")
    )


async def _run_case(model_profile: str, case: GoldenCase, *, use_swarm: bool) -> dict:
    issue = SourceIssue.model_validate(json.loads((GOLDEN_DIR / case.fixture).read_text()))
    casefile = build_casefile("swarm-compare", issue)
    agent = build_agent("security_reviewer", model_gateway=build_eval_model_gateway(model_profile))
    invocation = eval_invocation(
        "security_reviewer",
        objective="Adjudicate for swarm comparison.",
        constraints={"casefile": casefile.model_dump(mode="json"), "use_swarm": use_swarm},
    )
    result: AgentResult = await agent.run(invocation)
    if result.state != TaskState.COMPLETED or not result.artifact_refs:
        return {"fixture": case.fixture, "ok": False, "agreed": False}
    adjudication = result.artifact_refs[0].metadata["casefile"].get("adjudication")
    agreed = _disposition_open(adjudication) == case.expected_open
    return {"fixture": case.fixture, "ok": True, "agreed": agreed}


async def compare_modes(model_profile: str = "fake") -> dict:
    """Run every golden case in both modes; return per-mode agreement + a recommendation."""
    outcomes = {"single_agent": ModeOutcome("single_agent"), "swarm": ModeOutcome("swarm")}
    for case in GOLDEN_CASES:
        for mode, use_swarm in (("single_agent", False), ("swarm", True)):
            outcome = outcomes[mode]
            res = await _run_case(model_profile, case, use_swarm=use_swarm)
            outcome.cases += 1
            if not res["ok"]:
                outcome.failures += 1
            elif res["agreed"]:
                outcome.agreements += 1
            outcome.details.append(res)

    single = outcomes["single_agent"]
    swarm = outcomes["swarm"]
    if swarm.agreement_rate > single.agreement_rate:
        recommendation = "enable_swarm"
    elif swarm.agreement_rate == single.agreement_rate:
        recommendation = "keep_single_agent"  # swarm costs ~Nx; tie goes to the cheaper mode
    else:
        recommendation = "keep_single_agent"
    return {
        "model_profile": model_profile,
        "single_agent": {
            "agreement_rate": single.agreement_rate,
            "cases": single.cases,
            "details": single.details,
        },
        "swarm": {
            "agreement_rate": swarm.agreement_rate,
            "cases": swarm.cases,
            "details": swarm.details,
        },
        "recommendation": recommendation,
    }
