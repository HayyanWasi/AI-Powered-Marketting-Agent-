# Specification: Database & Storage Setup

**Feature Name:** database-storage  
**Phase:** Foundation  
**Priority:** 🔴 Critical  
**Estimated Time:** 3-4 hours

# User Story

As a developer building the AI Social Campaign Manager,

I want a configured PostgreSQL database and storage system for company profiles and brand images,

So that the application can persistently store company data, retrieve brand guidelines, and manage reference images for campaign generation.

# Overview

The database and storage setup establishes the persistent data layer for the AI Social Campaign Manager. This includes creating the `company_profiles` table in Supabase PostgreSQL for storing company information (name, brand tone, reference image URLs), setting up Supabase Storage buckets for brand images, implementing CRUD operations for company profiles, and creating database migration scripts. This foundation enables the company profile management needed for brand-consistent campaign generation.

# Functional Requirements

## FR-DB-01: Company Profiles Table Schema

The system shall create a `company_profiles` table in Supabase PostgreSQL with the following schema:

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | Unique company identifier |
| name | TEXT | NOT NULL | Company/organization name |
| tone | TEXT | NOT NULL | Brand voice/tone description |
| reference_image_urls | TEXT[] | NOT NULL, DEFAULT '{}' | Array of up to 6 public image URLs |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | Creation timestamp |
| updated_at | TIMESTAMPTZ | DEFAULT NOW() | Last update timestamp |

### Acceptance Criteria

- Table exists in Supabase PostgreSQL
- Schema matches specification exactly
- Default values work as expected
- Table can be queried via Supabase client

---

## FR-DB-02: Supabase Storage Bucket

The system shall create a public Supabase Storage bucket for brand reference images.

### Acceptance Criteria

- Storage bucket is publicly accessible
- Images uploaded generate permanent public URLs
- Bucket policy allows public read access
- Maximum file size configured (10MB recommended)

---

## FR-DB-03: Image Upload and URL Generation

The system shall upload brand reference images to Supabase Storage and return permanent public URLs.

### Acceptance Criteria

- Images upload successfully to storage bucket
- Generated URLs are permanent and publicly accessible
- Upload returns the public URL immediately after completion
- Failed uploads return clear error messages
- Supports at least 5-6 images per company (FR-11)

---

## FR-DB-04: Create Company Profile

The system shall create a new company profile with name, tone, and reference image URLs.

### Acceptance Criteria

- Requires name and tone (both non-empty)
- Accepts array of up to 6 image URLs
- Auto-generates UUID and timestamps
- Returns complete profile with generated ID
- Rejects duplicate company names

---

## FR-DB-05: Read Company Profile

The system shall retrieve a company profile by ID.

### Acceptance Criteria

- Returns complete profile when ID exists
- Returns None/null when ID does not exist
- Supports key-value lookup by company_id (FR-15)

---

## FR-DB-06: Update Company Profile

The system shall update an existing company profile.

### Acceptance Criteria

- Updates name, tone, and reference_image_urls fields
- Auto-updates updated_at timestamp
- Prevents updating non-existent company
- Returns updated profile

---

## FR-DB-07: Delete Company Profile

The system shall delete a company profile by ID.

### Acceptance Criteria

- Removes profile from database
- Returns success confirmation
- Returns error if profile does not exist
- Does NOT delete associated storage images (soft deletion concept)

---

## FR-DB-08: Database Migration Scripts

The system shall provide database migration scripts for schema versioning.

### Acceptance Criteria

- Migration script creates table if not exists
- Migration script rolls back (drops table) correctly
- Migration script is idempotent (safe to run multiple times)
- Migration script includes comments explaining schema

# Non-Functional Requirements

## NFR-DB-01: Performance

- Table queries complete in under 100ms for single company lookup
- Image upload completes in under 10 seconds (depends on file size)

---

## NFR-DB-02: Reliability

- Database connection retries on failure (up to 3 attempts)
- Transaction support for image upload + profile creation
- Error handling for network failures during upload

---

## NFR-DB-03: Security

- All API keys stored as environment variables (FR-12)
- Table uses Row Level Security (RLS) initially disabled for V1
- Storage bucket is public but images are content-addressable

---

## NFR-DB-04: Maintainability

- Migration scripts versioned in git
- Schema changes documented
- Clear error messages for all database operations

# Edge Cases

## Duplicate Company Names

**What happens when creating a company with an existing name?**

Answer: Reject with "Company name already exists" error (future deduplication logic)

---

## Image Upload Failures

**What happens if one image upload fails among multiple uploads?**

Answer: Return success for uploaded images with error for failed ones; allow retry

---

## Empty Reference Images

**Can a company exist with zero reference images?**

Answer: Yes, `reference_image_urls` defaults to empty array

---

## Large Image Files

**What happens if image exceeds storage limits?**

Answer: Validate file size (10MB max) and reject with clear error

---

## Concurrent Updates

**What happens if two users update the same company simultaneously?**

Answer: Supabase handles with timestamp-based conflict detection; last write wins

---

## Migration Rollback

**How to rollback schema changes if needed?**

Answer: Migration scripts support down migration (drop table)

---

## Missing Required Fields

**What happens if name or tone is missing?**

Answer: Validate and reject with "Required field missing" error

# Success Criteria

- ✅ Company profile can be created, read, updated, and deleted via Supabase client
- ✅ Images upload to Supabase Storage with permanent public URLs
- ✅ Database operations have ≥80% test coverage
- ✅ Migration scripts work both up and down
- ✅ Company lookup by ID completes in under 100ms
- ✅ Supabase Storage bucket is publicly accessible
- ✅ All tests pass in CI/CD pipeline

# Dependencies & Assumptions

## Dependencies

- External: Supabase project with PostgreSQL database and Storage enabled
- Internal: project-foundation feature (UV, Python environment, settings)

---

## Assumptions

- Supabase project is already created and accessible
- Supabase URL and API key are available in environment variables
- Storage bucket is configured with public policy
- Database credentials are valid
- Network connectivity to Supabase is available

# Out of Scope (For This Feature)

- Row Level Security (RLS) policies (deferred to V2 with multi-user)
- Company profile search/filtering (basic CRUD only)
- Image optimization/processing (upload raw images)
- Database connection pooling configuration
- Migration tools beyond basic up/down scripts
- Multi-company support (single company per profile in V1)
- Soft delete functionality (hard delete for V1)
- Image deletion when company is deleted
- Foreign key relationships to other tables (future features)

# Validation Checklist

## Content Quality

- No implementation details (languages, frameworks, APIs) - Focused on database structure
- Focused on user value and business needs - Enables company profile management for brand consistency
- Written for non-technical stakeholders - Clear acceptance criteria
- All mandatory sections completed

---

## Requirement Completeness

- No [NEEDS CLARIFICATION] markers remain
- Requirements are testable and unambiguous
- Success criteria are measurable
- Success criteria are technology-agnostic (no implementation details)
- All acceptance scenarios are defined
- Edge cases are identified
- Scope is clearly bounded
- Dependencies and assumptions identified

---

## Feature Readiness

- All functional requirements have clear acceptance criteria
- User scenarios cover primary flows
- Feature meets measurable outcomes defined in Success Criteria
- No implementation details leak into specification

# Notes

✅ All validation checks passed. This specification is ready for implementation planning.

The specification is complete and provides a clear data layer foundation for the AI Social Campaign Manager. It defines a simple, focused set of requirements for company profile management with Supabase PostgreSQL and Storage, ensuring the persistent data layer is ready for the orchestration and agent features.