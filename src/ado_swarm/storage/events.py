from __future__ import annotations

from ado_swarm.contracts.events import TaskEvent


class InMemoryEventStore:
    def __init__(self) -> None:
        self.events: list[TaskEvent] = []

    async def append(self, event: TaskEvent) -> TaskEvent:
        self.events.append(event)
        return event

    async def list_for_run(self, run_id: str) -> list[TaskEvent]:
        return [event for event in self.events if event.run_id == run_id]
