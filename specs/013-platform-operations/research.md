# Research: Platform & Operations Module

## Technology Decisions

### LangSmith SDK for AI Workflow Tracing

**Decision**: LangSmith is the primary AI observability platform.
OpenTelemetry complements it by providing infrastructure-wide distributed tracing.

**Rationale**: LangSmith provides built-in AI workflow observability, prompt inspection, execution visualization, and run tree hierarchy. The `RunTree` API allows precise parent-child span relationships across workflow nodes, LLM calls, and tool invocations. The `Client.create_run` API supports structured metadata (prompt_version, model_version, token_usage, cost_usd).

**Alternatives considered**:
- Custom tracing: Would require building trace storage, UI, and visualization from scratch. No prompt inspection capability.
- LangChain callback integration: Ties tracing to LangChain, but project uses LangGraph (different abstraction level). `RunTree` is more flexible.

**Implementation pattern**:
- Wrap LangSmith `Client` as a service dependency
- Use `RunTree` per workflow execution with child runs per node
- Attach metadata (prompt_version, model_version, cost) to each run
- Buffered posting with error handling; batch posting via `client.create_run` for resilience

---

### OpenTelemetry for Distributed Tracing

**Decision**: Use `opentelemetry-api>=1.20.0`, `opentelemetry-sdk>=1.20.0`, and `opentelemetry-exporter-otlp-proto-http>=1.20.0` with `BatchSpanProcessor` and OTLP HTTP exporter.

**Rationale**: OpenTelemetry is the industry standard for distributed tracing. Using `TracerProvider` with `Resource` (service.name, service.version, environment) and `BatchSpanProcessor` enables configurable export batching. OTLP HTTP exporter integrates with any OTel-compatible backend (Jaeger, Grafana Tempo, SigNoz, etc.).

**Alternatives considered**:
- Prometheus client: Metrics-only, no trace correlation capability.
- Datadog APM: Vendor lock-in, not OTel standard.
- Custom span propagation: Would require building instrumentation SDK from scratch.

**Implementation pattern**:
- Singleton `TracerProvider` configured at module initialization
- Named tracer per subsystem: `operations.workflow`, `operations.llm`, `operations.tool`
- Standard semantic conventions for span attributes:
  - Workflow: `workflow.id`, `workflow.type`, `workflow.status`
  - LLM: `llm.model`, `llm.prompt.template`, `gen_ai.request.max_tokens`
  - Tool: `tool.name`, `tool.input`, `tool.output`
- `BatchSpanProcessor` with configurable max_queue_size, max_export_batch_size
- Retry
- Guardrail

---

### Structured JSON Logging

**Decision**: Use Python stdlib `logging` with a custom JSON `Formatter` that outputs JSON objects with standard fields: `timestamp`, `level`, `logger`, `message`, `workflow_id`, `event_type`, `duration_ms`, `metadata`, `trace_id`, `span_id`, `Python logging`.

**Rationale**: Structured JSON enables automated search, filtering, alerting, and dashboard creation in log aggregation systems (ELK, Loki, Datadog, etc.). No external dependency needed — Python's `logging` module with a custom `logging.Formatter` subclass implements this cleanly.

**Alternatives considered**:
- structlog: Feature-rich but adds external dependency for simple JSON formatting.
- python-json-logger: Lightweight but not needed when custom formatter is trivial.
- Plain text: Cannot be queried or parsed automatically.

**Implementation pattern**:
- `JSONFormatter(logging.Formatter)` subclass emitting `json.dumps` of log record dict
- `LogRecord` factory adding `workflow_id`, `event_type`, `duration_ms` fields via `extra` dict
- Logger hierarchy: `operations.workflow`, `operations.llm`, `operations.guardrails`, `operations.metrics`, `operations.buffer`

---

### Prompt Version Registry

**Decision**: Use immutable UUIDv4 identifiers for prompt versions. Registry stores: `prompt_version_id`, `prompt_name`, `version`, `template_content`, `template_hash`, `created_at`, `is_active`

**Rationale**: Immutable UUIDs uniquely identify prompt versions, while sequential version numbers provide human-readable versioning for debugging and auditing . SHA256 hash detects content drift. `is_active` flag enables canary testing of new prompt versions without breaking existing traces.

**Alternatives considered**:
- Semantic version strings (v1.0, v2.0): Ambiguous when same version is edited.
- Mutable names: Cannot guarantee a trace references the exact prompt content used.

**Implementation pattern**:
- Prompt versions are cached in-memory for fast lookup and persisted in Supabase for durability.  
- Registration: `register_prompt(name, template)` → returns UUID
- Lookup: `get_prompt(version_id)` → prompt content
- Hashing: `sha256(template_content.encode())` for integrity check

---

### Model Version Registry

**Decision**: Use registry tracking `model_name`, `model_version`, `provider`, `supported_capabilities`, `cost_per_input_token`, `cost_per_output_token`, `is_deprecated`, `deprecation_date`.

**Rationale**: Cost tracking and guardrail evaluation require authoritative model metadata. The `cost_per_*_token` fields enable real-time cost estimation. `is_deprecated` feeds into guardrails (User Story 7).

**Alternatives considered**:
- Hardcoded model map: Cannot update without code deployment.
- External API query: Latency penalty for every LLM call.

