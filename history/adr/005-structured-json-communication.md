# ADR-005: Structured JSON Communication over Natural Language Between Components

**Status:** Accepted
**Date:** 2026-07-16

## Context

In the agent-centric architecture, AI agents communicated via natural language:
```
Planning Agent: "This campaign targets millennials interested in sustainable fashion..."
Copy Agent: "Here's a hook that appeals to eco-conscious millennials..."
```

Problems:
- Ambiguity and interpretation variance
- No schema validation
- Difficult to parse programmatically
- Hard to version and evolve
- Debugging requires reading unstructured text
- Cannot enforce contracts between components

## Decision

All inter-component communication (especially AI → AI and AI → deterministic code) uses **structured JSON contracts** with explicit schemas.

**Example:**
```json
{
  "audience": "Eco-conscious millennials (25-35) interested in sustainable fashion",
  "cta": "Shop the sustainable collection",
  "keywords": ["sustainable fashion", "eco-friendly", "organic cotton"],
  "outline": ["Hook", "Problem", "Solution", "CTA"]
}
```

**Enforcement:**
- Pydantic models define all contracts
- Validation at component boundaries
- Versioned schemas in `contracts/` directory

## Consequences

**Positive:**
- Deterministic parsing — no ambiguity
- Schema validation catches errors early
- Easy to version, document, and evolve
- Enables automated testing with fixtures
- Clear contracts between modules
- Debugging: inspect JSON, not prose

**Negative:**
- More upfront schema design work
- Less flexible than natural language
- AI must be prompted for structured output (slightly more tokens)
- Schema changes require coordinated updates

## Alternatives Considered

1. **Natural language communication** (original)
   - Rejected: Ambiguous, unvalidatable, hard to debug

2. **Hybrid: JSON for data, prose for reasoning**
   - Rejected: Two formats = complexity; structured output models handle reasoning traces

3. **Protocol Buffers / gRPC**
   - Rejected: Overkill for internal Python-to-Python; JSON + Pydantic is native

## References

- Architecture Evolution Summary: "AI Communication"
- Plan.md: Service Contracts section
- contracts/ directory (generated artifacts)