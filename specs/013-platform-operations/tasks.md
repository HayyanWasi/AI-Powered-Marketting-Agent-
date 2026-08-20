---

description: "Task breakdown for Platform & Operations Module implementation"

---

# Tasks: Platform & Operations Module

**Input**: Design documents from `specs/013-platform-operations/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Module skeleton, models, constants, and configuration

- [X] T001 [P] Create module structure at `backend/src/modules/operations/` with subdirectories: `interfaces/`, `models/`, `services/`, `repositories/`
- [X] T002 [P] Define enums in `backend/src/modules/operations/constants.py`: `ExecutionStatus`, `SpanType`, `SpanStatus`, `GuardrailSeverity`, `ComparisonOp`, `TelemetryEventType`
- [X] T003 [P] Define custom exceptions in `backend/src/modules/operations/errors.py`: `OperationsError`, `TelemetryBackendError`, `GuardrailEvaluationError`, `BufferOverflowError`
- [X] T004 [P] Define all data models in `backend/src/modules/operations/models/`: `execution_trace.py`, `ai_telemetry.py`, `guardrail_evaluation.py`, `operational_metrics.py`, `execution_history.py`, `telemetry_event.py`
- [X] T005 Define `PlatformOperationsService` ABC in `backend/src/modules/operations/interfaces/operations.py` with methods:` record_execution_start`,
,`record_execution_complete`
,`record_ai_request`
,`get_execution_history`
,`get_metrics`
,`register_prompt_version`
,`get_prompt_version`
,`get_model_info`
,`export_executions`
- [X] T006 [P] Add new dependencies to `pyproject.toml`: `langsmith>=0.1.0`, `opentelemetry-api>=1.20.0`, `opentelemetry-sdk>=1.20.0`, `opentelemetry-exporter-otlp-proto-http>=1.20.0`

**Checkpoint**: Module skeleton ready — models, interfaces, and enums defined. Blocking other phases removed.

---

## Phase 2: Foundational — Registries & Primitive Services

**Purpose**: Core services that underpin multiple user stories

- [X] T007 [P] [US4] Implement `PromptVersionRegistry` in `backend/src/modules/operations/services/prompt_registry.py` — register immutable prompt versions with SHA256 hash, lookup by UUID, activate/deactivate version
- [X] T008 [P] [US4] Implement `ModelVersionRegistry` in `backend/src/modules/operations/services/model_registry.py` — register models with name, version, provider, cost per token, deprecation status
- [X] T009 [P] [US3] Implement `JSONLogger` in `backend/src/modules/operations/services/json_logger.py` — custom logging.Formatter emitting JSON with timestamp, level, logger, message, workflow_id, event_type, duration_ms, metadata
- [X] T010 [P] [US9] Implement `TelemetryBuffer` in `backend/src/modules/operations/services/telemetry_buffer.py` — bounded queue (maxsize=10000, drop-oldest), async flush with exponential backoff, separate buffer instances per telemetry type

**Checkpoint**: Registries, logger, and buffer ready — US4, US3, US9 primitives available.

---

## Phase 3: User Story 1 — Complete Workflow Traceability (Priority: P1)

**Goal**: Every workflow execution produces a complete LangSmith trace with all spans linked by parent-child relationships.

**Independent Test**: Execute any workflow and verify a complete LangSmith trace appears with all spans (workflow nodes, AI calls, tool calls, retries).

### Implementation

- [X] T011 [US1] Implement `LangSmithAdapter` in `backend/src/modules/operations/services/langsmith_adapter.py` — wraps `langsmith.Client`, uses `RunTree` API for manual trace construction, creates parent/child spans for workflow nodes, LLM calls, tool invocations
- [X] T012 [US1] Implement error capture in LangSmith spans — on workflow failure, end spans with error details and stack trace
- [X] T013 [US1] Implement LangSmith metadata injection — attach prompt_version, model_name, model_version, input_tokens, output_tokens, total_tokens, estimated_cost_usd, and workflow_id to every AI span.

**Checkpoint**: US1 complete — all workflow executions produce complete LangSmith traces with error capture.

---

## Phase 4: User Story 2 — Cross-Workflow OpenTelemetry Spans (Priority: P1)

**Goal**: OpenTelemetry spans emitted across all workflow and AI execution layers, correlated with traces and metrics.

**Independent Test**: Run a workflow and verify OTel spans appear in the configured OTLP exporter with correct attributes.

### Implementation

- [X] T014 [P] [US2] Configure `TracerProvider` with `Resource` (service.name, service.version, environment) in `backend/src/modules/operations/services/otel_adapter.py`
- [X] T015 [P] [US2] Configure `BatchSpanProcessor` with OTLP HTTP exporter — endpoint, headers, timeout, max_queue_size, max_export_batch_size
- [X] T016 [US2] Emit workflow spans with semantic conventions: `workflow.id`, `workflow.type`, `workflow.status`
- [X] T017 [US2] Emit LLM spans with semantic conventions: `llm.model`, `prompt.version`, `gen_ai.request.max_tokens`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`
- [X] T018 [US2] Emit tool spans with semantic conventions: `tool.name`, `tool.input`, `tool.output`

