from __future__ import annotations

from copy import deepcopy

from ado_swarm.agents.ticket_analyst.normalization import build_casefile
from ado_swarm.contracts.casefile import SecurityCasefile
from ado_swarm.contracts.events import ArtifactRef
from ado_swarm.contracts.mission import AgentInvocation
from ado_swarm.contracts.source_provider import SourceIssue


def casefile_from_invocation(invocation: AgentInvocation) -> SecurityCasefile | None:
    raw_casefile = invocation.task.constraints.get("casefile")
    if raw_casefile is not None:
        return SecurityCasefile.model_validate(deepcopy(raw_casefile))
    raw_issue = invocation.task.constraints.get("source_issue")
    if raw_issue is not None:
        return build_casefile(invocation.run_id, SourceIssue.model_validate(raw_issue))
    for artifact in invocation.artifact_refs + invocation.task.input_refs:
        metadata = getattr(artifact, "metadata", {})
        if isinstance(metadata, dict) and "casefile" in metadata:
            return SecurityCasefile.model_validate(deepcopy(metadata["casefile"]))
    return None


def casefile_artifact(casefile: SecurityCasefile, *, producer: str) -> ArtifactRef:
    return ArtifactRef(
        name=f"{casefile.casefile_id}.{producer}.json",
        media_type="application/json",
        uri=f"memory://casefiles/{casefile.casefile_id}",
        metadata={"casefile": casefile.model_dump(mode="json"), "producer": producer},
    )
