# ADR-003: Single Copy Generator over Multiple Writing Agents

**Status:** Accepted
**Date:** 2026-07-16

## Context

Initial design used multiple specialized writing agents: Hook Writer, Caption Writer, CTA Writer, Formatter. Each was a separate LLM call with its own prompt.

Problems:
- Professional copywriting is a single creative process — hook, caption, CTA, and formatting are interdependent
- Splitting reduces quality (hooks don't match captions, CTAs feel disconnected)
- Multiple LLM calls = higher cost, higher latency
- Inconsistent tone/voice across components
- Difficult to maintain brand consistency across fragmented outputs

## Decision

Use a **Single Copy Generator** that produces all copy components in one structured output.

**Output structure:**
```json
{
  "hook": "...",
  "caption": "...",
  "cta": "...",
  "hashtags": [],
  "platform_formatting": {}
}
```

**Reasoning:** Professional copywriting is a unified creative act. The hook must lead naturally into the caption, which must set up the CTA. Hashtags must reflect the caption content. Platform formatting applies to the complete piece.

## Consequences

**Positive:**
- One LLM call for all copy → lower cost, lower latency
- Coherent, unified voice and narrative flow
- Easier validation (single output to check)
- Simpler prompt engineering
- Natural fit for structured JSON output

**Negative:**
- Longer prompt, more tokens per call
- Less granular retry (can't retry just hook)
- All-or-nothing generation (but regeneration is intent-based per ADR-008)

## Alternatives Considered

1. **Multiple writing agents** (original)
   - Rejected: Fragmented creative process, inconsistency, cost, latency

2. **Two-stage: Draft → Refine** - Generate draft, then refine each component
   - Rejected: Adds latency; single pass with good prompting achieves quality

3. **Template-based assembly** - Generate components, assemble via templates
   - Rejected: Templates reduce creativity; AI should handle formatting

## References

- Architecture Evolution Summary: "Content Generation"
- Plan.md: Dependency Sequence item 3
- Research.md: Research 2 (Campaign Outline Generation)