# Implementation Plan: Platform & Operations Module

**Branch**: `013-platform-operations` | **Date**: 2026-07-19 | **Spec**: `specs/013-platform-operations/spec.md`
**Input**: Feature specification from `specs/013-platform-operations/spec.md`

**Note**: This template is filled in by the `/sp.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Primary requirement: Provide production observability, telemetry, governance, and operational monitoring for AI workflows without participating in workflow execution or content generation. The module is a pure observer — it consumes execution events emitted by other modules and exposes operational telemetry through public interfaces.

Technical approach: Implement a `PlatformOperationsService` using LangSmith for AI workflow tracing, OpenTelemetry for distributed tracing, structured JSON logging, prompt/model version registries, token/cost tracking, operational metrics collection, execution history recording, operational guardrails, and resilient telemetry buffering.

## Technical Context

**Language/Version**: Python 3.13+  
**Primary Dependencies**: langsmith>=0.1.0, opentelemetry-api>=1.20.0, opentelemetry-sdk>=1.20.0, opentelemetry-exporter-otlp-proto-http>=1.20.0, pydantic>=2.0.0, supabase>=2.0.0  
**Storage**: Supabase PostgreSQL (execution_history table),In-memory telemetry retry buffer, Supabase PostgreSQL (execution_history), 
**Testing**: pytest, pytest-asyncio, pytest-mock  
**Target Platform**: Linux server  
**Project Type**: backend module (library-style, single package)
**Performance Goals**: Observability overhead <500ms per workflow; execution history queries <500ms for 10k records; offline export <60s for 10k executions  
**Constraints**: <200ms p95 history query; bounded-memory telemetry buffer (<100MB) during 10min backend outage; never block workflow execution; never modify workflow state  
**Scale/Scope**: Production observability for multi-step AI workflows in Campaign Management system; support concurrent workflow telemetry; handle 10-minute backend outages with data retention

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with `.specify/memory/constitution.md`:

- [x] **Test-First**: Tests written before implementation? (Principle I) — Tests will be written for trace creation, span generation, log formatting, version tracking, cost calculation, guardrail evaluation, and metrics aggregation per the testing strategy.
- [x] **Clean Code**: Type hints, dataclasses, docstrings, no print statements? (Principle II) — All public functions will have type hints, Google-style docstrings, explicit return types. Models use @dataclass. Logging replaces print.
- [x] **Module-First Architecture**: Feature belongs to exactly one module? (Principle III) — Operations is a dedicated module owning observability, tracing, history, metrics, cost tracking, and monitoring. It communicates only through PlatformOperationsService public interface.
- [x] **Separation of Responsibilities**: Single responsibility per module? (Principle IV) — Operations owns ONLY observability. It never executes workflows, generates AI content, or manages campaigns. Module ownership matches constitution: Operations = Observability, Tracing, History, Metrics, Cost tracking, Monitoring.
- [x] **Workflow-Driven Execution**: LangGraph for orchestration? (Principle V) — Operations does NOT use LangGraph. It observes execution events emitted by Workflow Engine (which does use LangGraph). This satisfies "business modules MUST remain executable without LangGraph" because Operations is a passive observer.
- [x] **Reliability & Recovery**: Fail gracefully? (Principle VI) — Telemetry buffering ensures workflow execution continues when backend services are unavailable. Bounded-memory queue with drop-oldest policy prevents OOM. Guardrail evaluation failure does not block workflow.
- [x] **Observability Standards**: Every workflow produces traceable metadata? — All 9 user stories enforce this.
- [x] **Stack**: Uses approved tech stack? — Python 3.13+, pydantic, FastAPI, Supabase. LangSmith and OpenTelemetry are new additions required by the feature but do not conflict with any existing stack constraint.
- [x] **Quality Gates**: Tests pass, coverage ≥80%, module boundaries preserved? — All verified in spec success criteria.

**Result**: GATE PASSED. No violations or unjustified complexity.

**Post-Phase 1 Re-evaluation** (2026-07-19):
- [x] **Test-First**: Testing strategy covers unit, integration, edge case, and performance tests. All mapped to spec user stories.
- [x] **Module-First Architecture**: Operations is a new module at `backend/src/modules/operations/`. It communicates only through `PlatformOperationsService` ABC. It does not import from `campaign_management`, `ai_generation`, or `workflow_engine` internals.
- [x] **Separation of Responsibilities**: Operations never executes workflows, generates AI, or manages campaigns. It is a pure observer consuming emitted events.
- [x] **Workflow-Driven Execution**: No LangGraph dependency. Operations is stateless and independently testable.
- [x] **Observability Standards**: All 10 models and 11 functional requirements enforce capture of execution status, latency, token usage, cost, errors, and checkpoints.
- [x] **Quality Gates**: All 7 quality gates satisfied.

### PlatformOperationsService depends on:
- LangSmithAdapter
- OpenTelemetryAdapter
- JSONLogger
- MetricsCollector
- CostTracker
- GuardrailEngine
- ExecutionHistoryRepository

**Constitutional compliance confirmed. No amendments needed.**

## Project Structure

### Documentation (this feature)

```text
specs/013-platform-operations/
├── plan.md              # This file (/sp.plan command output)
├── research.md          # Phase 0 output (/sp.plan command)
├── data-model.md        # Phase 1 output (/sp.plan command)
├── quickstart.md        # Phase 1 output (/sp.plan command)
├── contracts/           # Phase 1 output (/sp.plan command)
└── tasks.md             # Phase 2 output (/sp.tasks command - NOT created by /sp.plan)
```

### Source Code (repository root)

```text
backend/src/modules/operations/
├── __init__.py                  # Exports PlatformOperationsService
├── constants.py                 # Enums: TelemetryEventType, GuardrailRule, MetricName
├── errors.py                    # Custom exceptions
├── interfaces/
│   └── operations.py            # PlatformOperationsService (ABC)
├── models/
│   ├── execution_trace.py       # ExecutionTrace, TraceSpan
│   ├── ai_telemetry.py          # AITelemetryRecord
│   ├── guardrail_evaluation.py  # GuardrailEvaluation, GuardrailRule
│   ├── operational_metrics.py   # OperationalMetrics, MetricPoint
|   ├── telemetry_event.py
│   └── execution_history.py     # ExecutionHistoryRecord
├── services/
│   ├── langsmith_adapter.py     # LangSmithTraceService
│   ├── otel_adapter.py           # OpenTelemetryTraceService
│   ├── json_logger.py           # StructuredJSONLogService
│   ├── prompt_registry.py       # PromptVersionRegistry
│   ├── model_registry.py        # ModelVersionRegistry
│   ├── cost_tracker.py          # TokenCostTracker
│   ├── metrics_collector.py     # OperationalMetricsCollector
|   ├── metrics_reporter.py  
│   ├── execution_history_repository.py     # ExecutionHistoryRecorder
│   ├── OperationalGuardrailEngine     #     GuardrailEvaluationEngine
│   ├── telemetry_buffer.py      # TelemetryBuffer
│   └── platform_operations.py   # PlatformOperationsService (impl)
├──repositories/
|    └──execution_history_repository.py
└── __init__.py

