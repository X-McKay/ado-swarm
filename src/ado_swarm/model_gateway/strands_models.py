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

import datetime as _dt
import enum
import json
import uuid
from collections.abc import AsyncGenerator, Callable, Sequence
from typing import TYPE_CHECKING, Any, TypeVar

from pydantic import BaseModel
from pydantic.fields import FieldInfo

from ado_swarm.model_gateway.gateway import ModelProfile

if TYPE_CHECKING:
    from strands.models import Model as _StrandsModel
    from strands.types.content import Messages, SystemContentBlock
    from strands.types.streaming import StreamEvent
    from strands.types.tools import ToolChoice, ToolSpec

from strands.models import Model

T = TypeVar("T", bound=BaseModel)

# A deterministic fixed epoch used whenever a datetime value must be synthesized.
_FIXED_EPOCH = _dt.datetime(2020, 1, 1, 0, 0, 0, tzinfo=_dt.UTC)


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


# Type alias for the structured-output responder hook.
StructuredResponder = Callable[[type[BaseModel], "Messages"], BaseModel]


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
        """
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

    # -- structured output ---------------------------------------------------

    async def structured_output(
        self,
        output_model: type[T],
        prompt: Messages,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[dict[str, T | Any], None]:
        """Yield ``{"output": <instance of output_model>}`` deterministically."""
        if self._structured_responder is not None:
            instance = self._structured_responder(output_model, prompt)
        elif output_model in self._structured_outputs:
            instance = self._structured_outputs[output_model]
        else:
            instance = self._synthesize_model(output_model)

        if not isinstance(instance, output_model):
            raise TypeError(
                f"Structured output for {output_model.__name__} is "
                f"{type(instance).__name__}, expected an instance of {output_model.__name__}"
            )
        yield {"output": instance}

    @classmethod
    def _synthesize_model(cls, output_model: type[T]) -> T:
        """Build a valid instance filling required fields with zero-values."""
        values: dict[str, Any] = {}
        for name, field in output_model.model_fields.items():
            if not field.is_required():
                continue
            values[name] = cls._synthesize_field(field)
        return output_model(**values)

    @classmethod
    def _synthesize_field(cls, field: FieldInfo) -> Any:
        """Synthesize a deterministic, type-appropriate value for a field."""
        return cls._synthesize_value(field.annotation)

    @classmethod
    def _synthesize_value(cls, annotation: Any) -> Any:
        """Return a deterministic zero-value for the given type annotation."""
        import typing

        origin = typing.get_origin(annotation)
        args = typing.get_args(annotation)

        # Optional / Union: pick the first non-None member.
        if origin in (typing.Union,) or _is_union(annotation):
            non_none = [a for a in args if a is not type(None)]
            if not non_none:
                return None
            return cls._synthesize_value(non_none[0])

        if origin in (list, set, tuple, frozenset):
            return [] if origin is not tuple else ()
        if origin is dict:
            return {}

        if isinstance(annotation, type):
            if issubclass(annotation, enum.Enum):
                return next(iter(annotation))
            if issubclass(annotation, BaseModel):
                return cls._synthesize_model(annotation)
            if issubclass(annotation, bool):
                return False
            if issubclass(annotation, int):
                return 0
            if issubclass(annotation, float):
                return 0.0
            if issubclass(annotation, str):
                return ""
            if issubclass(annotation, bytes):
                return b""
            if issubclass(annotation, _dt.datetime):
                return _FIXED_EPOCH
            if issubclass(annotation, _dt.date):
                return _FIXED_EPOCH.date()
            if issubclass(annotation, (list, set, frozenset)):
                return []
            if issubclass(annotation, dict):
                return {}

        # Fallback for bare ``list``/``dict``/``Any`` and anything unknown.
        if annotation in (list, Sequence):
            return []
        if annotation is dict:
            return {}
        return None


def _is_union(annotation: Any) -> bool:
    """Return True for both ``typing.Union`` and PEP 604 ``X | Y`` unions."""
    import types
    import typing

    return typing.get_origin(annotation) is typing.Union or isinstance(annotation, types.UnionType)


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
    provider = profile.provider

    if provider == "fake":
        return FakeModel(profile, **fake_kwargs)

    if provider == "ollama":
        from strands.models.ollama import OllamaModel

        return OllamaModel(host=profile.base_url, model_id=profile.model_id)

    if provider in ("openai", "openai_compatible"):
        from strands.models.openai import OpenAIModel

        return OpenAIModel(
            client_args={
                "api_key": profile.api_key or "not-needed",
                "base_url": profile.base_url,
            },
            model_id=profile.model_id,
            params=profile.params
            or {"temperature": profile.temperature, "max_tokens": profile.max_tokens},
        )

    if provider == "litellm":
        from strands.models.litellm import LiteLLMModel

        return LiteLLMModel(model_id=profile.model_id)

    if provider == "bedrock":
        from strands.models import BedrockModel

        return BedrockModel(model_id=profile.model_id, region_name=profile.region)

    raise ValueError(f"Unsupported model provider: {provider}")
