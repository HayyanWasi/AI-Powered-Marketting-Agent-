# Feature Specification: Campaign Management Module

**Feature Branch**: `010-campaign-management`  
**Created**: 2026-07-16  
**Status**: Draft  
**Input**: User description: "Build the Campaign Management module to manage the complete lifecycle of marketing campaigns, including campaign CRUD, configuration, goals, platform selection, audience selection, campaign history, status management, publishing, and future analytics support."

---

## Campaign Management Module

**Intent**: Manage the complete lifecycle, configuration, state, and publication of marketing campaigns while serving as the single source of truth for campaign business data.

**Success Criteria**:
- Supports Create, Read, Update, Delete, Archive, and Restore operations for campaigns.
- Stores and retrieves campaign configuration accurately, including goals, audience, platforms, schedule, and metadata.
- Enforces valid campaign lifecycle transitions (Draft → Ready → Review → Approved → Published → Archived).
- Maintains a complete, immutable history of campaign changes and publication events.
- Stores campaign assets regardless of how they were generated.
- Allows users to resume editing draft campaigns without data loss.
- Publishes campaigns only after all required business conditions are satisfied.
- Provides campaign data consistently to downstream modules through defined interfaces.

**Constraints**:
- Acts as the single source of truth for all campaign business data.
- Must remain completely independent of AI generation, prompts, models, and workflow orchestration.
- Must reject invalid campaign state transitions.
- Campaign updates must be atomic; partial updates are not permitted.
- Campaign history must be append-only and immutable.
- Business validation must occur before any persistent state change.
- Modules may access campaign data only through public interfaces.

**Non-Goals**:
- Campaign strategy planning.
- SEO research and keyword planning.
- Copy, caption, or hashtag generation.
- Image prompt creation or image generation.
- Workflow execution, routing, retries, or checkpoint management.
- Human approval orchestration.
- Prompt management, model management, or execution tracing.
- Campaign analytics and performance reporting (future module).

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create a New Campaign (Priority: P1)
A marketing user creates a new campaign with basic configuration (name, goals, target audience, platforms, schedule) and saves it as a draft.

**Why this priority**: Campaign creation is the entry point for all campaign workflows. Without it, no other operations are possible.

**Independent Test**: Can be tested by creating a campaign via the public interface and verifying it persists with all provided configuration, returns a valid campaign ID, and is in "Draft" state.

**Acceptance Scenarios**:
1. **Given** a user with valid campaign configuration, **When** they create a campaign, **Then** the campaign is persisted with all fields, assigned a unique ID, and set to "Draft" state.
2. **Given** a campaign with required fields (name, goals, audience, platforms), **When** created, **Then** the campaign is retrievable by ID and matches the input configuration.
3. **Given** a campaign creation request with missing required fields, **When** submitted, **Then** the request is rejected with a validation error and no campaign is created.

---

### User Story 2 - Update Campaign Configuration (Priority: P1)
A marketing user modifies an existing draft campaign's configuration (goals, audience, platforms, schedule, metadata) and saves the changes.

**Why this priority**: Campaigns often require iterative refinement before review. Users must be able to update any aspect of a draft campaign.

**Independent Test**: Can be tested by creating a campaign, then updating each configuration field independently and verifying persistence and atomicity.

**Acceptance Scenarios**:
1. **Given** a campaign in "Draft" state, **When** the user updates any configuration field, **Then** the change is persisted atomically and the campaign remains in "Draft" state.
2. **Given** a campaign in "Draft" state, **When** the user submits a partial update (only some fields), **Then** only the provided fields are updated; unspecified fields retain their previous values.
3. **Given** a campaign not in "Draft" state, **When** the user attempts to update configuration, **Then** the request is rejected with a state transition error.

---

### User Story 3 - Advance Campaign Through Lifecycle (Priority: P1)
A marketing user advances a campaign through valid lifecycle states: Draft → Ready → Review → Approved → Published.

**Why this priority**: The lifecycle enforces business process. Each transition represents a meaningful gate (readiness, review, approval, publication).

**Independent Test**: Can be tested by creating a campaign and advancing it through each valid transition, verifying state changes and that required conditions are checked.

**Acceptance Scenarios**:
1. **Given** a campaign in "Draft" state with complete configuration, **When** the user marks it "Ready", **Then** the state changes to "Ready" and the transition is recorded in history.
2. **Given** a campaign in "Ready" state, **When** the user submits for review, **Then** the state changes to "Review".
3. **Given** a campaign in "Review" state, **When** an authorized reviewer approves it, **Then** the state changes to "Approved".
4. **Given** a campaign in "Approved" state, **When** the user publishes it, **Then** the state changes to "Published" and the publication timestamp is recorded.
5. **Given** a campaign in any state, **When** the user attempts an invalid transition (e.g., Draft → Approved), **Then** the request is rejected with a state transition error.

---

### User Story 4 - Archive and Restore Campaign (Priority: P2)
A marketing user archives a published or completed campaign, and later restores it to its previous state.

