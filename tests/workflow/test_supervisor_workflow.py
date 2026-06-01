"""Temporal workflow test suite (Phase 0 / M0).

These tests exercise ``SupervisorWorkflow`` end-to-end against the Temporal
time-skipping test environment with *mocked* activities, so no real agents,
models, or databases are required. They are the regression net for workflow
determinism, the mission lifecycle (run / pause / resume / cancel), and the
human-in-the-loop approval Updates and their validators.

The time-skipping environment (``WorkflowEnvironment.start_time_skipping``)
downloads a bundled test-server binary on first use. In hermetic/offline
sandboxes that download is blocked, so the ``workflow_env`` fixture attempts to
start the server once and ``pytest.skip``s the whole module if it cannot. When
the server *is* available, the same environment also validates deterministic
replay automatically.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

import pytest
from temporalio import activity
from temporalio.client import Client, WorkflowUpdateFailedError
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from ado_swarm.contracts.events import ArtifactRef, RunStatus, TaskState
from ado_swarm.contracts.mission import (
    AgentInvocation,
    AgentResult,
    PlanVersion,
    RunSnapshot,
    TaskSpec,
)
from ado_swarm.workflows.agent_task import AgentTaskWorkflow
from ado_swarm.workflows.supervisor import SupervisorWorkflow

# ---------------------------------------------------------------------------
# Time-skipping environment fixture (module scoped, skips when unavailable)
# ---------------------------------------------------------------------------


@pytest.fixture
async def workflow_env() -> AsyncIterator[WorkflowEnvironment]:
    """Start a time-skipping ``WorkflowEnvironment`` or skip the test.

    This fixture is function scoped on purpose: under pytest-asyncio's auto
    mode a module/session-scoped async fixture runs on a *different* event loop
    than the function-scoped tests, which would make the Temporal client and
    the gating ``asyncio.Event`` objects cross-loop and unusable. One env per
    test keeps everything on a single loop and fully hermetic.

    The pydantic data converter is applied so the workflows can pass the
    pydantic ``BaseModel`` contracts (``TaskSpec``, ``AgentResult``,
    ``RunSnapshot``, ...) across the activity / child-workflow boundaries.
    """
    try:
        env = await WorkflowEnvironment.start_time_skipping(
            data_converter=pydantic_data_converter,
        )
    except Exception as exc:  # pragma: no cover - environment dependent
        pytest.skip(f"time-skipping test server unavailable in this sandbox: {exc}")
    try:
        yield env
    finally:
        await env.shutdown()


@pytest.fixture
def client(workflow_env: WorkflowEnvironment) -> Client:
    return workflow_env.client


# ---------------------------------------------------------------------------
# Mocked activities (same registered names as the production activities)
# ---------------------------------------------------------------------------


def _make_plan(run_id: str, goal: str, *, num_tasks: int = 2) -> PlanVersion:
    """Build a small, valid linear plan (1-2 tasks)."""
    tasks: list[TaskSpec] = []
    previous: str | None = None
    for index in range(num_tasks):
        task = TaskSpec(
            run_id=run_id,
            title=f"task-{index}",
            objective=goal,
            capability="ticket_analyst",
            agent_id="ticket_analyst",
            depends_on=[previous] if previous else [],
            # Keep timeouts small so any (skipped) workflow time is bounded.
            timeout_seconds=30,
            max_attempts=1,
        )
        tasks.append(task)
        previous = task.task_id
    return PlanVersion(
        run_id=run_id,
        goal=goal,
        rationale="mock plan for workflow tests",
        tasks=tasks,
    )


@activity.defn(name="plan_mission")
async def mock_plan_mission(run_id: str, goal: str) -> PlanVersion:
    return _make_plan(run_id, goal, num_tasks=2)


@activity.defn(name="run_agent")
async def mock_run_agent(invocation: AgentInvocation) -> AgentResult:
    """Return a valid COMPLETED ``AgentResult`` with one artifact."""
    return AgentResult(
        run_id=invocation.run_id,
        task_id=invocation.task.task_id,
        state=TaskState.COMPLETED,
        summary=f"completed {invocation.task.title}",
        artifact_refs=[
            ArtifactRef(
                name=f"artifact-{invocation.task.task_id}",
                uri=f"mem://{invocation.task.task_id}",
            )
        ],
    )


# ---------------------------------------------------------------------------
# Worker helper
# ---------------------------------------------------------------------------


@asynccontextmanager
async def _worker(
    client: Client,
    task_queue: str,
    *,
    run_agent_activity: Callable[..., object] = mock_run_agent,
    plan_mission_activity: Callable[..., object] = mock_plan_mission,
) -> AsyncIterator[None]:
    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[SupervisorWorkflow, AgentTaskWorkflow],
        activities=[plan_mission_activity, run_agent_activity],
    ):
        yield


def _ids() -> tuple[str, str, str]:
    """Unique (run_id, workflow_id, task_queue) per test."""
    token = uuid.uuid4().hex
    return f"run-{token}", f"wf-{token}", f"tq-{token}"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_mission_runs_to_completed(client: Client) -> None:
    """A mission runs to COMPLETED; the snapshot/query reports task states.

    Because the time-skipping environment validates history on completion,
    a successful run is also the deterministic-replay assertion (requirement 5).
    """
    run_id, wf_id, task_queue = _ids()
    async with _worker(client, task_queue):
        handle = await client.start_workflow(
            SupervisorWorkflow.run,
            args=[run_id, "investigate finding"],
            id=wf_id,
            task_queue=task_queue,
        )
        result: RunSnapshot = await handle.result()

        # Query the live (closed) workflow snapshot too.
        queried: RunSnapshot | None = await handle.query(SupervisorWorkflow.get_snapshot)

    assert result.status is RunStatus.COMPLETED
    assert result.run_id == run_id
    assert result.current_plan_version == 1
    assert len(result.task_states) == 2
    assert all(state is TaskState.COMPLETED for state in result.task_states.values())
    assert len(result.artifact_refs) == 2

    assert queried is not None
    assert queried.status is RunStatus.COMPLETED
    assert queried.task_states == result.task_states


async def test_pause_then_resume(client: Client) -> None:
    """pause holds the run in WAITING_FOR_APPROVAL; resume returns it to RUNNING.

    A gating activity blocks the first ``run_agent`` so the supervisor is
    provably mid-flight when we pause, removing any completion race.
    """
    run_id, wf_id, task_queue = _ids()
    release = asyncio.Event()
    entered = asyncio.Event()

    @activity.defn(name="run_agent")
    async def gated_run_agent(invocation: AgentInvocation) -> AgentResult:
        entered.set()
        await release.wait()
        return AgentResult(
            run_id=invocation.run_id,
            task_id=invocation.task.task_id,
            state=TaskState.COMPLETED,
            summary="gated complete",
        )

    @activity.defn(name="plan_mission")
    async def single_plan(run_id_: str, goal: str) -> PlanVersion:
        return _make_plan(run_id_, goal, num_tasks=1)

    async with _worker(
        client,
        task_queue,
        run_agent_activity=gated_run_agent,
        plan_mission_activity=single_plan,
    ):
        handle = await client.start_workflow(
            SupervisorWorkflow.run,
            args=[run_id, "investigate finding"],
            id=wf_id,
            task_queue=task_queue,
        )
        # Wait until the first task's activity is actually running.
        await entered.wait()

        await handle.signal(SupervisorWorkflow.pause, "operator pause")
        paused: RunSnapshot | None = await handle.query(SupervisorWorkflow.get_snapshot)
        assert paused is not None
        assert paused.status is RunStatus.WAITING_FOR_APPROVAL
        assert paused.blocked_reason == "operator pause"

        await handle.signal(SupervisorWorkflow.resume)
        resumed: RunSnapshot | None = await handle.query(SupervisorWorkflow.get_snapshot)
        assert resumed is not None
        assert resumed.status is RunStatus.RUNNING

        # Let the gated activity finish so the run can complete.
        release.set()
        result: RunSnapshot = await handle.result()

    assert result.status is RunStatus.COMPLETED


async def test_cancel_signal(client: Client) -> None:
    """A cancel signal drives the run to RunStatus.CANCELLED."""
    run_id, wf_id, task_queue = _ids()
    release = asyncio.Event()
    entered = asyncio.Event()

    @activity.defn(name="run_agent")
    async def gated_run_agent(invocation: AgentInvocation) -> AgentResult:
        entered.set()
        await release.wait()
        return AgentResult(
            run_id=invocation.run_id,
            task_id=invocation.task.task_id,
            state=TaskState.COMPLETED,
            summary="gated complete",
        )

    @activity.defn(name="plan_mission")
    async def single_plan(run_id_: str, goal: str) -> PlanVersion:
        return _make_plan(run_id_, goal, num_tasks=1)

    async with _worker(
        client,
        task_queue,
        run_agent_activity=gated_run_agent,
        plan_mission_activity=single_plan,
    ):
        handle = await client.start_workflow(
            SupervisorWorkflow.run,
            args=[run_id, "investigate finding"],
            id=wf_id,
            task_queue=task_queue,
        )
        await entered.wait()

        # Pause first so the loop re-evaluates the wait_condition and observes
        # the cancel request rather than racing to the next task.
        await handle.signal(SupervisorWorkflow.pause, "hold")
        await handle.signal(SupervisorWorkflow.cancel, "operator cancel")
        release.set()
        result: RunSnapshot = await handle.result()

    assert result.status is RunStatus.CANCELLED
    assert result.blocked_reason == "operator cancel"


async def test_approve_task_update_and_validators(client: Client) -> None:
    """approve_task succeeds; reject/replan validators refuse bad input.

    The approve_task Update is sent while the run is gated mid-flight, then the
    run is allowed to complete and the approval is recorded on the snapshot.
    The reject/replan validators are exercised via ``execute_update`` with
    empty arguments, which must raise ``WorkflowUpdateFailedError``.
    """
    run_id, wf_id, task_queue = _ids()
    release = asyncio.Event()
    entered = asyncio.Event()

    @activity.defn(name="run_agent")
    async def gated_run_agent(invocation: AgentInvocation) -> AgentResult:
        entered.set()
        await release.wait()
        return AgentResult(
            run_id=invocation.run_id,
            task_id=invocation.task.task_id,
            state=TaskState.COMPLETED,
            summary="gated complete",
        )

    @activity.defn(name="plan_mission")
    async def single_plan(run_id_: str, goal: str) -> PlanVersion:
        return _make_plan(run_id_, goal, num_tasks=1)

    async with _worker(
        client,
        task_queue,
        run_agent_activity=gated_run_agent,
        plan_mission_activity=single_plan,
    ):
        handle = await client.start_workflow(
            SupervisorWorkflow.run,
            args=[run_id, "investigate finding"],
            id=wf_id,
            task_queue=task_queue,
        )
        await entered.wait()

        # Valid approval update returns "approved". Updates are addressed by
        # their registered name (the method name) so the string overload of
        # ``execute_update`` is used unambiguously.
        approved = await handle.execute_update(
            "approve_task",
            args=["task-123", "alice"],
        )
        assert approved == "approved"

        # reject_task validator rejects empty task_id.
        with pytest.raises(WorkflowUpdateFailedError):
            await handle.execute_update(
                "reject_task",
                args=["", "some reason"],
            )

        # request_replan validator rejects empty reason.
        with pytest.raises(WorkflowUpdateFailedError):
            await handle.execute_update(
                "request_replan",
                args=[""],
            )

        # The rejected updates must not have mutated the run.
        snapshot: RunSnapshot | None = await handle.query(SupervisorWorkflow.get_snapshot)
        assert snapshot is not None
        assert snapshot.approvals.get("task-123") == "alice"
        assert snapshot.status is not RunStatus.CANCELLED

        release.set()
        result: RunSnapshot = await handle.result()

    assert result.status is RunStatus.COMPLETED
    assert result.approvals.get("task-123") == "alice"
