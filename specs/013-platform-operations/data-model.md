# Data Models: Platform & Operations Module

## Entity Overview

| Entity | Description | Persistence |
|--------|-------------|-------------|
| ExecutionTrace | Complete trace of a workflow execution (all spans) | LangSmith + In-memory |
| TraceSpan | Single span within an execution trace | LangSmith + In-memory |
| AITelemetryRecord | Single AI request with cost/token metadata | LangSmith + JSON log |
| OperationalMetricsSnapshot | Aggregated operational metrics | Computed (not persisted) |
| GuardrailEvaluation | Result of a guardrail rule check | Execution history + JSON log |
| ExecutionHistoryRecord | Searchable record of completed workflow | Supabase PostgreSQL |
| GuardrailRule | Definition of a guardrail rule | In-memory config |
| PromptVersion | Immutable prompt template version | In-memory registry |
| ModelVersion | Model metadata with cost/deprecation info | In-memory registry |
| MetricPoint | Single data point in a metric time series | In-memory |

---

## Entity Definitions

### ExecutionTrace

Represents a complete trace of a workflow execution, containing all spans, metadata, costs, and guardrail results.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID | Yes | Unique trace identifier |
| workflow_id | str | Yes | Workflow execution identifier |
| workflow_type | str | Yes | Type/category of workflow |
| total_duration_ms | int | Yes | Total execution duration |
| total_cost_usd | Decimal | Yes | Sum of all AI call costs |
| total_tokens | int | Yes | Sum of all token usage |
| status | ExecutionStatus | Yes | Overall execution status |
| error | str | No | Error message if failed |
| guardrail_results | List[GuardrailEvaluation] | No | Guardrail evaluation results |
| metadata | Dict[str, Any] | No | Additional metadata |
| created_at | datetime | Yes | Trace creation timestamp |

**State transitions**: Created → Populated → Finalized (status: completed/failed)

---

### TraceSpan

A single span within an execution trace.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| span_id | UUID | Yes | Unique span identifier |
| parent_span_id | UUID | No | Parent span ID (null for root) |
| name | str | Yes | Span name (e.g., "llm_call", "tool_call", "workflow_node") |
| span_type | SpanType | Yes | Category: chain, llm, tool, workflow |
| start_time | datetime | Yes | Span start time |
| end_time | datetime | No | Span end time (null if in progress) |
| duration_ms | int | No | Computed duration |
| input | Dict[str, Any] | Yes | Span input data |
| output | Dict[str, Any] | No | Span output data |
| metadata | Dict[str, Any] | No | Span-specific metadata |
| status | SpanStatus | Yes | Span status: pending, success, error |
| error | str | No | Error details if failed |

---

### AITelemetryRecord

Single AI request record with full cost and version tracking.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID | Yes | Unique record identifier |
| workflow_id | str | Yes | Parent workflow ID |
| trace_span_id | UUID | Yes | Corresponding trace span |
| prompt_version_id | UUID | Yes | Immutable prompt version ID |
| prompt_name | str | Yes | Human-readable prompt name |
| model_name | str | Yes | Model name (e.g., "gpt-4") |
| model_version | str | Yes | Model version string |
| provider | str | Yes | Provider name ("openai", "google") |
| input_tokens | int | Yes | Prompt token count |
| output_tokens | int | Yes | Generated token count |
| total_tokens | int | Yes | input_tokens + output_tokens |
| cost_per_input_token | Decimal | Yes | Cost per input token in USD |
| cost_per_output_token | Decimal | Yes | Cost per output token in USD |
| estimated_cost_usd | Decimal | Yes | Computed total cost |
| latency_ms | int | Yes | Request latency |
| status | str | Yes | success / error |
| error_message | str | No | Error details if failed |
| created_at | datetime | Yes | Record timestamp |
| prompt_version | int | Sequential prompt version

---

### OperationalMetricsSnapshot

Computed snapshot of operational metrics generated from recent execution history. This entity is not persisted and is produced on demand by the MetricsCollector.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| window_start | datetime | Yes | Start of aggregation window |
| window_end | datetime | Yes | End of aggregation window |
| total_workflows | int | Yes | Workflows completed in window |
| latency_p50_ms | float | Yes | Median latency |
| latency_p95_ms | float | Yes | 95th percentile latency |
| latency_p99_ms | float | Yes | 99th percentile latency |
| throughput | float | Yes | Workflows per minute |
| failure_count | int | Yes | Failed workflow count |
| failure_rate | float | Yes | failure_count / total_workflows |
| total_retries | int | Yes | Sum of all retries |
| total_cost_usd | Decimal | Yes | Sum of all costs |
| total_tokens | int | Yes | Sum of all tokens |

---

### GuardrailEvaluation

