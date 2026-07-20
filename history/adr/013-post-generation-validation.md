# ADR-013: Validation Strategy — Post-Generation Only

**Status:** Accepted
**Date:** 2026-07-16

## Context

Original design: validate after every AI step (planning → validate → copy → validate → image prompt → validate). Problems:
- Added latency (validation LLM calls between each step)
- Reduced automation (human review gates between steps)
- Validation of intermediate outputs often redundant (final output validates whole)

## Decision

**Single validation phase after all generation completes.**

Workflow:
1. Context Builder
2. Strategy Planner
3. Copy Generator
4. Image Prompt Generator
5. Image Generator
6. **Validation (once)** → checks strategy + caption + image prompt + image together
7. Human Review

**Validation checks:**
- Brand consistency (caption matches guidelines, image matches prompt)
- Platform compliance (character limits, hashtag rules)
- Safety (no prohibited content)
- Completeness (all required fields present)

**If validation fails:** Regenerate from earliest affected node (per ADR-008 intent-based regeneration).

## Consequences

**Positive:**
- 30-50% latency reduction (fewer validation LLM calls)
- Full automation until human review
- Holistic validation catches cross-component issues
- Simpler workflow graph

**Negative:**
- Larger regeneration scope on validation failure
- Validation prompt more complex (multi-faceted)
- Cannot catch planning errors early (mitigated: planning is deterministic-ish)

## Alternatives Considered

1. **Validate after each step** (original)
   - Rejected: Latency, cost, over-engineering

2. **No validation** (trust AI)
   - Rejected: Quality risk unacceptable

3. **Human review after each step**
   - Rejected: Defeats automation goal

## References

- Architecture Evolution Summary: "Validation Strategy"
- ADR-006: Workflow Graph (validation as single node)
- ADR-008: Intent-Based Regeneration (handles validation failure)
- Plan.md: Validation Service