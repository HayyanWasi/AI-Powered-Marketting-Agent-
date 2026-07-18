# ADR-004: Dedicated Context Builder over Distributed Context Fetching

**Status:** Accepted
**Date:** 2026-07-16

## Context

In the agent-centric architecture, each AI agent independently fetched context:
- Brand data
- Audience profiles
- Platform rules
- Reference materials
- Previous campaigns

Problems:
- Duplicate database queries across agents
- Larger prompts (each agent includes full context)
- Inconsistent context between agents (different freshness, different subsets)
- Difficult to cache effectively
- Hard to test (each agent needs different mock data)

## Decision

Introduce a **Dedicated Context Builder** as a single workflow step that:
1. Collects all required context in one pass
2. Normalizes into a single structured context object
3. Passes that object to all downstream AI workers

**Context object structure:**
```json
{
  "brand": {...},
  "campaign": {...},
  "audience": {...},
  "platform": {...},
  "references": [...],
  "previous_campaigns": [...],
  "seo_research": {...}  // optional
}
```

## Consequences

**Positive:**
- Single data fetch → fewer DB queries, lower latency
- Consistent context across all AI workers
- Better caching (one cache entry for full context)
- Easier testing (one context builder to test/mock)
- Clear separation: data fetching (deterministic) vs. reasoning (AI)

**Negative:**
- Additional workflow step (but trivial latency)
- Context object can grow large (mitigated by optional fields)
- Upfront design of context schema required

## Alternatives Considered

1. **Distributed context fetching** (original)
   - Rejected: Duplicate queries, inconsistency, large prompts

2. **Shared context service** - Agents call a common context API
   - Rejected: Still distributed calls; Context Builder is simpler

3. **Lazy context loading** - Agents request only what they need
   - Rejected: Adds orchestration complexity; context is small enough to pre-fetch

## References

- Architecture Evolution Summary: "Context Handling"
- Plan.md: Dependency Sequence item 1 (Context Builder)
- Research.md: Research 1 (Required Company Information)