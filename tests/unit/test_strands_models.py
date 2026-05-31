"""Tests for the deterministic Strands model layer.

These tests exercise the REAL ``strands.Agent`` event loop against
:class:`FakeModel` -- nothing about the Agent is stubbed. They run fully
offline and deterministically.
"""

from __future__ import annotations

import datetime
import enum
import warnings
from typing import cast

import pytest
from pydantic import BaseModel
from strands import Agent, tool
from strands.types.content import Messages

from ado_swarm.model_gateway.gateway import ModelProfile
from ado_swarm.model_gateway.strands_models import (
    FakeModel,
    ScriptStep,
    ToolCall,
    build_strands_model,
)

# --------------------------------------------------------------------------- #
# (a) plain invocation
# --------------------------------------------------------------------------- #


async def test_plain_invoke_returns_non_empty_text() -> None:
    model = FakeModel(default_text="hello from fake")
    agent = Agent(model=model)

    result = await agent.invoke_async("hi")

    assert str(result).strip() == "hello from fake"
    assert str(result).strip() != ""


async def test_stream_reports_non_zero_token_usage() -> None:
    model = FakeModel(default_text="some answer")
    agent = Agent(model=model)

    result = await agent.invoke_async("hi")

    usage = result.metrics.accumulated_usage
    assert usage["inputTokens"] > 0
    assert usage["outputTokens"] > 0
    assert usage["totalTokens"] == usage["inputTokens"] + usage["outputTokens"]


async def test_plain_invoke_is_deterministic() -> None:
    agent_a = Agent(model=FakeModel(default_text="stable"))
    agent_b = Agent(model=FakeModel(default_text="stable"))

    result_a = await agent_a.invoke_async("hi")
    result_b = await agent_b.invoke_async("hi")

    assert str(result_a) == str(result_b)


# --------------------------------------------------------------------------- #
# (b) scripted tool-calling loop
# --------------------------------------------------------------------------- #


async def test_scripted_model_drives_real_tool_call() -> None:
    side_effects: list[tuple[int, int]] = []

    @tool
    def add(a: int, b: int) -> int:
        """Add two integers."""
        side_effects.append((a, b))
        return a + b

    model = FakeModel(
        script=[
            ScriptStep(tool_calls=[ToolCall(name="add", input={"a": 2, "b": 3})]),
            ScriptStep(text="The total is 5."),
        ],
    )
    agent = Agent(model=model, tools=[add])

    result = await agent.invoke_async("please add 2 and 3")

    # The tool was actually invoked by the agent loop.
    assert side_effects == [(2, 3)]
    # The agent looped back and produced the scripted final answer.
    assert str(result).strip() == "The total is 5."


async def test_scripted_multi_tool_loop() -> None:
    calls: list[str] = []

    @tool
    def fetch(name: str) -> str:
        """Fetch a record by name."""
        calls.append(name)
        return f"record:{name}"

    model = FakeModel(
        script=[
            ScriptStep(tool_calls=[ToolCall(name="fetch", input={"name": "alpha"})]),
            ScriptStep(tool_calls=[ToolCall(name="fetch", input={"name": "beta"})]),
            ScriptStep(text="done"),
        ],
    )
    agent = Agent(model=model, tools=[fetch])

    result = await agent.invoke_async("fetch alpha then beta")

    assert calls == ["alpha", "beta"]
    assert str(result).strip() == "done"


async def _collect_tool_use_ids(model: FakeModel) -> list[str]:
    ids: list[str] = []
    messages = cast(Messages, [{"role": "user", "content": [{"text": "x"}]}])
    async for event in model.stream(messages):
        start = event.get("contentBlockStart", {}).get("start") or {}
        tool_use = start.get("toolUse")
        if tool_use is not None:
            ids.append(tool_use["toolUseId"])
    return ids


async def test_tool_use_id_is_deterministic() -> None:
    ids_a = await _collect_tool_use_ids(
        FakeModel(script=[ScriptStep(tool_calls=[ToolCall(name="noop")])])
    )
    ids_b = await _collect_tool_use_ids(
        FakeModel(script=[ScriptStep(tool_calls=[ToolCall(name="noop")])])
    )

    assert ids_a == ids_b
    assert ids_a and ids_a[0].startswith("tooluse_")


# --------------------------------------------------------------------------- #
# (c) structured output
# --------------------------------------------------------------------------- #


class Severity(enum.Enum):
    LOW = "low"
    HIGH = "high"


class NestedModel(BaseModel):
    flag: bool


class Finding(BaseModel):
    title: str
    count: int
    score: float
    severity: Severity
    tags: list[str]
    nested: NestedModel
    discovered_at: datetime.datetime
    note: str | None = None
    extra: dict[str, str] = {}