**Checkpoint**: US2 complete — OTel spans emitted for all execution layers with correct attributes.

---

## Phase 5: User Story 3 — Structured JSON Operational Logging (Priority: P1)

**Goal**: All operational events emitted as structured JSON logs for automated querying and alerting.

**Independent Test**: Trigger operational events and verify JSON logs appear in the log aggregator with required fields.

### Implementation

- [X] T019 [US3] Implement operational event logging in `JSONLogger` — workflow start/complete/fail/retry events emit structured JSON with timestamp, workflow_id, event_type, duration_ms, metadata
- [X] T020 [US3] Implement AI request logging — each AI generation request logs prompt_version, model_version, token_usage, execution_cost_usd, latency_ms
- [X] T021 [US3] Implement guardrail evaluation logging — each guardrail check logs rule_name, passed, actual_value, threshold, severity
- [X] T022 [US3] Implement telemetry buffer logging — buffer status events (enqueue, flush, drop, retry) logged with buffer fill percentage

**Checkpoint**: US3 complete — all operational events produce structured JSON logs.

---

## Phase 6: User Story 4 — AI Request Cost & Token Tracking (Priority: P1)

**Goal**: Every AI request records prompt version, model version, token usage, and execution cost.

**Independent Test**: Make AI generation calls and verify cost/token metadata is recorded in both LangSmith and structured logs.

### Implementation

- [X] T023 [P] [US4] Implement `CostTracker` in `backend/src/modules/operations/services/cost_tracker.py` — computes estimated_cost_usd from input_tokens, output_tokens, cost_per_input_token, cost_per_output_token
- [X] T024 [US4] Implement per-workflow cost aggregation — sum all AI call costs within a workflow execution, record in execution trace and history
- [X] T025 [US4] Integrate `CostTracker` with `LangSmithAdapter` — attach token_usage and estimated_cost_usd to LLM spans
- [X] T026 [US4] Integrate `CostTracker` with `JSONLogger` — include cost fields in AI request log entries

**Checkpoint**: US4 complete — every AI request records complete usage and cost metadata in both LangSmith and logs.

---

## Phase 7: User Story 5 — Workflow Operational Metrics Collection (Priority: P1)

**Goal**: Workflow latency, retry count, throughput, and failure rate metrics collected for system health monitoring.

**Independent Test**: Run workflows under load and verify metrics are emitted.

### Implementation

- [X] T027 [US5] Implement `MetricsCollector` in `backend/src/modules/operations/services/metrics_collector.py` — sliding window aggregation of p50/p95/p99 latency, throughput (workflows/min), failure_rate, retry_count, token usage, total cost
- [X] T028 [US5] Implement MetricsReporter in
backend/src/modules/operations/services/metrics_reporter.py
— expose metrics through PlatformOperationsService.get_metrics()
and publish them to the configured OpenTelemetry metrics exporter.
- [X] T029 [US5] Implement histogram computation — sorted list for n < 1000, switch to t-digest for n >= 1000 percentile calculations

**Checkpoint**: US5 complete — latency percentiles, throughput, and error rates available via public interface.

---

## Phase 8: User Story 6 — Searchable Execution History (Priority: P2)

**Goal**: Searchable execution history for completed workflows with query by workflow_id, status, time range, tags.

**Independent Test**: Execute workflows, then query execution history store by workflow_id, time range, status, or tags.

### Implementation

- [X] T030 [P] [US6] Create Supabase migration for `execution_history` table — columns: id UUID PK, workflow_id text, workflow_type text, status text, start_time timestamptz, end_time timestamptz, duration_ms int, total_cost_usd numeric, total_tokens int, tags text[], metadata jsonb, trace_id uuid, guardrail_summary jsonb, created_at timestamptz, retry_count int
- [X] T031 [P] [US6] Add database indexes — btree on (workflow_id, status, start_time), GIN on tags
- [X] T032 [US6] Implement `ExecutionHistoryRepository` in `backend/src/modules/operations/repositories/execution_history_repository.py` — insert, query by filters (workflow_id, status, time_range, tags), pagination (limit/offset), count for total results
- [X] T033 [US6] Implement `ExecutionHistoryService` in `backend/src/modules/operations/services/execution_history_service.py` — record completed workflow executions, retrieve through repository with filtering and pagination

