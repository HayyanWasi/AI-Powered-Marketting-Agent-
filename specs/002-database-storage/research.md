# Research: Database & Storage Setup

## Technology Decisions

### Supabase Python SDK (v2)

**Decision**: Use `supabase>=2.0.0` Python SDK for both PostgreSQL and Storage operations.

**Rationale**: Already a project dependency (listed in pyproject.toml). Provides a unified client for both database queries and file storage. Eliminates need for a separate PostgreSQL driver.

**Alternatives considered**:
- `psycopg2` + raw SQL: Would require manual connection management, no Storage support
- SQLAlchemy: Over-engineered for a single-table use case; violates KISS principle
- `boto3` (S3): Would require separate service for file storage; Supabase Storage provides public URLs natively

### Image Validation with Pillow

**Decision**: Use Pillow (PIL) for image validation (file size, dimensions).

**Rationale**: Already a project dependency (listed in pyproject.toml). Can validate image dimensions (>=1080x1080 per constitution) and file format before upload.

**Alternatives considered**:
- `python-magic`: MIME-type detection only, no dimension validation
- Custom validation: Rediscovering what Pillow already provides

### Migration Scripts

**Decision**: Plain SQL files with up/down naming convention, executed manually or via a simple runner script.

**Rationale**: Only two tables exist (company_profiles now, possibly more later). A full migration framework (Alembic) is over-engineered for this scale. Plain SQL is transparent, versionable, and reviewable.

**Alternatives considered**:
- Alembic: Full migration framework; too heavy for single-table project
- Supabase Studio UI: Not reproducible, not version-controlled

### Single-Company V1 Mode

**Decision**: Enforce at the service layer — `create_profile` checks for existing profiles before inserting. No database-level unique constraint beyond the business rule.

**Rationale**: Simplifies service logic. The V1 assumption is that there's one marketing team using the system. When multi-tenant is needed, the constraint can be relaxed with a tenant_id column.

### Retry Logic

**Decision**: Implement exponential backoff retry (3 attempts) on Supabase API calls for transient network failures.

**Rationale**: Supabase is an external API — network blips happen. Retry with backoff increases reliability without requiring a separate resilience library like tenacity.

**Alternatives considered**:
- `tenacity` library: Adds another dependency for a 3-line retry decorator
- No retry: Would fail on transient network errors; violates Fail Gracefully principle
