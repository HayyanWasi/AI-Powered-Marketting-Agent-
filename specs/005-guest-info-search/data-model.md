# Data Model: Guest Information Retrieval

## Overview

Three core entities: `SearchResult`, `ConfidenceLevel`, `GuestProfile`. Internal dataclass for service logic, Pydantic models for API I/O (following existing pattern from `models/guest.py`).

---

## 1. ConfidenceLevel

Enum for reliability of the generated profile.

| Value | Meaning | Criteria |
|-------|---------|----------|
| `HIGH` | Confident | Consistent, corroborated across multiple (>=3) independent sources |
| `MEDIUM` | Some corroboration | Information present in 2 sources or partial corroboration |
| `LOW` | Uncertain | Single source, or conflicting information that could not be resolved |

If conflicts exist between sources: prefer information appearing consistently across multiple results, ignore unsupported claims, lower confidence level.

---

## 2. SearchResult

Represents a single publicly available search result metadata entry.

| Field | Type | Description | Source |
|-------|------|-------------|--------|
| `website_name` | `str` | Name of the website hosting the result | Extracted from URL domain or search result metadata |
| `page_title` | `str` | Title of the search result page | DDGS `title` field |
| `snippet` | `str` | Search description/snippet | DDGS `body` field |
| `source_url` | `str` | Full URL of the search result | DDGS `href` field |

**Constraints**: Max 7 results per search. Metadata only — no webpage content is fetched or analyzed.

---

## 3. GuestProfile

The structured profile generated from analyzing all `SearchResult` metadata together.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `full_name` | `str` | No | Guest's full name. Empty if cannot be determined. |
| `current_position` | `str` | No | Current professional role/title. Empty if uncertain. |
| `organization` | `str` | No | Current company/organization. Empty if uncertain. |
| `professional_biography` | `str` | No | Concise summary of the guest's background, supported only by search metadata. Empty if insufficient info. |
| `areas_of_expertise` | `list[str]` | No | List of expertise areas identified from search results. Empty list if none. |
| `confidence_level` | `ConfidenceLevel` | Yes | Overall confidence based on consistency and quantity of sources. |
| `sources_used` | `list[SearchResult]` | Yes | The search results that contributed to this profile. |

**State transitions**: Single-shot generation — no mutable state. Either a profile is generated (possibly partial) or manual input is requested.

**Validation rules**:
- All fields may be empty if information cannot be determined (FR-06)
- Never invent or assume missing information (FR-06)
- Biography must summarize only information supported by search results (FR-04)
- Conflicting information lowers confidence level rather than being combined into contradictory claims (FR-05)
- Duplicate information from multiple results is merged (SC-003)

---

## 4. API Models

### GuestSearchRequest (Pydantic — input)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `guest_name` | `str` | Yes | Full name of the guest/speaker to search for |
| `company_name` | `str` | No | Company/organization name (optional). Used to narrow search. |
| `session_id` | `str` | No | Existing session ID to associate the profile with |

### GuestSearchResponse (Pydantic — output)

| Field | Type | Description |
|-------|------|-------------|
| `profile` | `GuestProfile` | The generated guest profile (partial or complete) |
| `needs_manual_input` | `bool` | True when profile could not be reliably generated — user must manually provide biography, position, and organization |
| `error` | `str` | Error message if search/analysis failed entirely |

---

## 5. Relationship to Existing Models

```
Guest (existing) ──session──► GuestProfile (new)
  |                              |
  | session_id                   | session_id
  | guest_name                   | ephemeral (24h TTL)
  | company_name                 | cached in SessionCache
```

A `Guest` represents the identity being searched for (guest_name + company_name). A `GuestProfile` is the **result** of a successful search — it's ephemeral and stored only in the session cache, never in the database.
