# Harness Runtime Operations

The harness runtime layers deterministic Temporal workflows around agent execution. Use Temporal for durable run lifecycle, Signals and Updates for control, and the optional Strands adapter for richer agent-loop behavior.

## Runtime controls

The CLI exposes `ado-swarm runs describe`, `ado-swarm runs pause`, `ado-swarm runs resume`, and `ado-swarm runs artifacts`. API endpoints mirror the same controls for mission start, status, pause, and resume.

## Model and agent events

Agent results now include checkpoint, budget, and telemetry fields. Checkpoints are persisted best-effort by the `run_agent` activity when Postgres is available. This preserves E2E behavior while enabling crash-resume implementation in the next richer-agent wave.

## Policy and budgets

Every write-capable tool should be checked through `ToolPolicy` with a `ToolContext`. High-risk tasks and write tools require explicit approval state before execution.