**Implementation pattern**:
- Initialized with supported models during startup and persisted in Supabase. The in-memory cache is refreshed whenever model metadata changes.
- `get_model(model_name, model_version)` → model metadata
- `is_deprecated(model_name, model_version)` → bool for guardrails
- `estimate_cost(model_name, input_tokens, output_tokens)` → USD cost

---

### Token and Cost Tracking

**Decision**: Capture per-AI-call: `input_tokens`, `output_tokens`, `total_tokens`, `estimated_cost_usd`. Aggregate per-workflow: sum of all AI call costs. Store in both LangSmith trace metadata and structured JSON log.

**Rationale**: Token tracking is foundational to cost optimization. Storing in both LangSmith and JSON logs ensures availability regardless of which tool the operator uses.

**Implementation pattern**:
- `TokenCostTracker` receives per-call token counts and model info
- Computes cost: `(input_tokens * cost_per_input) + (output_tokens * cost_per_output)`
- Emits: `AITelemetryRecord` with all fields
- Aggregates per workflow execution

---

### Operational Metrics Collector

**Decision**: Collect p50/p95/p99 latency, throughput (workflows/min), failure_rate, retry_count. Expose through `get_metrics()` on `PlatformOperationsService`.

**Rationale**: These are the standard RED (Rate, Errors, Duration) metrics for production systems. Percentile calculations need sufficient samples; windowed aggregation (1min rolling) provides freshness.

**Implementation pattern**:
- `MetricsCollector` maintains sliding window of execution events
- Compute latency percentiles from the configured rolling window.
- Throughput: count of completed workflows per minute
- Failure rate: failed / total per minute
- Exported to OTel metrics provider for dashboarding

---

### Execution History Recorder

**Decision**: Store execution records in Supabase PostgreSQL `execution_history` table. Queryable by `workflow_id`, `status`, `time_range`, `tags`. Supports pagination.

**Rationale**: Supabase is already the project's database. PostgreSQL enables rich querying and indexing. The spec requires <500ms query time for 10k records, which PostgreSQL can satisfy with proper indexing.

**Implementation pattern**:
- Table: `execution_history(id uuid PK, workflow_id text, status text, start_time timestamptz, end_time timestamptz, duration_ms int, total_cost_usd numeric, tags text[], metadata jsonb, trace_id text, created_at timestamptz)`
- Indexes: `workflow_id`, `status`, `start_time`, `tags` GIN index


---

### Operational Guardrails Engine

**Decision**: Rule-based guardrail evaluation engine. Rules defined as: `(metric, operator, threshold, severity)`. Evaluation runs asynchronously after workflow completion. Never blocks execution.

**Rationale**: The spec requires guardrails to execute without blocking workflow execution. Rule-based evaluation is deterministic, fast (<50ms), and auditable.

**Guardrail rules**:
1. `cost > max_budget_per_workflow` → `WARNING`
2. `model_version in deprecated_models` → `WARNING`
3. `latency > max_latency_slo` → `INFO`
4. `total_tokens > max_tokens_per_workflow` → `INFO`
5. `prompt_version not active` → `INFO`

**Implementation pattern**:
- `GuardrailEngine.evaluate(execution_context)` → `List[GuardrailEvaluation]`
- Each evaluation: `(rule_name, passed, actual_value, threshold, severity, timestamp)`
- Results recorded in execution history and JSON log
- Failures in guardrail evaluation itself → logged, workflow unaffected

---

### Telemetry Buffering

**Decision**: Bounded in-memory queue (`maxsize=10000`) with drop-oldest policy. Each buffer maintains independent retry state and exponential backoff timers.. Async flush with exponential backoff (1s, 2s, 4s, max 30s).

**Rationale**: Ensures workflow execution never blocks when backends are unavailable. Bounded memory prevents OOM. Drop-oldest is appropriate because recent telemetry is more valuable for debugging than old.

**Alternatives considered**:
- Disk-backed buffer: More durable but slower; spec requires <50ms overhead per workflow.
- Blocking send: Would violate non-blocking requirement.
- Unbounded queue: Risk OOM during extended outage.

**Implementation pattern**:
- `TelemetryBuffer(maxsize=10000, drop_policy="oldest")`
- `enqueue(item)` → returns `(success, dropped_count)`
- `flush()` → async batch send with retry
- Separate buffer instances for LangSmith, OTel, and log aggregator
- Monitor buffer fill percentage as an operational metric

---

## Dependency Summary

| Dependency | Version | Purpose | Config Source |
|-----------|---------|---------|--------------|
| langsmith | >=0.1.0 | AI workflow tracing | LANGSMITH_API_KEY, LANGSMITH_PROJECT env vars |
| opentelemetry-api | >=1.20.0 | OTel API for span creation | OTEL_EXPORTER_OTLP_ENDPOINT, OTEL_SERVICE_NAME |
| opentelemetry-sdk | >=1.20.0 | OTel SDK for span processing | Inherits from API env vars |
| opentelemetry-exporter-otlp-proto-http | >=1.20.0 | OTLP HTTP export | OTEL_EXPORTER_OTLP_ENDPOINT (default: http://localhost:4318) |
| supabase | >=2.0.0 | Execution history persistence | SUPABASE_URL, SUPABASE_SERVICE_KEY |
| pydantic | >=2.0.0 | Configuration models | Already in project |

### Future Enhancements

- AI quality evaluation integration
- Prompt A/B testing
- Real-time alerting
- Dashboard generation
- Automated anomaly detection