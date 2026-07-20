# ADR-017: Supabase PostgreSQL + Supabase Storage for Company Profile Persistence

**Status:** Accepted
**Date:** 2026-07-16

## Context

The Company Profile Service requires persistent storage for:
- Structured company profile data (profiles, images metadata)
- Binary brand reference images
- Support for concurrent access from Campaign Generation Service

Options evaluated against project constraints (Python 3.13+, FastAPI, existing Supabase usage in codebase).

## Decision

**Primary Database: Supabase PostgreSQL**
- Tables: `company_profiles`, `brand_reference_images`
- UUID primary keys, foreign key relationships
- Unique constraint on `company_profiles.company_name`
- Row Level Security (RLS) policies for future multi-tenancy
- Connection via Supabase Python SDK (async via httpx)

**Blob Storage: Supabase Storage (Public Bucket)**
- Bucket: `brand-images` (public read)
- Path pattern: `{company_profile_id}/{image_id}.{ext}`
- Direct public URL access for Campaign Generation prompts
- Supabase Python SDK for upload/delete operations

**Integration with Existing Stack:**
- FastAPI service uses `supabase` Python SDK
- Async HTTP via `httpx` for Supabase REST calls
- Image validation via `Pillow` before upload
- Pydantic models for request/response validation

## Consequences

**Positive:**
- Leverages existing Supabase infrastructure (no new vendor)
- PostgreSQL provides ACID, constraints, relational integrity
- Supabase Storage integrates with same auth/project
- Public bucket = simple CDN-like image delivery
- Single connection pool for DB + Storage via SDK
- Row Level Security ready for future auth
- Type-safe Python SDK with async support
- Managed service (no DB ops overhead)

**Negative:**
- Vendor lock-in to Supabase (mitigated: standard PostgreSQL + S3-compatible)
- Public bucket = images accessible without auth (acceptable: brand assets)
- Supabase SDK adds dependency (already in pyproject.toml)
- Cold starts on Supabase free tier (acceptable for MVP)
- RLS policies add complexity if multi-tenancy needed

## Alternatives Considered

1. **Self-hosted PostgreSQL + S3/MinIO**
   - Rejected: Operational overhead; Supabase already in use

2. **MongoDB + GridFS**
   - Rejected: Relational data fits SQL better; team expertise in PostgreSQL

3. **Supabase PostgreSQL + Base64 in DB**
   - Rejected: Performance, size limits, no streaming (per ADR-016)

4. **Firebase Firestore + Firebase Storage**
   - Rejected: Different paradigm; Supabase already established

5. **SQLite + Local filesystem**
   - Rejected: No persistence across deployments; no concurrency

## References

- Plan.md: Technical Context, Storage, Architecture
- AGENTS.md: Active Technologies (Supabase PostgreSQL, Supabase Storage)
- Contracts/openapi.yaml: Image URL format in BrandImageResponse
- ADR-014: Company Profile Service as Bounded Context
- ADR-015: Company Profile Data Model & Validation Rules
- ADR-016: Brand Reference Image Management Strategy