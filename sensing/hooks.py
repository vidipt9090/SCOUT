"""CrewAI hooks writing to the shared trace. after_llm_call does not fire on a tool-call turn, so model calls are counted at before_llm_call."""
import threading

from crewai.hooks import after_llm_call, after_tool_call, before_llm_call, before_tool_call

from scout_platform.rate_limit import wait_for_slot
from scout_platform.tracing.writer import TraceWriter

_current: dict[str, TraceWriter | str | None] = {"writer": None, "prompt_version": None}
_lock = threading.Lock()


def use_trace(writer: TraceWriter, prompt_version: str | None = None) -> None:
    with _lock:
        _current.update(writer=writer, prompt_version=prompt_version)


def _emit(ctx, event_type: str, **kwargs) -> None:
    writer = _current["writer"]
    if writer is not None:
        agent = getattr(getattr(ctx, "agent", None), "role", None) or "unknown"
        writer.event(agent, event_type, prompt_version=_current["prompt_version"], **kwargs)


@before_llm_call
def _on_model_start(ctx):
    waited = wait_for_slot()
    if waited:
        _emit(ctx, "rate_wait", payload_ref=f"{waited:.1f}")
    _emit(ctx, "model_start")


@after_llm_call
def _on_model_end(ctx):
    _emit(ctx, "model_end")


@before_tool_call
def _on_tool_start(ctx):
    _emit(ctx, "tool_start", tool_name=ctx.tool_name, args=ctx.tool_input)


@after_tool_call
def _on_tool_end(ctx):
    _emit(ctx, "tool_end", tool_name=ctx.tool_name)
