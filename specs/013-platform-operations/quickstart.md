# Quickstart: Platform & Operations Module

## Prerequisites

- Python 3.13+
- `uv` package manager
- Supabase project (Execution History storage)
- LangSmith account and API key
- OpenTelemetry Collector (optional, defaults to `http://localhost:4318`)

---

# Installation

Add dependencies to `pyproject.toml`:

```toml
[project]
dependencies = [
    ...
    "langsmith>=0.1.0",
    "opentelemetry-api>=1.20.0",
    "opentelemetry-sdk>=1.20.0",
    "opentelemetry-exporter-otlp-proto-http>=1.20.0",
]
```

Install dependencies:

```bash
uv sync
```

---

# Environment Configuration

```bash
# LangSmith
export LANGSMITH_API_KEY="ls_..."
export LANGSMITH_PROJECT="ai-marketing-agent"

# OpenTelemetry
export OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4318"
export OTEL_SERVICE_NAME="ai-marketing-agent-operations"

# Supabase
export SUPABASE_URL="https://project.supabase.co"
export SUPABASE_SERVICE_KEY="..."
```

---

# Architecture Overview

The Platform & Operations module is a passive observer.

It never executes workflows or generates AI content.

Instead, other modules emit execution events, and the Platform Operations module records operational telemetry.

```
Workflow Engine
        │
        │ emits execution events
        ▼
PlatformOperationsService
        │
 ┌──────┼──────────────┬─────────────┐
 │      │              │             │
 ▼      ▼              ▼             ▼
LangSmith      OpenTelemetry    JSON Logger
        │              │
        └──────┬───────┘
               ▼
      Metrics Collector
               ▼
      Execution History
               ▼
      Operational Guardrails
```

---

# Basic Usage

Create the public service.

```python
from modules.operations import PlatformOperationsService

operations = PlatformOperationsService()
```

Record the start of a workflow execution.

```python
trace = await operations.record_workflow_started(
    workflow_id="wf-001",
    workflow_type="campaign_generation",
)
```

Record an AI request.

```python
await operations.record_ai_request(
    workflow_id="wf-001",
    trace_id=trace.id,
    prompt_name="copy_generator",
    prompt_version=2,
    model_name="gpt-4o",
    model_version="2026-06",
    input_tokens=245,
    output_tokens=386,
    latency_ms=1180,
)
```

Record workflow completion.

```python
await operations.record_workflow_completed(
    workflow_id="wf-001",
    status="completed",
)
```

The module automatically:

- Creates LangSmith traces
- Emits OpenTelemetry spans
- Writes structured JSON logs
- Tracks token usage
- Calculates execution cost
- Updates operational metrics
- Stores execution history
- Evaluates operational guardrails

---

# Registering Prompt Versions

Register a new prompt template.

```python
prompt = await operations.register_prompt(
    name="copy_generator",
    template="Generate {tone} marketing copy for {platform}..."
)

print(prompt.version)
```

---

# Registering Model Versions

Register or update available AI models.

```python
await operations.register_model(
    model_name="gpt-4o",
    model_version="2026-06",
    provider="openai",
    input_token_cost=0.000005,
    output_token_cost=0.000015,
)
```

---

# Query Execution History

Retrieve execution history.

```python
results = await operations.search_execution_history(
    status="failed",
    start_time=datetime.now() - timedelta(hours=1),
    limit=50,
)
```

---

# Retrieve Metrics

Get the current operational metrics snapshot.

```python
metrics = await operations.get_metrics_snapshot()

print(metrics.latency_p95_ms)
print(metrics.failure_rate)
print(metrics.throughput)
```

---

# Retrieve Trace Information

Fetch execution trace metadata.

```python
trace = await operations.get_execution_trace(
    workflow_id="wf-001"
)
```

---

# Telemetry Buffer Status

Inspect telemetry buffering during backend outages.

```python
status = await operations.get_buffer_status()

print(status.queue_size)
print(status.retry_count)
print(status.dropped_events)
```

---

# Running Tests

```bash
# Unit tests
uv run pytest backend/tests/unit/operations/ -v

# Integration tests
uv run pytest backend/tests/integration/test_operations_pipeline.py -v

# Coverage
uv run pytest \
backend/tests/unit/operations/ \
backend/tests/integration/test_operations_pipeline.py \
--cov=src.modules.operations \
--cov-report=term
```

---

# Operational Notes

- **Observer Only** — Never executes workflows or AI generation.
- **Non-Blocking** — Observability failures never interrupt workflow execution.
- **Telemetry Buffer** — Uses bounded-memory buffering with automatic retry.
- **LangSmith** — Stores complete AI workflow traces.
- **OpenTelemetry** — Emits distributed traces compatible with any OTLP backend.
- **Structured Logging** — All operational events are emitted as JSON.
- **Execution History** — Stores searchable workflow execution metadata.
- **Operational Guardrails** — Evaluate latency, cost, token budgets, prompt versions, and model versions without modifying workflow behavior.

---

# Public Interface

Only one public service is exposed by this module.

```python
PlatformOperationsService
```

All tracers, registries, collectors, repositories, loggers, telemetry providers, and guardrail engines are internal implementation details and must not be accessed directly by other modules.