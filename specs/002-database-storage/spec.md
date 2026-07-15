# Feature Specification: Database & Storage Setup

**Feature Branch**: `002-database-storage`
**Created**: 2026-07-13
**Status**: Draft
**Input**: User description: "Set up Supabase PostgreSQL database and storage buckets for company profiles and brand images. FR-11, FR-12, FR-13."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Marketing User Sets Up Company Brand Profile (Priority: P1)

As a marketing user configuring the AI Social Campaign Manager for the first time, I want to create my company profile with brand tone and upload reference images, so that the system can generate brand-consistent social media campaigns automatically.

**Why this priority**: Company profile setup is the entry gate — no campaign can be generated without brand context. All downstream features (agents, image generation, validation) depend on this data existing.

**Independent Test**: A user can create a company profile with name and tone, upload up to 6 reference images via multipart upload, and verify the profile is stored and retrievable via the API.

**Acceptance Scenarios**:

1. **Given** a first-time marketing user, **When** they submit a company name and brand tone, **Then** a company profile is created with a unique ID and timestamps.
2. **Given** an existing company profile, **When** the user uploads up to 6 brand reference images via multipart/form-data, **Then** each image gets a permanent public URL stored in the profile.
3. **Given** a company name that already exists (single-company V1 constraint), **When** the user tries to create a duplicate, **Then** the system rejects with "Company name already exists".

---

### User Story 2 - Developer Manages Company Profiles via SupabaseService (Priority: P2)

As a developer integrating company profile management into the campaign workflow, I want a service abstraction with full CRUD operations, so that I can programmatically create, read, update, and delete brand data without writing raw queries.

**Why this priority**: CRUD operations are the building blocks for the orchestration layer. Agents need to read profiles during generation, and admins need to update brand guidelines over time. A service abstraction keeps data logic centralized and testable.

**Independent Test**: All four CRUD operations can be verified independently via the service interface, with mocked data client, without requiring any other feature.

**Acceptance Scenarios**:

1. **Given** a valid company profile, **When** queried by ID, **Then** the complete profile is returned.
2. **Given** an existing company profile, **When** updated with new name/tone/images, **Then** the profile is updated and the last-updated timestamp refreshes.
3. **Given** an existing company profile, **When** deleted by ID, **Then** the profile is removed and success is confirmed.

---

### User Story 3 - Developer Runs Database Migrations for Schema Versioning (Priority: P3)

As a developer maintaining the database schema over time, I want versioned migration scripts that can create and roll back the company_profiles table, so that schema changes are tracked, repeatable, and reversible.

**Why this priority**: Migration scripts ensure database consistency across environments (dev, staging, production) but are only needed once the table design is finalized.

**Independent Test**: A developer can run the up migration, verify the table exists with correct schema, run the down migration, and verify the table is removed — all without any application code running.

**Acceptance Scenarios**:

1. **Given** a clean database instance, **When** the up migration runs, **Then** the `company_profiles` table is created with the correct schema.
2. **Given** the table exists, **When** the down migration runs, **Then** the table is dropped cleanly.
3. **Given** the table already exists, **When** the up migration runs again, **Then** it succeeds without errors (idempotent).

---

### Edge Cases

- **Duplicate Company Names**: What happens when creating a company with an existing name? Reject with "Company name already exists" error (single-company V1).
- **Image Upload Failures**: What if one image upload fails among multiple? Return success for uploaded images with error for failed ones; allow retry.
- **Empty Reference Images**: Can a company exist with zero reference images? Yes, defaults to empty set.
- **Large Image Files**: What if image exceeds storage limits? Validate file size (10MB max) and reject with clear error.
- **Concurrent Updates**: What if two users update the same company simultaneously? Last-write-wins.
- **Migration Rollback**: How to rollback schema if needed? Down migration drops the table.
- **Missing Required Fields**: What if name or tone is missing? Validate and reject with "Required field missing" error.
- **Storage Bucket Not Found**: What if storage bucket does not exist on upload? Create bucket on first use or return clear setup error.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-DB-01**: System MUST create a `company_profiles` table with columns: id (UUID PK), name (text, required), tone (text, required), reference_image_urls (text array), created_at (timestamp), updated_at (timestamp).
- **FR-DB-02**: System MUST create a public storage bucket for brand reference images with 10MB max file size.
- **FR-DB-03**: System MUST provide an image upload endpoint that accepts multipart/form-data with up to 6 image files, uploads each to storage, and returns permanent public URLs.
- **FR-DB-04**: System MUST implement a service class that wraps the data client and exposes methods: `create_profile(name, tone)`, `get_profile(id)`, `update_profile(id, data)`, `delete_profile(id)`, `upload_image(file)`.
- **FR-DB-05**: `create_profile` MUST require non-empty name and tone, auto-generate ID and timestamps, and reject duplicate company names.
- **FR-DB-06**: `get_profile` MUST return the complete profile by ID or indicate not found.
- **FR-DB-07**: `update_profile` MUST update name, tone, and image URL fields, auto-update the last-updated timestamp, and error if profile does not exist.
- **FR-DB-08**: `delete_profile` MUST remove the profile by ID, return success confirmation, error if not found, and NOT delete associated storage images.
- **FR-DB-09**: `upload_image` MUST validate file size under 10MB, upload to storage, and return a permanent public URL.
- **FR-DB-10**: System MUST support single-company mode (V1) — only one company profile exists at a time. Creating a new profile when one exists is blocked until the existing one is deleted.
- **FR-DB-11**: System MUST provide database migration scripts that are idempotent, versioned, and support both up and down operations.
- **FR-DB-12**: All service methods MUST include retry logic on network failures and return meaningful error messages.

### Key Entities

- **Company Profile**: A single marketing organization record with brand identity (name, tone) and up to 6 reference image URLs.
- **Brand Reference Image**: An image file (logo, color palette, style example) uploaded via multipart/form-data, with a permanent public URL.
- **Data Service**: Abstraction class that encapsulates all database and storage operations, providing a clean interface for callers and enabling mock-based testing.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Company profile can be created, read, updated, and deleted via the service interface with all operations completing in under 100ms for single record lookups.
- **SC-002**: Images upload to storage with permanent public URLs in under 10 seconds per image.
- **SC-003**: Service layer has >=80% test coverage across all CRUD paths and error states, with mocked data client.
- **SC-004**: Migration scripts run both up and down cleanly across dev, staging, and production environments.
- **SC-005**: Company lookup by ID completes in under 100ms under normal network conditions.
- **SC-006**: Storage bucket is publicly accessible with 10MB file size limit enforced.
- **SC-007**: Service raises user-friendly errors for all failure modes (missing fields, duplicates, network failures, invalid files).
