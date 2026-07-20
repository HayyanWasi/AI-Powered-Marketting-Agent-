# ADR-014: Company Profile Service as Separate Bounded Context

**Status:** Accepted
**Date:** 2026-07-16

## Context

The AI Campaign Generation system needs access to company brand information (guidelines, tone, reference images) to produce on-brand campaigns. Initially, this data could have been embedded within campaign requests or stored as part of campaign records.

Problems with embedded approach:
- Company branding changes infrequently but would require repeated setup per campaign
- No single source of truth for brand identity
- Campaign Generation Service would be bloated with redundant brand data
- No reusability across campaigns for the same company

## Decision

Create a **separate Company Profile Service** as a distinct bounded context/module with its own API contract:

**Module Responsibilities:**
- Company Profile CRUD (create, retrieve, update, list)
- Brand Reference Image management (upload, list, delete, reorder)
- Profile completeness validation for campaign generation eligibility
- Unique company name enforcement

**Integration Contract:**
- Campaign Generation Service retrieves company profiles via REST API (`GET /api/v1/company-profiles/{profile_id}`)
- Company Profile Service exposes OpenAPI 3.1 contract (contracts/openapi.yaml)
- Profile data includes: company_name, brand_guidelines, brand_tone, reference_images (ordered URLs)

**Module Boundary:**
- Company Profile Service owns the `company_profiles` and `brand_reference_images` tables
- Campaign Generation Service treats company profile as read-only reference data
- No direct database access across module boundaries

## Consequences

**Positive:**
- Single source of truth for brand identity
- Profiles persist across campaign sessions
- Campaign Generation stays focused on generation logic
- Independent deployability (future)
- Clear ownership: Company Profile Service = brand data authority
- Reusable profiles across multiple campaigns

**Negative:**
- Additional service/module to maintain
- Network latency for profile retrieval (mitigated: caching in Campaign Generation)
- Contract maintenance overhead
- Potential for stale data if profile updates during campaign generation

## Alternatives Considered

1. **Embed brand data in campaign request**
   - Rejected: Repeated setup per campaign; no persistence; bloated requests

2. **Store brand data directly in campaign records**
   - Rejected: Duplicates data; no single source of truth; harder to update brand globally

3. **Temporary company profiles per session**
   - Rejected: Branding changes infrequently; session-based loses history

4. **Shared database tables (no service boundary)**
   - Rejected: Violates modular architecture (ADR-007); tight coupling

## References

- Plan.md: Architecture, Dependency Sequence, Service Contracts
- Research.md: Research 1, 2, 3
- Data-model.md: Entities, Relationships, Validation Rules
- Contracts/openapi.yaml: API specification
- ADR-007: Modular Architecture with Separated Concerns