**Why this priority**: Archiving removes campaigns from active views while preserving data. Restoration supports reuse and compliance.

**Independent Test**: Can be tested by publishing a campaign, archiving it, verifying it no longer appears in active lists, then restoring it and verifying the previous state is recovered.

**Acceptance Scenarios**:
1. **Given** a campaign in "Published" state, **When** the user archives it, **Then** the state changes to "Archived" and the campaign is excluded from active campaign listings.
2. **Given** a campaign in "Archived" state, **When** the user restores it, **Then** the state returns to its pre-archived state (e.g., "Published") and the campaign reappears in active listings.
3. **Given** a campaign in "Draft" state, **When** the user archives it, **Then** the state changes to "Archived" (drafts can be archived directly).

---

### User Story 5 - View Campaign History (Priority: P2)
A marketing user views the complete, immutable history of a campaign including all configuration changes, state transitions, and publication events.

**Why this priority**: History provides audit trail, debugging capability, and compliance evidence. Immutability ensures trust.

**Independent Test**: Can be tested by performing a series of operations on a campaign (create, update, transition, publish) and verifying the history log contains every event in order with correct details.

**Acceptance Scenarios**:
1. **Given** a campaign with multiple updates and state transitions, **When** the user requests history, **Then** the history returns all events in chronological order with timestamps, actor, event type, and changed fields.
2. **Given** a campaign history, **When** any attempt is made to modify or delete a history entry, **Then** the operation is rejected (history is append-only and immutable).
3. **Given** a campaign, **When** the user views history, **Then** publication events include the publication timestamp and the campaign snapshot at time of publication.

---

### User Story 6 - Retrieve Campaign for Downstream Use (Priority: P1)
A downstream module (e.g., Campaign Generation, Publishing) retrieves a campaign by ID to access its configuration and assets.

**Why this priority**: The module is the single source of truth. Downstream consumers need consistent, reliable access.

**Independent Test**: Can be tested by creating a campaign with assets, then retrieving it via the public interface and verifying all configuration and asset references are present and accurate.

**Acceptance Scenarios**:
1. **Given** a campaign with configuration and associated assets, **When** a downstream module retrieves it by ID, **Then** the response includes all configuration fields and asset references.
2. **Given** a campaign ID that does not exist, **When** a retrieval is attempted, **Then** a "not found" error is returned.
3. **Given** a campaign in "Draft" state, **When** retrieved by a downstream module, **Then** the data is returned (state does not restrict read access).

---

### User Story 7 - Store Campaign Assets (Priority: P2)
The system stores campaign assets (generated copy, images, hashtags, metadata) regardless of how they were generated (AI, manual, imported).

**Why this priority**: Assets are the deliverable. The module must persist them without coupling to generation method.

**Independent Test**: Can be tested by attaching assets to a campaign via the public interface and verifying they are retrievable with the campaign.

**Acceptance Scenarios**:
1. **Given** a campaign, **When** assets are associated with it, **Then** the assets are persisted and returned with the campaign.
2. **Given** assets from different sources (AI-generated, manually entered, imported), **When** stored, **Then** all are treated equally with no source-specific logic.
3. **Given** a campaign with assets, **When** the campaign is retrieved, **Then** all assets are included in the response.

---

### Edge Cases

- **Concurrent updates**: Two users attempt to update the same campaign simultaneously → system uses optimistic locking or last-write-wins with conflict detection.
- **Large campaign configuration**: Campaign with maximum allowed platforms, audience segments, and metadata → system handles without performance degradation.
- **Invalid state transition chain**: User attempts Draft → Published directly → rejected with clear error message listing valid next states.
- **Delete vs Archive**: User attempts to delete a Published campaign → system requires archiving first; hard delete only for Drafts (or not at all, per policy).
- **History size**: Campaign with hundreds of history entries → history retrieval supports pagination.
- **Asset storage limits**: Campaign exceeds asset storage quota → clear error at association time.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow users to create a new campaign with required fields (name, goals, target audience, platforms, schedule) and optional metadata.
- **FR-002**: System MUST assign a unique identifier to each campaign upon creation.
- **FR-003**: System MUST allow users to retrieve a campaign by its unique identifier.
- **FR-004**: System MUST allow users to list campaigns with filters (state, date range, owner).
- **FR-005**: System MUST allow users to update a campaign's configuration (goals, audience, platforms, schedule, metadata) when the campaign is in "Draft" state.
- **FR-006**: System MUST reject configuration updates for campaigns not in "Draft" state with a clear state transition error.
- **FR-007**: System MUST enforce atomic updates — all provided fields update together or none do.
- **FR-008**: System MUST enforce the following valid state transitions:
  - Draft → Ready
  - Ready → Review
  - Ready → Draft (reopen)
  - Review → Approved
  - Review → Ready (request changes)
  - Approved → Published
  - Approved → Review (recall approval)
  - Published → Archived
  - Archived → [previous state] (restore)
  - Draft → Archived
