"""
Wraps agent tools to capture execution metrics (latency, errors, args, results).
"""

from __future__ import annotations

import functools
import json
import time
from typing import Any, Callable


def wrap_tool_for_tracing(logger, tool_func: Callable) -> Callable:
    """Wraps a tool function to trace execution metrics."""

    @functools.wraps(tool_func)
    def wrapper(*args, **kwargs) -> Any:
        tool_name = tool_func.__name__
        start_time = time.time()

        # Capture arguments
        try:
            args_dict = {f"arg_{i}": arg for i, arg in enumerate(args)}
            args_dict.update(kwargs)
        except Exception:
            args_dict = {"raw_args": str(args), "raw_kwargs": str(kwargs)}

        try:
            result = tool_func(*args, **kwargs)
            latency_ms = (time.time() - start_time) * 1000
            logger.record_tool_call(
                tool_name=tool_name,
                args=args_dict,
                result=str(result)[:500],  # Limit result size
                error=None,
                latency_ms=latency_ms,
            )
            return result
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            error_msg = f"{type(e).__name__}: {str(e)}"
            logger.record_tool_call(
                tool_name=tool_name,
                args=args_dict,
                result=None,
                error=error_msg,
                latency_ms=latency_ms,
            )
            # Re-raise so the error is handled by the agent
            raise

    return wrapper


def create_traced_tools(tools_list: list, logger) -> list:
    """Wraps all tools in a list for tracing."""
    return [wrap_tool_for_tracing(logger, tool) for tool in tools_list]
