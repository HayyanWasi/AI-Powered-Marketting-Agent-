---
name: spec-driven-qa-testing
description: Verifies a finished implementation against a spec's requirements, constraints, and success criteria. Use this whenever the user asks for QA testing, acceptance testing, "test this against the spec," sign-off before release, or a pass/fail check on a built feature. This is a check on completed work, not test-writing during development (use test-driven-development for that) and not spec creation (use spec-driven-development for that). Always trigger when the user has a spec document and wants to know if the implementation actually meets it.
---

# Spec-Driven QA Testing

QA against a spec means one thing: does the implementation do what the spec says, nothing more assumed, nothing less accepted. Every test traces back to a line in the spec. If it's not in the spec, it's not in scope for pass/fail — flag it separately.

## Core Rule

**No spec item, no test. No test, no claim of "pass."**

Do not invent requirements the spec doesn't state. Do not skip a requirement because it seems obvious or hard to test. Do not mark something "pass" without evidence you can point to (an actual run, an actual output, an actual error message).

## Step 1: Extract and Separate the Spec

Read the spec, plan, tasks, research, Data-models, quickstart and then split it into three lists. Specs often mix these together in prose — pull them apart:

- **Requirements** — what the system must do (functional behavior)
- **Constraints** — limits it must respect (performance, security, format, compatibility, business rules)
- **Success criteria** — how "done" is measured (the bar for sign-off)

If any of the three is missing, vague, or not measurable, **stop and say so before testing**. Example: "Fast response time" is not testable. "Response under 300ms at p95" is. Flag every vague item back to the user instead of guessing a number.

## Step 2: Build a Traceability Matrix

One row per spec item. Do this before writing a single test case.

| ID | Spec item | Type | Test case(s) | Status |
|----|-----------|------|---------------|--------|
| R1 | User can reset password via email link | Requirement | TC-01, TC-02 | Not run |
| C1 | Link expires after 24 hours | Constraint | TC-03 | Not run |
| S1 | 95% of reset flows complete in under 2 min | Success criteria | TC-04 | Not run |

This matrix is the deliverable that proves coverage. At the end, every row must have a status. A spec item with zero test cases is a gap — call it out, don't ignore it.

## Step 3: Design Test Cases

For every requirement and constraint, cover:

- **Happy path** — the normal, intended use
- **Negative path** — invalid input, wrong sequence, unauthorized access
- **Edge cases** — boundaries (empty, max, zero, exactly-at-the-limit)
- **Constraint violation** — deliberately try to break the constraint (e.g. use an expired link, exceed a rate limit)

Each test case needs:
- What you're doing (steps)
- What you expect (tied directly to the spec wording)
- What actually happened (filled in during execution, not before)

Don't write vague test cases like "check login works." Write "enter valid email + valid password → expect redirect to dashboard within 2s."

## Step 4: Execute and Record

Run every test case. For each one, record:

- **Pass** — actual result matches expected result, with evidence
- **Fail** — actual result does not match; log a defect (Step 5)
- **Blocked** — couldn't run it (environment issue, missing dependency) — this is not a pass, don't count it as one

Do not summarize results without running them. "Should work" is not a status.

## Step 5: Log Defects

For every fail, log:

- Spec item it violates (link back to the traceability matrix ID)
- Steps to reproduce
- Expected vs actual
- Severity — use this scale, don't invent your own:
  - **Blocker** — violates a success criterion or core requirement, ships broken
  - **Major** — violates a requirement or constraint, workaround exists
  - **Minor** — cosmetic or edge-case only, doesn't violate spec wording

## Step 6: Sign-Off Report

The final output is not "looks good." It's a decision, backed by the matrix:

- Coverage: X/Y spec items have at least one test case
- Pass rate: X/Y test cases passed
- Open defects by severity
- **Go / No-Go recommendation**, based only on success criteria — not on your opinion of code quality, not on how close it seems

**No-Go if:** any success criterion fails, or any Blocker defect is open.
**Go with caveats if:** all success criteria pass but Minor defects remain — list them.
**Go if:** all success criteria pass, no Blocker or Major defects open.

State the recommendation in one line at the top of the report. Details follow, not the other way around.

## Failure Modes to Avoid

1. Testing what seems important instead of what the spec says
2. Marking "pass" because the feature "basically works"
3. Treating a vague spec item as testable by guessing a threshold yourself
4. Skipping constraint-violation tests because the happy path passed
5. Burying a No-Go recommendation under a wall of detail
6. Counting "blocked" tests as passes to inflate coverage numbers
7. Testing things outside the spec and letting that affect the sign-off decision — log them separately as observations, not as pass/fail

## Output Format

Always produce, in this order:
1. One-line Go / No-Go / Go-with-caveats verdict
2. Traceability matrix (full, every spec item, every status)
3. Defect list (if any), sorted by severity
4. Anything found outside spec scope (observations only, doesn't affect verdict)
