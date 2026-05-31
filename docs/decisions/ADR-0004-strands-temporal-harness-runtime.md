# ADR-0004: Strands inside Temporal for durable agent harness execution

**Status:** Accepted

`ado-swarm` keeps Temporal as the durable outer orchestration layer and introduces a Strands-compatible runtime adapter inside the agent boundary. Temporal owns long-running workflow state, retry policy, approvals, and mission lifecycle. Strands owns the ReAct-loop-oriented agent runtime, hooks, streaming, and future checkpoint integration.

This split keeps workflow code deterministic and makes agent runtime behavior independently testable. The adapter intentionally falls back to the existing model gateway when Strands is unavailable or when a specific agent has not yet opted into native Strands tools.
