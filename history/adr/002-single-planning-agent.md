# ADR-002: Single Planning Agent

**Status:** Accepted
**Date:** 2026-07-16

## Context

Original design: separate planners for Audience, Messaging, Hook, SEO, CTA, Platform, Promotion, Brand (8 planners). Problems:
- Tasks are interdependent (audience affects messaging, SEO affects hooks, etc.)
- Multiple LLM calls (latency, cost)
- Inconsistencies between planners (audience planner says X, messaging says Y)
- Hard to maintain coherent strategy

## Decision

**Single Planning Agent** produces a complete, structured campaign strategy in one call:

```json
{
  "audience": "...",
  "messaging": "...",
  "keywords": [...],
  "cta": "...",
  "platform_strategy": {...},
  "visual_direction": "...",
  "campaign_outline": [...]
}
```

All planning decisions emerge from one reasoning process.

## Consequences

**Positive:**
- Coherent, consistent strategy
- Single LLM call (cost, latency)
- Easier to prompt engineer (one prompt)
- Deterministic output structure

**Negative:**
- Larger prompt, more complex output schema
- Single point of failure (mitigated: validation after)
- Less modular (but planning is inherently holistic)

## Alternatives Considered

1. **Multiple planners with shared context**
   - Rejected: Still multiple calls; consistency not guaranteed

2. **Planner + refiners** (plan then refine each section)
   - Rejected: Adds latency; planning is atomic reasoning

3. **Human-in-the-loop planning**
   - Rejected: Defeats automation; planning is fast

## References

- Architecture Evolution Summary: "Planning Architecture"
- ADR-001: Workflow-Centric Architecture
- ADR-005: Structured JSON Communication (planning output format)
- Plan.md: Planning Agent specification