"""
Logging infrastructure for MyAgent: structured logging, token tracking, and tool tracing.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class ToolCall:
    """A single tool execution record."""
    tool_name: str
    args: dict[str, Any]
    result: Any
    error: str | None = None
    latency_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class TokenUsage:
    """Token usage for a single LLM call."""
    phase: str  # "triage", "rundown", etc
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class RunMetrics:
    """Summary metrics for an entire run."""
    run_id: str
    start_time: str
    end_time: str | None = None
    duration_seconds: float = 0.0
    phases_run: list[str] = field(default_factory=list)
    total_tool_calls: int = 0
    failed_tool_calls: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_usd: float = 0.0
    errors: list[str] = field(default_factory=list)


def _serialize_for_json(obj: Any) -> Any:
    """Convert objects to JSON-serializable format."""
    if is_dataclass(obj) and not isinstance(obj, type):
        return asdict(obj)
    if isinstance(obj, (datetime, Path)):
        return str(obj)
    if isinstance(obj, Exception):
        return str(obj)
    return obj


class ToolCallTracer:
    """Tracks all tool calls: arguments, results, latencies, errors."""

    def __init__(self, logs_dir: str = "./logs"):
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(exist_ok=True)
        self.calls: list[ToolCall] = []

    def record_call(
        self,
        tool_name: str,
        args: dict[str, Any],
        result: Any = None,
        error: str | None = None,
        latency_ms: float = 0.0,
    ) -> None:
        """Record a tool call."""
        call = ToolCall(
            tool_name=tool_name,
            args=args,
            result=result,
            error=error,
            latency_ms=latency_ms,
        )
        self.calls.append(call)

    def save(self, run_id: str) -> Path:
        """Save trace to disk."""
        trace_file = self.logs_dir / f"{run_id}_tool_calls.json"
        with open(trace_file, "w") as f:
            json.dump(
                [asdict(call) for call in self.calls],
                f,
                indent=2,
                default=_serialize_for_json,
            )
        return trace_file

    def get_summary(self) -> dict[str, Any]:
        """Get summary stats."""
        failed = sum(1 for call in self.calls if call.error)
        total_latency = sum(call.latency_ms for call in self.calls)
        return {
            "total_calls": len(self.calls),
            "failed_calls": failed,
            "success_rate": (len(self.calls) - failed) / len(self.calls)
            if self.calls
            else 1.0,
            "total_latency_ms": total_latency,
            "avg_latency_ms": total_latency / len(self.calls) if self.calls else 0.0,
        }


class TokenUsageTracker:
    """Tracks token usage across all LLM calls."""

    def __init__(self, logs_dir: str = "./logs"):
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(exist_ok=True)
        self.usage: list[TokenUsage] = []
        # GPT-4o pricing (as of 2024)
        self.price_per_1k_input = 0.003
        self.price_per_1k_output = 0.006

    def record_usage(
        self,
        phase: str,
        input_tokens: int,
        output_tokens: int,
    ) -> None:
        """Record token usage for a phase."""
        total = input_tokens + output_tokens
        cost = (input_tokens * self.price_per_1k_input + output_tokens * self.price_per_1k_output) / 1000
        usage = TokenUsage(
            phase=phase,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total,
            cost_usd=cost,
        )
        self.usage.append(usage)

    def save(self, run_id: str) -> Path:
        """Save token usage to disk."""
        usage_file = self.logs_dir / f"{run_id}_tokens.json"
        with open(usage_file, "w") as f:
            json.dump(
                [asdict(u) for u in self.usage],
                f,
                indent=2,
                default=_serialize_for_json,
            )
        return usage_file

    def get_summary(self) -> dict[str, Any]:
        """Get aggregate stats."""
        total_input = sum(u.input_tokens for u in self.usage)
        total_output = sum(u.output_tokens for u in self.usage)
        total_cost = sum(u.cost_usd for u in self.usage)
        return {
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_tokens": total_input + total_output,
            "total_cost_usd": total_cost,
            "phases": {u.phase: asdict(u) for u in self.usage},
        }


class RunLogger:
    """Unified logging for a run: structured logs + metrics + traces."""

    def __init__(self, run_id: str | None = None, logs_dir: str = "./logs"):
        self.run_id = run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(exist_ok=True)

        # Set up Python logging
        log_file = self.logs_dir / f"{self.run_id}_agent.log"
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(),
            ],
        )
        self.logger = logging.getLogger(__name__)

        # Tracers
        self.tool_tracer = ToolCallTracer(logs_dir)
        self.token_tracker = TokenUsageTracker(logs_dir)

        # Metrics
        self.metrics = RunMetrics(
            run_id=self.run_id,
            start_time=datetime.now().isoformat(),
        )

    def record_phase_start(self, phase: str) -> None:
        """Log phase start."""
        self.metrics.phases_run.append(phase)
        self.logger.info(f"=== Phase: {phase} START ===")

    def record_phase_end(self, phase: str) -> None:
        """Log phase end."""
        self.logger.info(f"=== Phase: {phase} END ===")

    def record_tool_call(
        self,
        tool_name: str,
        args: dict[str, Any],
        result: Any = None,
        error: str | None = None,
        latency_ms: float = 0.0,
    ) -> None:
        """Record a tool call."""
        self.tool_tracer.record_call(tool_name, args, result, error, latency_ms)
        self.metrics.total_tool_calls += 1
        if error:
            self.metrics.failed_tool_calls += 1
            self.logger.error(f"Tool {tool_name} failed: {error}")
            self.metrics.errors.append(f"{tool_name}: {error}")
        else:
            self.logger.info(
                f"Tool {tool_name} succeeded in {latency_ms:.1f}ms"
            )

    def record_tokens(self, phase: str, input_tokens: int, output_tokens: int) -> None:
        """Record token usage."""
        self.token_tracker.record_usage(phase, input_tokens, output_tokens)
        self.metrics.total_input_tokens += input_tokens
        self.metrics.total_output_tokens += output_tokens
        cost = self.token_tracker.get_summary()["phases"][phase]["cost_usd"]
        self.metrics.total_cost_usd += cost
        self.logger.info(
            f"Phase {phase}: {input_tokens} input + {output_tokens} output tokens "
            f"(${cost:.4f})"
        )

    def record_error(self, error: str) -> None:
        """Record an error."""
        self.logger.error(error)
        self.metrics.errors.append(error)

    def finalize(self) -> None:
        """Save all logs and metrics."""
        self.metrics.end_time = datetime.now().isoformat()
        start = datetime.fromisoformat(self.metrics.start_time)
        end = datetime.fromisoformat(self.metrics.end_time)
        self.metrics.duration_seconds = (end - start).total_seconds()

        # Save traces
        tool_trace_file = self.tool_tracer.save(self.run_id)
        token_file = self.token_tracker.save(self.run_id)

        # Save metrics
        metrics_file = self.logs_dir / f"{self.run_id}_metrics.json"
        with open(metrics_file, "w") as f:
            json.dump(asdict(self.metrics), f, indent=2, default=_serialize_for_json)

        # Log summary
        tool_summary = self.tool_tracer.get_summary()
        token_summary = self.token_tracker.get_summary()

        self.logger.info("=== RUN SUMMARY ===")
        self.logger.info(f"Duration: {self.metrics.duration_seconds:.1f}s")
        self.logger.info(
            f"Tool calls: {tool_summary['total_calls']} "
            f"({tool_summary['success_rate']:.1%} success rate)"
        )
        self.logger.info(
            f"Tokens: {token_summary['total_tokens']} "
            f"(${token_summary['total_cost_usd']:.4f})"
        )
        self.logger.info(f"Files saved to {self.logs_dir}")

        # Close file handlers to release file locks
        for handler in self.logger.handlers:
            handler.close()

        return {
            "run_id": self.run_id,
            "metrics_file": str(metrics_file),
            "tool_trace_file": str(tool_trace_file),
            "token_file": str(token_file),
            "tool_summary": tool_summary,
            "token_summary": token_summary,
        }
