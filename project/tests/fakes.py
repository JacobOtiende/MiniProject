"""
Fakes used only in tests — no real network or LLM calls happen here.
"""
from __future__ import annotations

from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import PrivateAttr


class ScriptedChatModel(BaseChatModel):
    """Drives langgraph's create_react_agent loop deterministically: returns
    one pre-scripted AIMessage (with or without tool_calls) per call, in
    order. When the scripted message has no tool_calls, the ReAct loop
    treats it as the final answer and stops."""

    responses: list[AIMessage]
    _index: int = PrivateAttr(default=0)

    @property
    def _llm_type(self) -> str:
        return "scripted-fake"

    def bind_tools(self, tools: Any, **kwargs: Any) -> "ScriptedChatModel":
        # create_react_agent binds tool schemas at build time; irrelevant
        # here since every response is pre-scripted, not generated.
        return self

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        if self._index >= len(self.responses):
            raise AssertionError(
                f"ScriptedChatModel ran out of responses after {self._index} calls. "
                f"Last messages seen: {messages[-2:]}"
            )
        message = self.responses[self._index]
        self._index += 1
        return ChatResult(generations=[ChatGeneration(message=message)])


class FakeToolCallMessage:
    """Convenience builder for a scripted AIMessage with tool calls."""

    @staticmethod
    def with_calls(calls: list[dict]) -> AIMessage:
        # Each call: {"name": ..., "args": {...}, "id": "..."}
        return AIMessage(content="", tool_calls=calls)

    @staticmethod
    def final(text: str) -> AIMessage:
        return AIMessage(content=text)


class _Exec:
    def __init__(self, result: Any):
        self._result = result

    def execute(self) -> Any:
        return self._result


class FakeEventsResource:
    def __init__(self, existing_events: list[dict] | None = None):
        self.existing_events = existing_events or []
        self.created: list[dict] = []

    def list(self, timeMin: str | None = None, timeMax: str | None = None, **kwargs) -> _Exec:
        # Real overlap filtering (mirrors tools/demo_calendar.py) — needed
        # because propose_alternate_times walks real candidate windows and
        # must actually see them as conflict-free once they don't overlap.
        from datetime import datetime

        if timeMin is None or timeMax is None:
            return _Exec({"items": self.existing_events})
        window_start = datetime.fromisoformat(timeMin)
        window_end = datetime.fromisoformat(timeMax)
        items = []
        for event in self.existing_events:
            ev_start = datetime.fromisoformat(event["start"]["dateTime"])
            ev_end = datetime.fromisoformat(event["end"]["dateTime"])
            if ev_start < window_end and ev_end > window_start:
                items.append(event)
        return _Exec({"items": items})

    def insert(self, **kwargs) -> _Exec:
        event_id = f"evt-{len(self.created) + 1}"
        self.created.append({"id": event_id, **kwargs.get("body", {})})
        return _Exec({"id": event_id})

    def patch(self, **kwargs) -> _Exec:
        return _Exec({})


class FakeCalendarService:
    def __init__(self, existing_events: list[dict] | None = None):
        self._events = FakeEventsResource(existing_events)

    def events(self) -> FakeEventsResource:
        return self._events