backend/tests/unit/operations/
├── test_langsmith_tracer.py
├── test_otel_tracer.py
├── test_json_logger.py
├── test_prompt_registry.py
├── test_model_registry.py
├── test_cost_tracker.py
├── test_guardrail_engine.py
├── test_metrics_collector.py
└── test_telemetry_buffer.py

backend/tests/integration/test_operations_pipeline.py
```

**Structure Decision**: Follows the existing module pattern (`backend/src/modules/<name>/` with interfaces/, models/, services/ sub-directories). Tests mirror the existing structure under `backend/tests/unit/` and `backend/tests/integration/`.

### Public Interface

The module exposes only the public `PlatformOperationsService` interface.

All tracing providers, telemetry collectors, registries, repositories, loggers, metrics collectors, and guardrail implementations are internal implementation details and MUST NOT be accessed directly by other modules.

Future observability providers (LangSmith, Phoenix, Weights & Biases, etc.) or monitoring backends can be integrated without changing extern

al module contracts.

## Complexity Tracking

> **No violations — complexity is justified by spec requirements.**

| Dependency | Why Needed | Simpler Alternative Rejected Because |
|------------|------------|-------------------------------------|
| LangSmith SDK | AI workflow tracing per FR-001 | Custom tracing lacks built-in AI observability, prompt inspection, and execution visualization |
| OpenTelemetry SDK + OTLP | Distributed tracing per FR-002 | In-process logging alone cannot correlate with infrastructure metrics |
| Multiple services (11) in module | Each maps to a unique FR (FR-001 through FR-011) | Monolithic service would violate single-responsibility and fail clean code review |
