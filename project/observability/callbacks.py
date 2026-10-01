"""
LangChain callbacks for observability: token tracking and tool call logging.
"""

from __future__ import annotations

import time
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler


class TokenTrackingCallback(BaseCallbackHandler):
    """Tracks token usage from LLM calls."""

    def __init__(self, logger, phase: str):
        self.logger = logger
        self.phase = phase

    def on_llm_end(self, response, **kwargs) -> None:
        """Called when LLM call finishes."""
        if response and hasattr(response, "usage_metadata") and response.usage_metadata:
            usage = response.usage_metadata
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)
            self.logger.record_tokens(self.phase, input_tokens, output_tokens)


class ToolCallCallback(BaseCallbackHandler):
    """Tracks tool calls: which tools, arguments, results, latencies."""

    def __init__(self, logger):
        self.logger = logger
        self.tool_start_times: dict[str, float] = {}

    def on_tool_start(self, serialized: dict, input_str: str, **kwargs) -> None:
        """Called when a tool starts."""
        tool_name = serialized.get("name", "unknown")
        self.tool_start_times[tool_name] = time.time()
        self.logger.logger.debug(f"Tool START: {tool_name} with input: {input_str}")

    def on_tool_end(self, output: str, **kwargs) -> None:
        """Called when a tool finishes successfully."""
        tool_name = kwargs.get("name", "unknown")
        start_time = self.tool_start_times.pop(tool_name, time.time())
        latency_ms = (time.time() - start_time) * 1000

        # Try to parse structured output
        try:
            import json
            args = json.loads(kwargs.get("input_str", "{}")) if "input_str" in kwargs else {}
        except Exception:
            args = {"raw_input": str(kwargs.get("input_str", ""))}

        try:
            result = json.loads(output) if output else None
        except Exception:
            result = output

        self.logger.record_tool_call(
            tool_name=tool_name,
            args=args,
            result=result,
            error=None,
            latency_ms=latency_ms,
        )

    def on_tool_error(self, error: Exception | KeyboardInterrupt, **kwargs) -> None:
        """Called when a tool fails."""
        tool_name = kwargs.get("name", "unknown")
        start_time = self.tool_start_times.pop(tool_name, time.time())
        latency_ms = (time.time() - start_time) * 1000

        try:
            import json
            args = json.loads(kwargs.get("input_str", "{}")) if "input_str" in kwargs else {}
        except Exception:
            args = {"raw_input": str(kwargs.get("input_str", ""))}

        error_msg = f"{type(error).__name__}: {str(error)}"
        self.logger.record_tool_call(
            tool_name=tool_name,
            args=args,
            result=None,
            error=error_msg,
            latency_ms=latency_ms,
        )

    def on_chain_start(self, serialized: dict, inputs: dict, **kwargs) -> None:
        """Called when an agent step starts."""
        chain_name = serialized.get("name", "unknown")
        self.logger.logger.debug(f"Chain START: {chain_name}")

    def on_chain_end(self, outputs: dict, **kwargs) -> None:
        """Called when an agent step finishes."""
        chain_name = kwargs.get("name", "unknown")
        self.logger.logger.debug(f"Chain END: {chain_name}")