Result of a single guardrail rule check.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID | Yes | Unique evaluation identifier |
| workflow_id | str | Yes | Evaluated workflow |
| rule_name | str | Yes | Guardrail rule name |
| rule_severity | GuardrailSeverity | Yes | Severity: INFO, WARNING, CRITICAL |
| passed | bool | Yes | true = compliant, false = violation |
| actual_value | float | Yes | Observed value |
| threshold_value | float | Yes | Rule threshold |
| violation_message | str | No | Human-readable violation description |
| evaluated_at | datetime | Yes | Evaluation timestamp |

---

### ExecutionHistoryRecord

Searchable record of a completed workflow execution.

| Field | Type | Required | Description | Indexed |
|-------|------|----------|-------------|---------|
| id | UUID | Yes | Unique record ID | PK |
| workflow_id | str | Yes | Workflow execution ID | Yes |
| workflow_type | str | Yes | Type of workflow | No |
| status | ExecutionStatus | Yes | Final status | Yes |
| start_time | datetime | Yes | Execution start | Yes |
| end_time | datetime | Yes | Execution end | No |
| duration_ms | int | Yes | Total duration | No |
| total_cost_usd | Decimal | Yes | Total cost | No |
| total_tokens | int | Yes | Total tokens | No |
| tags | List[str] | No | User-defined tags | GIN |
| metadata | Dict[str, Any] | No | Flexible metadata | No |
| trace_id | UUID | No | LangSmith trace reference | No |
| guardrail_summary | Dict[str, Any] | No | Aggregated guardrail results | No |
| created_at | datetime | Yes | Record creation time | No |

---

### GuardrailRule

Definition of a single guardrail rule.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | str | Yes | Unique rule name |
| description | str | Yes | Human-readable description |
| metric | str | Yes | Metric to evaluate (cost_usd, latency_ms, total_tokens, model_version) |
| operator | ComparisonOp | Yes | gt, gte, lt, lte, eq, in |
| threshold | float | Yes | Threshold value |
| severity | GuardrailSeverity | Yes | Severity level |
| enabled | bool | Yes | Whether rule is active |

---

### PromptVersion

Immutable prompt template version.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| version_id | UUID | Yes | Immutable identifier |
| name | str | Yes | Human-readable prompt name |
| template | str | Yes | Prompt template content |
| template_hash | str | Yes | SHA256 hash of template |
| created_at | datetime | Yes | Registration timestamp |
| is_active | bool | Yes | Whether this version is active for new traces |
|version | int | Yes | Sequential version number

---

### ModelVersion

Model metadata with cost and deprecation information.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| model_name | str | Yes | Model identifier (e.g., "gpt-4") |
| model_version | str | Yes | Model version string |
| provider | str | Yes | "openai" / "google" / "anthropic" |
| cost_per_input_token | Decimal | Yes | USD per input token |
| cost_per_output_token | Decimal | Yes | USD per output token |
| is_deprecated | bool | Yes | Whether model is deprecated |
| deprecation_date | datetime | No | Expected deprecation date |
| supported_capabilities | List[str] | No | e.g., ["chat", "function_calling"] |

---

## Enums

### ExecutionStatus
```
PENDING, RUNNING, COMPLETED, FAILED, CANCELLED
```

### SpanType
```
WORKFLOW, CHAIN, LLM, TOOL, RETRY
```

### SpanStatus
```
PENDING, SUCCESS, ERROR
```

### GuardrailSeverity
```
INFO, WARNING, CRITICAL
```

### ComparisonOp
```
GT, GTE, LT, LTE, EQ, IN
```

### TelemetryEventType
```
WORKFLOW_START, WORKFLOW_COMPLETE, WORKFLOW_FAIL, WORKFLOW_RETRY,
AI_REQUEST_START, AI_REQUEST_COMPLETE,
GUARDRAIL_EVALUATION, TELEMETRY_BUFFER_STATUS
```

---

## Relationships

```
ExecutionTrace 1──* TraceSpan
ExecutionTrace 1──* AITelemetryRecord
ExecutionTrace 1──* GuardrailEvaluation
ExecutionTrace 1──1 ExecutionHistoryRecord
WorkflowExecution 1──1 ExecutionTrace
WorkflowExecution 1──* AITelemetryRecord (via multiple AI calls)
```

## Validation Rules

| Entity | Field | Rule |
|--------|-------|------|
| AITelemetryRecord | input_tokens | >= 0 |
| AITelemetryRecord | output_tokens | >= 0 |
| AITelemetryRecord | estimated_cost_usd | >= 0 |
| AITelemetryRecord | total_tokens | = input_tokens + output_tokens |
| ExecutionHistoryRecord | duration_ms | >= 0 |
| OperationalMetricsSnapshot | failure_rate | 0.0 to 1.0 |
| OperationalMetricsSnapshot | total_workflows | > 0 when metrics computed |
| GuardrailEvaluation | actual_value | float, may be any value |
| PromptVersion | template_hash | SHA256 hex string (64 chars) |
| TelemetryBuffer | maxsize | > 0, suggested 10000 |