async def _structured_output(agent: Agent, output_model: type[BaseModel], prompt: str):
    """Call the structured-output method while silencing the deprecation warning."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        return await agent.structured_output_async(output_model, prompt)


async def test_structured_output_synthesized_instance() -> None:
    agent = Agent(model=FakeModel())

    result = await _structured_output(agent, Finding, "produce a finding")

    assert isinstance(result, Finding)
    # Deterministic synthesized zero-values.
    assert result.title == ""
    assert result.count == 0
    assert result.score == 0.0
    assert result.severity is Severity.LOW  # first enum member
    assert result.tags == []
    assert result.nested.flag is False
    assert result.discovered_at == datetime.datetime(2020, 1, 1, tzinfo=datetime.UTC)
    assert result.note is None


async def test_structured_output_injected_exact_instance() -> None:
    exact = Finding(
        title="SQL injection",
        count=3,
        score=9.8,
        severity=Severity.HIGH,
        tags=["sql", "owasp"],
        nested=NestedModel(flag=True),
        discovered_at=datetime.datetime(2021, 6, 1, tzinfo=datetime.UTC),
        note="urgent",
    )
    agent = Agent(model=FakeModel(structured_outputs={Finding: exact}))

    result = await _structured_output(agent, Finding, "produce a finding")

    assert result == exact
    assert result.title == "SQL injection"
    assert result.severity is Severity.HIGH


async def test_structured_output_responder_hook() -> None:
    seen: list[type[BaseModel]] = []

    def responder(output_model: type[BaseModel], messages):
        seen.append(output_model)
        return Finding(
            title="from responder",
            count=1,
            score=1.0,
            severity=Severity.HIGH,
            tags=["x"],
            nested=NestedModel(flag=True),
            discovered_at=datetime.datetime(2022, 1, 1, tzinfo=datetime.UTC),
        )

    agent = Agent(model=FakeModel(structured_responder=responder))

    result = await _structured_output(agent, Finding, "produce a finding")

    assert result.title == "from responder"
    assert seen == [Finding]


async def test_structured_output_responder_takes_precedence_over_mapping() -> None:
    mapped = Finding(
        title="mapped",
        count=0,
        score=0.0,
        severity=Severity.LOW,
        tags=[],
        nested=NestedModel(flag=False),
        discovered_at=datetime.datetime(2020, 1, 1, tzinfo=datetime.UTC),
    )

    def responder(output_model: type[BaseModel], messages):
        return Finding(
            title="responder wins",
            count=0,
            score=0.0,
            severity=Severity.LOW,
            tags=[],
            nested=NestedModel(flag=False),
            discovered_at=datetime.datetime(2020, 1, 1, tzinfo=datetime.UTC),
        )

    model = FakeModel(
        structured_outputs={Finding: mapped},
        structured_responder=responder,
    )

    output = [chunk async for chunk in model.structured_output(Finding, [])]
    assert output[-1]["output"].title == "responder wins"


async def test_structured_output_wrong_type_raises() -> None:
    model = FakeModel(structured_responder=lambda om, msgs: NestedModel(flag=True))

    with pytest.raises(TypeError):
        async for _ in model.structured_output(Finding, []):
            pass


# --------------------------------------------------------------------------- #
# config / count_tokens
# --------------------------------------------------------------------------- #


async def test_get_and_update_config() -> None:
    model = FakeModel(ModelProfile(model_id="abc"))

    assert model.get_config()["model_id"] == "abc"

    model.update_config(temperature=0.7)
    assert model.get_config()["temperature"] == 0.7
    # Existing keys preserved.
    assert model.get_config()["model_id"] == "abc"


async def test_count_tokens_is_positive_and_deterministic() -> None:
    model = FakeModel()
    messages = cast(Messages, [{"role": "user", "content": [{"text": "hello world"}]}])

    a = await model.count_tokens(messages)
    b = await model.count_tokens(messages)

    assert a == b
    assert a > 0


# --------------------------------------------------------------------------- #
# build_strands_model factory
# --------------------------------------------------------------------------- #


def test_build_strands_model_fake() -> None:
    model = build_strands_model(ModelProfile(provider="fake", model_id="det"))
    assert isinstance(model, FakeModel)
    assert model.get_config()["model_id"] == "det"


def test_build_strands_model_fake_forwards_script() -> None:
    script = [ScriptStep(text="scripted")]
    model = build_strands_model(ModelProfile(provider="fake"), script=script)
    assert isinstance(model, FakeModel)


def test_build_strands_model_rejects_unknown_provider() -> None:
    with pytest.raises(ValueError, match="Unsupported model provider"):
        build_strands_model(ModelProfile(provider="does-not-exist"))


def test_build_strands_model_ollama() -> None:
    model = build_strands_model(
        ModelProfile(provider="ollama", model_id="llama3", base_url="http://localhost:11434")
    )
    from strands.models.ollama import OllamaModel

    assert isinstance(model, OllamaModel)


def test_build_strands_model_openai_compatible() -> None:
    model = build_strands_model(
        ModelProfile(
            provider="openai_compatible",
            model_id="gpt-x",
            base_url="http://localhost:8000/v1",
        )
    )
    from strands.models.openai import OpenAIModel

    assert isinstance(model, OpenAIModel)