**Checkpoint**: US6 complete — execution history is searchable with <500ms query time for 10k records.

---

## Phase 9: User Story 7 + User Story 8 — Guardrails & Export (Priority: P2)

**Goal 1**: Operational guardrails evaluate execution events without blocking workflow execution.
**Goal 2**: Export historical workflow executions for offline evaluation.

**Independent Test 1**: Execute workflows violating guardrails — verify violation events recorded without blocking execution.
**Independent Test 2**: Export execution history and verify it contains all data needed for offline evaluation.

### Implementation

- [X] T034 [P] [US7] Predefined rules:

• Workflow cost exceeds configured budget
• Workflow latency exceeds configured SLO
• Total tokens exceed configured budget
• Deprecated model version detected
• Deprecated prompt version detected
- [X] T035 [US7] Implement guardrail violation recording — attach `GuardrailEvaluation` list to execution trace, emit via JSON logger, store summary in execution_history
- [X] T036 [US7] Implement guardrail rule configuration — load rules from config/env, enable/disable rules at runtime
- [X] T037 [US8] Implement `ExecutionExportService` in `backend/src/modules/operations/services/export_service.py` — query execution_history by date range, convert to JSONL, upload to Supabase Storage, return download URL

**Checkpoint**: US7 + US8 complete — guardrails evaluate without blocking, export produces usable datasets.

---

## Phase 10: User Story 9 — Observability Resilience (Priority: P1)

**Goal**: Workflow execution continues uninterrupted when LangSmith, OTel collector, or log aggregator are temporarily unavailable.

**Independent Test**: Disable observability backends and verify workflows complete successfully with local buffering.

### Implementation

- [X] T038 [US9] Integrate `TelemetryBuffer` with `LangSmithAdapter` — buffer trace post calls when LangSmith API is unavailable, retry with exponential backoff (1s, 2s, 4s, max 30s)
- [X] T039 [US9] Integrate `TelemetryBuffer` with `OTelAdapter` — buffer span export calls when OTLP collector is down, retry with backoff
- [X] T040 [US9] Integrate `TelemetryBuffer` with `JSONLogger` — buffer log entries when log aggregator is unavailable (e.g., network filesystem), retry on reconnect
- [X] T041 [US9] Implement buffer monitoring — track fill percentage, drop count, oldest_buffer_age, retry count as operational metrics; emit WARNING log when buffer > 80% full

**Checkpoint**: US9 complete — workflows complete successfully during backend outages with bounded-memory buffering.

---

## Phase 11: Integration — PlatformOperationsService

**Purpose**: Wire all services together behind the public interface.

- [X] T042 Implement `PlatformOperationsService` in `backend/src/modules/operations/services/platform_operations.py` — composes all internal services, implements the ABC from `interfaces/operations.py`
- [X] T043 Implement record_execution_start —
create LangSmith root run,
start OpenTelemetry root span,
emit workflow start log,
initialize execution context.
Do not persist execution history until workflow completion.
Persist history only after completion.
- [X] T044 Implement `record_execution_complete` — finalizes LangSmith trace, closes OTel span, runs guardrails, updates metrics, finalizes execution history, emits JSON log
- [X] T045 Implement record_ai_request —
create LangSmith child span,
emit OpenTelemetry LLM span,
track token usage and cost,
update workflow token/cost aggregates,
emit structured JSON log. — creates child LangSmith span, emits OTel LLM span, tracks cost/tokens, emits JSON log
- [X] T046 Wire telemetry buffering into all external calls — LangSmith post, OTel export, log emission all go through buffer
- [X] T047 Export public interface via `backend/src/modules/operations/__init__.py`

**Checkpoint**: All platform operations accessible through a single public `PlatformOperationsService`.

---

## Phase 12: Tests

**Purpose**: Verify correctness, resilience, and performance.