- **FR-009**: System MUST reject any state transition not listed in FR-008 with a descriptive error.
- **FR-010**: System MUST record every state transition in the campaign history with timestamp, actor, from-state, to-state, and reason (if provided).
- **FR-011**: System MUST record every configuration change in the campaign history with timestamp, actor, and changed fields (before/after values).
- **FR-012**: System MUST record publication events in history with timestamp, actor, and campaign snapshot at publication.
- **FR-013**: Campaign history MUST be append-only — no modification or deletion of history entries is permitted.
- **FR-014**: System MUST allow users to associate assets (copy, images, hashtags, metadata) with a campaign.
- **FR-015**: System MUST store assets without coupling to their generation source (AI, manual, imported).
- **FR-016**: System MUST allow users to archive a campaign from any state, moving it to "Archived" state.
- **FR-017**: System MUST allow users to restore an archived campaign to its previous state.
- **FR-018**: System MUST exclude archived campaigns from default active campaign listings.
- **FR-019**: System MUST validate all required business conditions before allowing a state transition (e.g., "Ready" requires complete configuration; "Approved" requires review completion).
- **FR-020**: System MUST perform business validation before any persistent state change; invalid requests must not mutate data.
- **FR-021**: System MUST provide a public interface (API) for downstream modules to retrieve campaign data by ID.
- **FR-022**: System MUST return campaign data including all configuration fields and asset references via the public interface.
- **FR-023**: System MUST support pagination for campaign list and history queries.
- **FR-024**: System MUST support optimistic concurrency control for campaign updates to prevent lost updates.

### Key Entities

- **Campaign**: The central entity representing a marketing campaign.
  - Attributes: ID (UUID), Name (string, required), Goals (structured text, required), Target Audience (structured, required), Platforms (list of platform identifiers, required), Schedule (start/end dates, timezone, required), Metadata (key-value pairs, optional), State (enum: Draft, Ready, Review, Approved, Published, Archived), Created At (timestamp), Updated At (timestamp), Published At (timestamp, nullable), Archived At (timestamp, nullable), Version (integer for optimistic locking).
  - Relationships: Has many History Entries; Has many Assets; References Company Profile (via Company Profile Service).

- **Campaign History Entry**: Immutable record of a campaign event.
  - Attributes: ID (UUID), Campaign ID (FK), Event Type (enum: Created, ConfigurationChanged, StateTransitioned, AssetAssociated, Published, Archived, Restored), Timestamp, Actor (user ID or system), From State (nullable), To State (nullable), Changed Fields (JSON, nullable), Snapshot (JSON, nullable — full campaign state at time of event for publication events).
  - Relationships: Belongs to Campaign.

- **Campaign Asset**: A deliverable associated with a campaign.
  - Attributes: ID (UUID), Campaign ID (FK), Asset Type (enum: Copy, Image, HashtagSet, Metadata, Other), Content (JSON or text), Source (enum: AI, Manual, Imported), Created At (timestamp).
  - Relationships: Belongs to Campaign.

- **Campaign State**: Enum defining valid lifecycle states.
  - Values: Draft, Ready, Review, Approved, Published, Archived.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can create a campaign with all required configuration in under 2 minutes.
- **SC-002**: Campaign configuration updates are reflected immediately upon save (under 500ms perceived latency).
- **SC-003**: Invalid state transitions are rejected 100% of the time with a clear error message listing valid next states.
- **SC-004**: Campaign history captures 100% of configuration changes and state transitions with zero data loss.
- **SC-005**: History queries return results in under 1 second for campaigns with up to 500 history entries.
- **SC-006**: Downstream modules retrieve campaign data via the public interface with 99.9% availability.
- **SC-007**: Archived campaigns are excluded from active listings within 1 second of archiving.
- **SC-008**: Concurrent update attempts on the same campaign are detected and resolved without data corruption (optimistic locking succeeds or fails cleanly).
- **SC-009**: Campaign assets from any source (AI, manual, imported) are stored and retrieved identically.
- **SC-010**: A campaign can be advanced from Draft to Published through all required gates with zero manual workarounds.

---

## Assumptions

- **Authentication/Authorization**: User identity and permissions are provided by an external auth system; this module receives actor IDs and enforces ownership/role checks.
- **Company Profile Integration**: Campaigns reference Company Profiles (from module 009) for brand context; this module stores only the Company Profile ID, not the profile data itself.
- **Asset Storage**: Large binary assets (images) are stored in object storage (e.g., Supabase Storage); this module stores references (URLs, metadata) only.
- **Notification/Events**: State transitions may emit domain events for downstream consumers; event publishing is asynchronous and at-least-once.
- **Data Retention**: Campaigns and history are retained indefinitely unless a separate retention policy module is introduced.
- **Multi-tenancy**: The module supports multiple organizations/workspaces via a tenant/organization ID on each campaign (inherited from user context).