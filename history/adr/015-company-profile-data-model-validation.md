# ADR-015: Company Profile Data Model & Validation Rules

**Status:** Accepted
**Date:** 2026-07-16

## Context

The Company Profile Service needs a data model that captures sufficient brand information for AI campaign generation while remaining practical for users to maintain. Key questions:
- What fields are required vs optional?
- How to enforce data quality for reliable AI output?
- What constitutes a "complete" profile eligible for campaign generation?

## Decision

**CompanyProfile Entity:**
| Field | Type | Required | Unique | Notes |
|-------|------|----------|--------|-------|
| id | UUID | Yes | Yes | System-generated |
| company_name | string | Yes | Yes | Human-readable identifier |
| brand_guidelines | string | Yes | No | Communication rules, style guide text |
| brand_tone | string | No | No | Optional tone descriptor (e.g., "professional", "playful") |
| reference_images | list[string] | No | No | Ordered image URLs (max 6) |
| created_at | datetime | Yes | No | Timestamp |
| updated_at | datetime | Yes | No | Timestamp |

**BrandReferenceImage Entity:**
| Field | Type | Required | Unique | Notes |
|-------|------|----------|--------|-------|
| id | UUID | Yes | Yes | System-generated |
| company_profile_id | UUID | Yes | No | FK to CompanyProfile |
| storage_path | string | Yes | No | Blob storage path |
| filename | string | Yes | No | Original filename |
| content_type | string | Yes | No | MIME type (jpeg/png/webp) |
| file_size | integer | Yes | No | Bytes |
| sort_order | integer | Yes | No | Position 0-5 |
| uploaded_at | datetime | Yes | No | Timestamp |

**Validation Rules (enforced at API layer + DB constraints):**
1. `company_name` non-empty + unique (DB unique constraint)
2. `brand_guidelines` non-empty (API validation)
3. Max 6 reference_images per profile (business logic check)
4. Image format: JPEG/PNG/WebP only (file validation)
5. Image resolution: >= 1080x1080 (file validation)
6. `sort_order` 0-5, unique per profile (business logic)

**Profile Completeness for Campaign Generation:**
A profile is "complete" (eligible for campaign generation) iff:
- `company_name` is present AND
- `brand_guidelines` is non-empty

`brand_tone` and `reference_images` are optional enhancements.

**Validation Timing:** Fail-fast at profile create/update, NOT deferred to campaign generation time.

## Consequences

**Positive:**
- Structured fields enable targeted validation and updates
- Clear contract for AI prompt construction (guidelines + tone + images)
- Fail-fast prevents incomplete profiles from reaching generation
- Unique company_name prevents duplicate brand entities
- Optional fields don't block text-only campaigns
- Ordered images allow priority-based selection for generation

**Negative:**
- More upfront schema design vs flexible JSON blob
- Unique constraint on company_name requires handling 409 Conflict
- Max 6 images is arbitrary limit (but prevents unbounded growth)
- Resolution check adds upload latency
- Two-table join for profile + images

## Alternatives Considered

1. **Flexible JSON blob instead of structured fields**
   - Rejected: No validation, no targeted updates, harder prompt construction

2. **Require brand_tone for completeness**
   - Rejected: Guidelines text sufficient; tone is refinement

3. **Require at least 1 reference image for completeness**
   - Rejected: Blocks text-only campaigns; images enhance not require

4. **Validate completeness at campaign generation time**
   - Rejected: Fail-fast principle; earlier feedback better UX

5. **Soft delete vs hard delete for profiles**
   - Deferred: Depends on campaign history retention requirements (TBD)

## References

- Plan.md: Data Model, Validation Rules, Tradeoffs
- Research.md: Research 1, 2, 3
- Data-model.md: Entities, Relationships, Validation Rules, State Transitions
- Contracts/openapi.yaml: CreateCompanyProfileRequest, ErrorResponse schemas
- ADR-014: Company Profile Service as Separate Bounded Context