- [X] T048 [P] Write unit tests for `LangSmithAdapter` — trace creation (T011), span hierarchy (T012), metadata injection (T013), error capture (T012)
- [X] T049 [P] Write unit tests for `OTelAdapter` — span creation (T016, T017, T018), exporter configuration (T015), resource attributes (T014)
- [X] T050 [P] Write unit tests for `JSONLogger` — event log format (T019, T020, T021, T022), required field validation
- [X] T051 [P] Write unit tests for `PromptVersionRegistry` — registration (T007), lookup, hash computation, duplicate detection
- [X] T052 [P] Write unit tests for `ModelVersionRegistry` — registration (T008), lookup, cost per token, deprecation query
- [X] T053 [P] Write unit tests for `CostTracker` — cost calculation (T023), workflow aggregation (T024), edge cases (zero tokens, missing model)
- [X] T054 [P] Write unit tests for `MetricsCollector` — latency percentiles (T027), throughput calculation, failure rate, sliding window behavior
- [X] T055 [P] Write unit tests for `GuardrailEngine` — rule evaluation (T034), violation recording (T035), rule configuration (T036), evaluation failure handling
- [X] T056 [P] Write unit tests for `TelemetryBuffer` — enqueue/dequeue (T010), drop-oldest policy, backoff retry, concurrent access, buffer full behavior
- [X] T057 [P] Write unit tests for `ExecutionHistoryRepository` — insert/query (T032), filter combinations (T033), pagination, empty results
- [X] T058 Write integration tests in `backend/tests/integration/test_operations_pipeline.py` — e2e telemetry pipeline (T042–T046), LangSmith trace verification, OTel exporter integration, execution history recording, buffering during backend outage
T058A
Write unit tests for ExecutionExportService
- JSONL generation
- Supabase upload
- empty export
- invalid date range
- [X] T059 Write edge case tests — LangSmith unavailable, OTLP collector unavailable, log aggregator unavailable, buffer overflow, guardrail evaluation failure, concurrent workflow telemetry
- [X] T060 Write performance tests — verify observability overhead <50ms per workflow, bounded-memory buffering during 10min simulated outage, support concurrent workflow telemetry

**Checkpoint**: All tests pass with >=80% code coverage on operations module.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS US3, US4, US9
- **User Stories (Phases 3–10)**: All depend on Phase 1 complete
  - Phase 3 (US1): Depends on Phase 2 T010 (telemetry buffer) for resilience
  - Phase 4 (US2): Depends on Phase 2 T010 (telemetry buffer) for resilience
  - Phase 5 (US3): Depends on Phase 2 T009 (JSONLogger). Can run parallel with Phases 3, 4
  - Phase 6 (US4): Depends on Phase 2 T007, T008 (registries). Can run parallel with Phases 3, 4, 5
  - Phase 7 (US5): Depends on Phase 2. Can run parallel with Phases 3–6
  - Phase 8 (US6): Depends on Phase 1 only. Can run parallel with Phases 3–7
  - Phase 9 (US7+US8): Depends on Phase 2 T007, T008 (registries) for model/prompt version checks
  - Phase 10 (US9): Depends on Phase 2 T010 (telemetry buffer). Integrates with Phases 3–5
- **Integration (Phase 11)**: Depends on all US phases (3–10)
- **Tests (Phase 12)**: Can start after Phase 1 for unit test scaffolding; full test suite depends on Phase 11

### Within Each Phase

- [P] tasks can run in parallel (different files, no dependencies)
- Non-[P] tasks within a phase must run sequentially
- Implementation tasks before their corresponding test tasks

### Parallel Opportunities

| Task IDs | Can Run With | Rationale |
|----------|-------------|-----------|
| T001–T006 | All in Phase 1 | Different files, no internal dependencies |
| T007–T010 | All in Phase 2 | Independent registries, logger, buffer |
| Phases 3–6 | Can run in parallel | Independent user stories |
| Phases 7–10 | Can run in parallel | Independent user stories |

---

## Implementation Strategy

### MVP Scope: All P1 User Stories

Core observability must work before P2 stories:
1. Phase 1 → Phase 2 → Phase 3 (US1 LangSmith) → Phase 4 (US2 OTel) → Phase 5 (US3 Logging) → Phase 6 (US4 Cost) → Phase 7 (US5 Metrics) → Phase 10 (US9 Resilience) → Phase 11 (Integration)

### Incremental Delivery

1. Complete Phase 1 (Setup) → Foundation ready
2. Complete Phase 2 (Foundational) → Registries, logger, buffer ready
3. Add US1 + US2 + US3 + US4 + US5 + US9 (All P1) → Full observability
4. Add Phase 11 (Integration) → Single public interface
5. Add Phase 8 (US6 History P2) → Searchable history
6. Add Phase 9 (US7 Guardrails + US8 Export P2) → Governance
7. Add Phase 12 (Tests) → Final verification

### Parallel Team Strategy

With multiple developers after Phase 1 complete:
- Developer A: US1 (LangSmith) + US4 (Cost tracking)
- Developer B: US2 (OTel) + US5 (Metrics)
- Developer C: US3 (Logging) + US9 (Buffer integration)
- Developer D: US6 (History) + US7+US8 (Guardrails + Export)

---

## Notes

- [P] tasks = different files, no dependencies
- [US*] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Implement test cases alongside each implementation task following the project's test-first workflow.
- Commit after each logical task group
- Verify constitution compliance at each phase checkpoint
