# ADR-008: Intent-Based Regeneration Strategy

**Status:** Accepted
**Date:** 2026-07-16

## Context

Originally, any user edit to a campaign triggered full regeneration: planning → copy → image prompts → images. This caused:
- High latency (user waits for entire pipeline)
- High cost (re-running LLMs and image generation unnecessarily)
- Poor UX (changing caption regenerates images)

## Decision

**Intent-based regeneration:** Only re-execute workflow nodes affected by the user's edit intent.

| Edit Intent | Regenerates | Preserves |
|-------------|-------------|-----------|
| Caption change | Caption only | Strategy, image prompt, image |
| Image change | Image prompt + image | Strategy, caption |
| Strategy change | Planning + caption + image prompt + image | (nothing) |
| Platform change | Caption formatting + platform-specific elements | Core strategy, image |
| Tone change | Caption (rewritten) | Strategy, image |

**Implementation:** Workflow tracks dependency graph. User edit declares intent → workflow computes minimal affected subgraph → resumes from earliest affected node.

## Consequences

**Positive:**
- 60-80% faster edits (empirically)
- 50-70% cost reduction for edits
- Better UX: instant preview for caption tweaks
- Clear mental model for users

**Negative:**
- Complexity in dependency tracking
- Must correctly declare edit intent (UI responsibility)
- Risk of stale preserved artifacts if dependencies missed
- More complex workflow state

## Alternatives Considered

1. **Full regeneration always** (original)
   - Rejected: Unacceptable latency/cost for iterative editing

2. **Manual "regenerate" buttons per section**
   - Rejected: Burden on user; error-prone

3. **Diff-based regeneration** (compare old vs new output)
   - Rejected: Semantic diff on LLM output is unreliable

## References

- Architecture Evolution Summary: "Regeneration Strategy"
- Plan.md: Workflow Graph dependencies
- ADR-006: LangGraph Workflow Orchestration (enables this)