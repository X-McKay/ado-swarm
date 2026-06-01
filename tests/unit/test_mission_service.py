from __future__ import annotations

from ado_swarm.config import Settings
from ado_swarm.runtime.mission_service import MissionService


class FakeHandle:
    def __init__(self, workflow_id: str) -> None:
        self.id = workflow_id
        self.signals: list[tuple[str, tuple]] = []

    async def query(self, name: str):
        assert name == "get_snapshot"
        return {"status": "running"}

    async def signal(self, name: str, *args):
        self.signals.append((name, args))


class FakeClient:
    def __init__(self) -> None:
        self.started: list[dict] = []
        self.handle = FakeHandle("mission:existing")

    async def start_workflow(self, workflow, *, args, id, task_queue, search_attributes=None):
        self.started.append(
            {
                "workflow": workflow,
                "args": args,
                "id": id,
                "task_queue": task_queue,
                "search_attributes": search_attributes or {},
            }
        )
        return FakeHandle(id)

    def get_workflow_handle(self, workflow_id: str) -> FakeHandle:
        self.handle.id = workflow_id
        return self.handle


async def test_mission_service_start_uses_supervisor_workflow(monkeypatch) -> None:
    client = FakeClient()

    async def fake_build_client(settings=None):
        return client

    monkeypatch.setattr(
        "ado_swarm.runtime.mission_service.build_temporal_client", fake_build_client
    )
    settings = Settings(temporal_task_queue="queue")

    result = await MissionService(settings).start("Fix security findings")

    assert result["status"] == "started"
    assert result["goal"] == "Fix security findings"
    assert client.started[0]["workflow"] == "SupervisorWorkflow"
    assert client.started[0]["task_queue"] == "queue"
    assert client.started[0]["args"][0] == result["run_id"]
    assert client.started[0]["args"][1] == "Fix security findings"
    assert client.started[0]["search_attributes"]["RunId"] == [result["run_id"]]
    assert client.started[0]["search_attributes"]["SourceProvider"] == ["stub"]
    assert client.started[0]["search_attributes"]["MissionStatus"] == ["created"]


async def test_mission_service_describe_pause_resume(monkeypatch) -> None:
    client = FakeClient()

    async def fake_build_client(settings=None):
        return client

    monkeypatch.setattr(
        "ado_swarm.runtime.mission_service.build_temporal_client", fake_build_client
    )
    service = MissionService(Settings())

    assert await service.describe("mission:1") == {"status": "running"}
    assert await service.pause("mission:1", "reason") == {
        "workflow_id": "mission:1",
        "status": "pause_signal_sent",
    }
    assert await service.resume("mission:1") == {
        "workflow_id": "mission:1",
        "status": "resume_signal_sent",
    }
    assert client.handle.signals == [("pause", ("reason",)), ("resume", ())]
