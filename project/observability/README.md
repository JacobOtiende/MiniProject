# Observability: Logging, Token Tracking, and Tool Tracing

MiniProject now includes comprehensive observability infrastructure to track agent behavior, costs, and performance.

## What Gets Logged

### 1. **Tool Call Tracing** — Every tool execution is recorded
- Tool name
- Input arguments
- Output/result
- Execution latency
- Success/failure status
- Timestamps

Example: When the agent calls `check_emails()`, you get:
```json
{
  "tool_name": "check_emails",
  "args": {"folder": "inbox"},
  "result": "Found 3 emails",
  "error": null,
  "latency_ms": 123.45,
  "timestamp": "2026-09-30T20:15:17.123456"
}
```

### 2. **Token Usage Tracking** — LLM token consumption and cost
- Input tokens per phase
- Output tokens per phase
- Total tokens
- Estimated cost (GPT-4o pricing)

Example:
```json
{
  "phase": "triage",
  "input_tokens": 1250,
  "output_tokens": 856,
  "total_tokens": 2106,
  "cost_usd": 0.0087
}
```

### 3. **Structured Logging** — Agent activity logged to file and console
- Phase transitions
- Tool execution (success/failure)
- Token usage
- Run summary

### 4. **Metrics** — Aggregated statistics for the entire run
- Duration
- Phases run
- Tool success rate
- Total cost
- Errors encountered

## Output Files

After each run, four files are created in `./logs/`:

```
logs/
├── YYYYMMDD_HHMMSS_agent.log        # Structured logs (text)
├── YYYYMMDD_HHMMSS_metrics.json     # Run metrics & summary
├── YYYYMMDD_HHMMSS_tool_calls.json  # Detailed tool trace
└── YYYYMMDD_HHMMSS_tokens.json      # Token usage breakdown
```

### agent.log Example
```
2026-09-30 20:15:17,132 - observability.logging - INFO - === Phase: triage START ===
2026-09-30 20:15:17,134 - observability.logging - INFO - Tool check_emails succeeded in 123.5ms
2026-09-30 20:15:17,134 - observability.logging - INFO - Tool log_task succeeded in 45.2ms
2026-09-30 20:15:17,136 - observability.logging - INFO - Phase triage: 1250 input + 856 output tokens ($0.0087)
```

### metrics.json Example
```json
{
  "run_id": "20260930_201517",
  "start_time": "2026-09-30T20:15:17.132000",
  "end_time": "2026-09-30T20:15:25.845000",
  "duration_seconds": 8.713,
  "phases_run": ["triage", "rundown", "achievements", "review"],
  "total_tool_calls": 12,
  "failed_tool_calls": 1,
  "total_input_tokens": 5234,
  "total_output_tokens": 3128,
  "total_cost_usd": 0.0342,
  "errors": ["bad_tool: API Error: 500"]
}
```

### tool_calls.json Example
```json
[
  {
    "tool_name": "check_emails",
    "args": {"folder": "inbox"},
    "result": "Found 3 emails",
    "error": null,
    "latency_ms": 123.45,
    "timestamp": "2026-09-30T20:15:17.123456"
  },
  {
    "tool_name": "bad_tool",
    "args": {},
    "result": null,
    "error": "API Error: 500",
    "latency_ms": 1200.0,
    "timestamp": "2026-09-30T20:15:18.234567"
  }
]
```

## How to Use

### Automatic Tracking (No Code Changes Needed)

The observability system is already integrated into `main.py`. Just run as normal:

```bash
python main.py
```

You'll see a summary at the end:
```
=== Observability Summary ===
Logs saved to: ./logs/20260930_201517_metrics.json
Tool calls: 12 (91.7% success)
Total tokens: 8362 ($0.0342)
```

### Access Logs After a Run

```python
import json
from pathlib import Path

# Find latest run
logs_dir = Path("./logs")
latest_metrics = sorted(logs_dir.glob("*_metrics.json"))[-1]

# Load metrics
with open(latest_metrics) as f:
    metrics = json.load(f)

print(f"Run {metrics['run_id']}:")
print(f"  Duration: {metrics['duration_seconds']:.1f}s")
print(f"  Cost: ${metrics['total_cost_usd']:.4f}")
print(f"  Tool calls: {metrics['total_tool_calls']}")
print(f"  Success rate: {(1 - metrics['failed_tool_calls']/metrics['total_tool_calls'])*100:.1f}%")
```

### Programmatic Usage

```python
from observability.logging import RunLogger

# Create logger
logger = RunLogger(run_id="my_custom_id", logs_dir="./logs")

# Record activity
logger.record_phase_start("triage")
logger.record_tool_call("check_emails", {"folder": "inbox"}, "3 emails", None, 123.45)
logger.record_tokens("triage", 1250, 856)
logger.record_phase_end("triage")

# Save everything
summary = logger.finalize()
print(f"Cost this run: ${summary['token_summary']['total_cost_usd']:.4f}")
```

## Pricing

GPT-4o pricing (current):
- **Input:** $0.003 / 1K tokens
- **Output:** $0.006 / 1K tokens

Modify in `logging.py` if pricing changes.

## Performance Impact

Observability adds minimal overhead:
- Tool wrapping: <1ms per tool call
- Token tracking: <1ms per LLM call
- File I/O: ~10-50ms at run end (one-time)

## Troubleshooting

### "Logs saved to but I can't find the files"
Check `./logs/` directory. If it doesn't exist, create it:
```bash
mkdir logs
```

### "Cost seems wrong"
Verify the pricing constants in `observability/logging.py`. OpenAI's pricing changes periodically.

### "Tool calls not showing up in the trace"
Make sure `deps.logger` is set. The tool wrapper logs to `deps.logger` if available, but silently skips if it's `None`.

## Future Enhancements

- [ ] Circuit breaker for repeated tool failures
- [ ] Context window size tracking
- [ ] Per-phase performance comparison
- [ ] Cost alerts/thresholds
- [ ] Structured output format (JSON) for LLM responses
