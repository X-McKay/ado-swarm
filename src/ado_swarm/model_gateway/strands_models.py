"""Deterministic Strands model layer for offline, hermetic CI runs.

This module provides :class:`FakeModel`, a fully deterministic, network-free
implementation of the Strands ``strands.models.Model`` ABC. It emits a valid
event sequence that the real Strands ``Agent`` event loop accepts, including a
scripted tool-calling mode that drives the agent through an actual tool-use loop.

It also provides :func:`build_strands_model`, a factory that maps a
:class:`~ado_swarm.model_gateway.gateway.ModelProfile` to a concrete Strands
model. Provider classes are lazily imported so that ``fake`` works without any
optional model dependencies installed.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncGenerator, Sequence
from typing import TYPE_CHECKING, Any, TypeVar, cast

from pydantic import BaseModel

from ado_swarm.model_gateway.factory import build_provider_model
from ado_swarm.model_gateway.gateway import ModelProfile
from ado_swarm.model_gateway.structured_output import (
    StructuredResponder,
    resolve_structured_instance,
    synthesize_model,
)

if TYPE_CHECKING:
    from strands.models import Model as _StrandsModel
    from strands.types.content import Messages, SystemContentBlock
    from strands.types.streaming import StreamEvent
    from strands.types.tools import ToolChoice, ToolSpec

from strands.models import Model

T = TypeVar("T", bound=BaseModel)


class ToolCall(BaseModel):
    """A scripted tool invocation the :class:`FakeModel` should emit.

    Attributes:
        name: The name of the tool to invoke (must match a registered ``@tool``).
        input: The JSON-serializable arguments to pass to the tool.
        tool_use_id: Optional stable id; a deterministic one is generated if omitted.
    """

    name: str
    input: dict[str, Any] = {}
    tool_use_id: str | None = None


class ScriptStep(BaseModel):
    """A single scripted turn for :class:`FakeModel`.

    Exactly one of ``text`` or ``tool_calls`` should be meaningful per step. If
    ``tool_calls`` is non-empty the step emits a ``tool_use`` turn; otherwise it
    emits a final text turn with ``stopReason="end_turn"``.
    """

    text: str = ""
    tool_calls: list[ToolCall] = []


class FakeModel(Model):
    """A deterministic, offline implementation of the Strands ``Model`` ABC.

    The model drives the real Strands ``Agent`` event loop without any network
    access. Two streaming modes are supported:

    * **Default mode** -- every ``stream`` call emits a single text turn whose
      content is :attr:`default_text` (deterministic).
    * **Scripted mode** -- when ``script`` is provided, each ``stream`` call
      consumes the next :class:`ScriptStep`. Steps with ``tool_calls`` emit a
      ``tool_use`` turn so the agent actually invokes the tool; the following
      step (after tool results land in the message history) emits the final
      answer. This proves the agent loops over tools.

    Structured output is deterministic too. Resolution order per call:

    1. ``structured_responder(output_model, messages)`` if provided.
    2. An exact instance from ``structured_outputs[output_model]`` if present.
    3. A synthesized instance built from field defaults / type-appropriate
       zero values (see :meth:`_synthesize_model`).
    """

    def __init__(
        self,
        profile: ModelProfile | None = None,
        *,
        default_text: str = "ok",
        script: Sequence[ScriptStep] | None = None,
        structured_outputs: dict[type[BaseModel], BaseModel] | None = None,
        structured_responder: StructuredResponder | None = None,
        **config: Any,
    ) -> None:
        """Construct a deterministic fake model.

        Args:
            profile: Optional model profile; only used to seed ``model_id`` in the
                stored config. A default profile is used when omitted.
            default_text: Text emitted by every non-scripted ``stream`` call.
            script: Optional ordered scripted turns enabling tool-calling mode.
            structured_outputs: Mapping of output-model class to an exact instance
                returned by ``structured_output`` for that class.
            structured_responder: Callable that returns an exact instance given the
                requested output model and prompt messages. Takes precedence over
                ``structured_outputs``.
            **config: Extra config overrides merged into :meth:`get_config`.
        """
        self._profile = profile or ModelProfile()
        self.default_text = default_text
        self._script: list[ScriptStep] = list(script) if script is not None else []
        self._step_index = 0
        self._structured_outputs = dict(structured_outputs or {})
        self._structured_responder = structured_responder
        self.config: dict[str, Any] = {
            "model_id": self._profile.model_id,
            "params": dict(self._profile.params),
            **config,
        }

    # -- configuration -------------------------------------------------------

    def get_config(self) -> dict[str, Any]:
        """Return the stored model configuration dict."""
        return self.config

    def update_config(self, **model_config: Any) -> None:
        """Merge ``model_config`` into the stored configuration."""
        self.config.update(model_config)

    async def count_tokens(
        self,
        messages: Messages,
        tool_specs: list[ToolSpec] | None = None,
        system_prompt: str | None = None,
        system_prompt_content: list[SystemContentBlock] | None = None,
    ) -> int:
        """Cheap deterministic length-based token estimate (chars / 4)."""
        chars = len(json.dumps(messages, default=str))
        if system_prompt:
            chars += len(system_prompt)
        if tool_specs:
            chars += len(json.dumps(tool_specs, default=str))
        return max(1, chars // 4)

    # -- streaming -----------------------------------------------------------

    async def stream(
        self,
        messages: Messages,
        tool_specs: list[ToolSpec] | None = None,
        system_prompt: str | None = None,
        *,
        tool_choice: ToolChoice | None = None,
        system_prompt_content: list[SystemContentBlock] | None = None,
        invocation_state: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[StreamEvent, None]:
        """Emit a deterministic, Strands-compatible event sequence.

        The sequence mirrors a real provider:
        ``messageStart`` -> ``contentBlockStart`` -> ``contentBlockDelta`` ->
        ``contentBlockStop`` -> ``messageStop`` -> ``metadata``. In scripted
        tool-use turns a ``toolUse`` content block is emitted and the message
        stops with ``stopReason="tool_use"``.

        Structured-output forcing: when the Strands event loop forces structured
        output it re-invokes ``stream`` with ``tool_choice`` set (the forced
        ``{"any": {}}`` / ``{"tool": {...}}`` shape) and ``tool_specs`` reduced
        to the single structured-output tool. This branch detects that case and
        emits a ``toolUse`` for the forced tool whose ``input`` is the resolved
        structured-output instance (serialized to JSON) -- *without* consuming a
        scripted step -- so the non-deprecated
        ``invoke_async(structured_output_model=...)`` path works.
        """
        forced = self._forced_structured_output(tool_specs, tool_choice, invocation_state)
        if forced is not None:
            async for event in self._stream_forced_structured_output(
                forced, messages, tool_specs, system_prompt
            ):
                yield event
            return

        step = self._next_step()

        input_tokens = await self.count_tokens(messages, tool_specs, system_prompt)

        yield {"messageStart": {"role": "assistant"}}

        output_chars = 0
        if step.tool_calls:
            for tool_call in step.tool_calls:
                tool_use_id = tool_call.tool_use_id or _deterministic_tool_use_id(
                    self._step_index, tool_call.name
                )
                yield {
                    "contentBlockStart": {
                        "start": {"toolUse": {"name": tool_call.name, "toolUseId": tool_use_id}}
                    }
                }
                serialized = json.dumps(tool_call.input)
                output_chars += len(serialized)
                yield {"contentBlockDelta": {"delta": {"toolUse": {"input": serialized}}}}
                yield {"contentBlockStop": {}}
            stop_reason = "tool_use"
        else:
            text = step.text or self.default_text
            output_chars += len(text)
            yield {"contentBlockStart": {"start": {}}}
            yield {"contentBlockDelta": {"delta": {"text": text}}}
            yield {"contentBlockStop": {}}
            stop_reason = "end_turn"

        yield {"messageStop": {"stopReason": stop_reason}}

        output_tokens = max(1, output_chars // 4)
        yield {
            "metadata": {
                "usage": {
                    "inputTokens": input_tokens,
                    "outputTokens": output_tokens,
                    "totalTokens": input_tokens + output_tokens,
                },
                "metrics": {"latencyMs": 1},
            }
        }

    def _next_step(self) -> ScriptStep:
        """Return the scripted step for this ``stream`` call (deterministic)."""
        if not self._script:
            return ScriptStep(text=self.default_text)
        if self._step_index < len(self._script):
            step = self._script[self._step_index]
        else:
            # Past the end of the script: emit a deterministic terminal answer
            # so the agent loop always terminates rather than hanging.
            step = ScriptStep(text=self.default_text)
        self._step_index += 1
        return step

    # -- forced structured output (non-deprecated path) ----------------------

    def _forced_structured_output(
        self,
        tool_specs: list[ToolSpec] | None,
        tool_choice: ToolChoice | None,
        invocation_state: dict[str, Any] | None,
    ) -> tuple[type[BaseModel], ToolSpec] | None:
        """Detect a forced structured-output ``stream`` call.

        Strands' event loop forces structured output by re-invoking ``stream``
        with a truthy ``tool_choice`` (the ``{"any": {}}`` / ``{"tool": {...}}``
        shape) and ``tool_specs`` reduced to the single structured-output tool
        spec (whose ``name`` equals the Pydantic model class name).

        Returns the resolved ``(output_model, tool_spec)`` pair when this call is
        a forced structured-output request, or ``None`` for an ordinary call.
        """
        if not tool_choice or not tool_specs:
            return None

        # In forced mode Strands passes exactly the one structured-output tool.
        # Identify the spec named by an explicit ``{"tool": {"name": ...}}``
        # choice, otherwise the sole spec for an ``{"any": {}}`` choice.
        forced_name = None
        choice = cast("dict[str, Any]", tool_choice)
        if isinstance(choice, dict):
            tool_sel = choice.get("tool")
            if isinstance(tool_sel, dict):
                forced_name = tool_sel.get("name")

        candidate: ToolSpec | None = None
        if forced_name is not None:
            candidate = next((s for s in tool_specs if s.get("name") == forced_name), None)
        elif len(tool_specs) == 1:
            candidate = tool_specs[0]
        if candidate is None:
            return None

        output_model = self._resolve_output_model(candidate, invocation_state)
        if output_model is None:
            return None
        return output_model, candidate

    @staticmethod
    def _resolve_output_model(
        tool_spec: ToolSpec,
        invocation_state: dict[str, Any] | None,
    ) -> type[BaseModel] | None:
        """Recover the exact ``output_model`` type backing a structured-output tool.

        The event loop registers a ``StructuredOutputTool`` (whose
        ``structured_output_model`` is the original Pydantic class) as a dynamic
        tool on the agent, and stores the agent on ``invocation_state``. Matching
        the forced tool spec's ``name`` against that registry recovers the exact
        type, so responder / mapping / synthesis all dispatch correctly.
        """
        tool_name = tool_spec.get("name")
        if not tool_name or not invocation_state:
            return None
        agent = invocation_state.get("agent")
        registry = getattr(agent, "tool_registry", None)
        if registry is None:
            return None
        for tools in (
            getattr(registry, "dynamic_tools", {}),
            getattr(registry, "registry", {}),
        ):
            tool = tools.get(tool_name)
            model = getattr(tool, "structured_output_model", None)
            if isinstance(model, type) and issubclass(model, BaseModel):
                return model
        return None

    async def _stream_forced_structured_output(
        self,
        forced: tuple[type[BaseModel], ToolSpec],
        messages: Messages,
        tool_specs: list[ToolSpec] | None,
        system_prompt: str | None,
    ) -> AsyncGenerator[StreamEvent, None]:
        """Emit a ``toolUse`` for the forced structured-output tool.

        The ``input`` is the resolved structured-output instance serialized to
        JSON (``model_dump(mode="json")``), which round-trips back through the
        tool's Pydantic validation in the event loop. Resolution reuses the
        existing precedence: responder -> mapping -> synthesized instance.
        """
        output_model, tool_spec = forced
        instance = self._resolve_structured_instance(output_model, messages)
        tool_name = str(tool_spec.get("name"))
        tool_use_id = _deterministic_tool_use_id(self._step_index, tool_name)

        input_tokens = await self.count_tokens(messages, tool_specs, system_prompt)

        yield {"messageStart": {"role": "assistant"}}
        yield {
            "contentBlockStart": {
                "start": {"toolUse": {"name": tool_name, "toolUseId": tool_use_id}}
            }
        }
        serialized = json.dumps(instance.model_dump(mode="json"))
        yield {"contentBlockDelta": {"delta": {"toolUse": {"input": serialized}}}}
        yield {"contentBlockStop": {}}
        yield {"messageStop": {"stopReason": "tool_use"}}

        output_tokens = max(1, len(serialized) // 4)
        yield {
            "metadata": {
                "usage": {
                    "inputTokens": input_tokens,
                    "outputTokens": output_tokens,
                    "totalTokens": input_tokens + output_tokens,
                },
                "metrics": {"latencyMs": 1},
            }
        }

    def _resolve_structured_instance(
        self, output_model: type[BaseModel], messages: Messages
    ) -> BaseModel:
        """Resolve a structured-output instance using the shared helper."""
        return resolve_structured_instance(
            output_model,
            messages,
            structured_outputs=self._structured_outputs,
            structured_responder=self._structured_responder,
        )

    # -- structured output ---------------------------------------------------

    async def structured_output(
        self,
        output_model: type[T],
        prompt: Messages,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[dict[str, T | Any], None]:
        """Yield ``{"output": <instance of output_model>}`` deterministically."""
        instance = self._resolve_structured_instance(output_model, prompt)
        yield {"output": cast("T", instance)}

    @classmethod
    def _synthesize_model(cls, output_model: type[T]) -> T:
        """Build a valid instance filling required fields with zero-values."""
        return synthesize_model(output_model)


def _deterministic_tool_use_id(step_index: int, tool_name: str) -> str:
    """Generate a stable, deterministic tool-use id for a scripted call."""
    seed = f"fake-{step_index}-{tool_name}"
    digest = uuid.uuid5(uuid.NAMESPACE_OID, seed).hex[:24]
    return f"tooluse_{digest}"


def build_strands_model(profile: ModelProfile, **fake_kwargs: Any) -> _StrandsModel:
    """Build a concrete Strands model from a :class:`ModelProfile`.

    Provider classes are imported lazily so that the ``fake`` provider works
    without any optional model dependency installed.

    Args:
        profile: The model profile selecting provider and options.
        **fake_kwargs: Extra keyword arguments forwarded to :class:`FakeModel`
            (e.g. ``script=...`` or ``structured_outputs=...``). Ignored for
            non-fake providers.

    Returns:
        A concrete ``strands.models.Model`` instance.

    Raises:
        ValueError: If the provider is not supported.
    """
    return build_provider_model(
        profile, fake_model_factory=lambda fake_profile: FakeModel(fake_profile, **fake_kwargs)
    )
