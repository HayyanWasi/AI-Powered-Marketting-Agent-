# ADR-011: Built-In Observability (Operations Module)

**Status:** Accepted
**Date:** 2026-07-16

## Context

Observability was an afterthought in early designs. Problems discovered late:
- No visibility into workflow execution
- No cost tracking per campaign
- No prompt/model version correlation with quality
- Debugging required adding logs post-hoc

## Decision

**Observability is a first-class module (Operations), not an afterthought.** It is built into the workflow from day one.

**Operations module tracks:**

| Category | Metrics |
|----------|---------|
| **Workflow** | Execution count, duration, success/failure rate, node durations |
| **Node-level** | Per-node latency, token usage, cost, error rate, retry count |
| **AI-specific** | Prompt version, model version, temperature, tokens in/out, cost per call |
| **Business** | Campaigns created, edited, published, cost per campaign |
| **Quality** | Validation pass/fail rates, human approval rates, regeneration frequency |

**Implementation:**
- Structured logging (JSON) with correlation IDs (campaign_id, execution_id)
- OpenTelemetry traces spanning workflow nodes
- Metrics exported to Prometheus / Datadog
- Cost calculated per node using token counts × model pricing
- Prompt/model version embedded in every AI call context

**Guardrails integrated:**
- Token budget per campaign
- Cost alerts
- Latency SLOs
- Error rate thresholds

## Consequences

**Positive:**
- Production-ready from start
- Data-driven optimization (prompt tuning, model selection)
- Cost control and forecasting
- Fast incident response
- Audit trail for AI decisions

**Negative:**
- Additional infrastructure (metrics pipeline)
- Instrumentation overhead (minimal with OpenTelemetry)
- PII in traces (sanitize prompt inputs)

## Alternatives Considered

1. **Add logging later**
   - Rejected: "Later" never comes; retrofitting is expensive

2. **Vendor APM only (DataDog, New Relic)**
   - Rejected: Vendor lock-in; AI-specific metrics need custom instrumentation

3. **Minimal logging, debug on demand**
   - Rejected: Insufficient for AI system debugging

## References

- Architecture Evolution Summary: "Observability"
- ADR-010: Execution History (feeds Operations)
- ADR-006: LangGraph (provides node-level hooks)
- Plan.md: Observability section