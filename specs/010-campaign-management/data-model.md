# Data Model: Campaign Management Module

## Entities

### Campaign
Core entity representing a marketing campaign.

| Field | Type | Required | Unique | Notes |
|-------|------|----------|--------|-------|
| id | UUID | Yes | Yes | System-generated (gen_random_uuid) |
| organization_id | UUID | Yes | No | Multi-tenancy; from auth context |
| company_profile_id | UUID | Yes | No | FK to Company Profile (feature 009) |
| name | string | Yes | Yes* | Unique per organization |
| goals | JSONB | Yes | No | Structured: {primary: string, metrics: [], targets: {}} |
| target_audience | JSONB | Yes | No | Structured: {segments: [], demographics: {}, interests: []} |
| platforms | string[] | Yes | No | Enum list: instagram, facebook, linkedin, twitter, tiktok |
| schedule | JSONB | Yes | No | {start_date, end_date, timezone, recurrence_rule?} |
| metadata | JSONB | No | No | Flexible key-value for extensions |
| state | enum | Yes | No | Draft, Ready, Review, Approved, Published, Archived |
| version | integer | Yes | No | Optimistic locking; starts at 1 |
| created_at | timestamptz | Yes | No | Auto NOW() |
| updated_at | timestamptz | Yes | No | Auto NOW() on update |
| published_at | timestamptz | No | No | Set on transition to Published |
| archived_at | timestamptz | No | No | Set on transition to Archived |
| created_by | UUID | Yes | No | Actor ID |
| updated_by | UUID | Yes | No | Actor ID |

*Unique constraint: `(organization_id, name)`

**Relationships**:
- Campaign (1) ────── (0..N) CampaignHistoryEntry
- Campaign (1) ────── (0..N) CampaignAsset
- Campaign (N) ────── (1) CompanyProfile (via company_profile_id)
- Campaign (N) ────── (1) Organization (via organization_id)

---

### CampaignHistoryEntry
Immutable audit log entry for campaign changes.

| Field | Type | Required | Unique | Notes |
|-------|------|----------|--------|-------|
| id | UUID | Yes | Yes | System-generated |
| campaign_id | UUID | Yes | No | FK to campaigns |
| event_type | enum | Yes | No | Created, ConfigurationChanged, StateTransitioned, AssetAssociated, Published, Archived, Restored |
| timestamp | timestamptz | Yes | No | Event time (NOW()) |
| actor_id | UUID | Yes | No | User/service that triggered |
| from_state | enum | No | No | Previous state (for StateTransitioned) |
| to_state | enum | No | No | New state (for StateTransitioned) |
| changed_fields | JSONB | No | No | Field-level diff {field: {old, new}} |
| snapshot | JSONB | No | No | Full campaign state at event (for Published) |
| metadata | JSONB | No | No | Additional context (reason, etc.) |

**Constraints**:
- Append-only: No UPDATE or DELETE permitted (enforced by trigger)
- Index on `(campaign_id, timestamp DESC)` for history queries

---

### CampaignAsset
Deliverable asset associated with a campaign.

| Field | Type | Required | Unique | Notes |
|-------|------|----------|--------|-------|
| id | UUID | Yes | Yes | System-generated |
| campaign_id | UUID | Yes | No | FK to campaigns |
| asset_type | enum | Yes | No | copy, image, hashtag_set, metadata, other |
| content | JSONB | Yes* | No | Text assets: {text, format?}; Images: {url, width, height, mime_type} |
| storage_path | string | No | No | Supabase Storage path (for images) |
| source | enum | Yes | No | ai, manual, imported |
| created_at | timestamptz | Yes | No | Auto NOW() |
| created_by | UUID | Yes | No | Actor ID |

*Required for text assets; images use storage_path + content for metadata

**Asset Type Details**:
- `copy`: {text: string, format: "markdown"|"plain"}
- `image`: {url: string, width: int, height: int, mime_type: string}
- `hashtag_set`: {tags: string[]}
- `metadata`: {key: value} flexible

---

### CampaignState (Enum)
Valid lifecycle states with transition rules.

| State | Description | Can Edit Config? |
|-------|-------------|------------------|
| Draft | Initial state; fully editable | Yes |
| Ready | Configuration complete; awaiting review | No |
| Review | Under review by approver | No |
| Approved | Approved; ready to publish | No |
| Published | Live on platforms | No |
| Archived | Completed/retired; hidden from active lists | No |

**Valid Transitions**:
```
Draft → Ready, Archived
Ready → Review, Draft, Archived
Review → Approved, Ready, Archived
Approved → Published, Review, Archived
Published → Archived
Archived → Draft, Ready, Review, Approved, Published (restore)
```

---

## Validation Rules

| Rule | Scope | Enforcement |
|------|-------|-------------|
| name non-empty, ≤255 chars | Create, Update | API validation + DB CHECK |
| (organization_id, name) unique | Create, Update | DB UNIQUE constraint |
| goals, target_audience, platforms, schedule required | Create | API validation |
| platforms must be valid enum values | Create, Update | API validation |
| state transitions per valid graph | Transition | State machine validation |
| version matches expected on update | Update | DB WHERE version = ? |
| history immutable | Always | DB trigger |
| published_at set only on Published transition | Transition | Service logic |
| archived_at set only on Archived transition | Transition | Service logic |

---

## State Transitions Detail

| From | To | Preconditions | Side Effects |
|------|-----|---------------|--------------|
| Draft | Ready | goals, audience, platforms, schedule present | Record transition; version++ |
| Ready | Review | — | Record transition |
| Ready | Draft | — | Record transition |
| Review | Approved | Actor has approver role | Record transition |
| Review | Ready | — | Record transition |
| Approved | Published | Assets present (if required) | Record transition; set published_at |
| Approved | Review | — | Record transition |
| Published | Archived | — | Record transition; set archived_at |
| Draft | Archived | — | Record transition; set archived_at |
| Archived | [previous] | — | Record transition; clear archived_at; restore previous state |

---

## Indexes

```sql
-- Campaigns
CREATE INDEX idx_campaigns_org_state ON campaigns(organization_id, state);
CREATE INDEX idx_campaigns_org_updated ON campaigns(organization_id, updated_at DESC);
CREATE INDEX idx_campaigns_company_profile ON campaigns(company_profile_id);

-- History
CREATE INDEX idx_history_campaign_time ON campaign_history(campaign_id, timestamp DESC);

-- Assets
CREATE INDEX idx_assets_campaign ON campaign_assets(campaign_id);
```