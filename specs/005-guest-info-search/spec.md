# Feature Specification: Guest Information Retrieval

**Feature Branch**: `005-guest-info-search`
**Phase**: Core Services
**Created**: 2026-07-15
**Status**: Draft
**Input**: DuckDuckGo Search Service for automatically gathering publicly available guest/speaker information from search engines to generate structured guest profiles for personalized social media campaign content.

## User Scenarios & Testing

### User Story 1 - Search and Generate Guest Profile (Priority: P1)

As a Marketing Organizer, I want the system to automatically gather publicly available information about a guest so that I do not need to manually research every speaker before generating marketing content.

**Why this priority**: This is the core value of the feature — without automated retrieval, the organizer must manually research each guest, defeating the purpose.

**Independent Test**: Can be fully tested by providing a known guest name and verifying a structured profile is returned with the expected fields populated.

**Acceptance Scenarios**:

1. **Given** a valid guest name and optionally a company name, **When** the system performs a search, **Then** the system shall generate a structured guest profile containing Full Name, Current Position, Organization, Professional Biography, Areas of Expertise, Confidence Level, and Sources Used.
2. **Given** only partial information is available from search results, **When** the profile is generated, **Then** the system shall populate only the fields it can determine and leave others empty.
3. **Given** different search results contain conflicting information (e.g., different job titles), **When** the profile is generated, **Then** the system shall prefer information appearing consistently across multiple results and lower the confidence level when conflicts cannot be resolved.
4. **Given** no relevant search results exist, **When** the search completes, **Then** the system shall request the organizer to manually provide the Professional Biography, Current Position, and Organization.
5. **Given** a search using guest name and company returns fewer than 3 results, **When** the system detects insufficient results, **Then** it shall automatically retry using only the guest name.

---

### Edge Cases

- Guest has no company associated with them.
- Guest recently changed company — search may surface old and new roles.
- Guest has multiple professional roles across different organizations.
- Multiple people share the same name — results may mix profiles.
- Search results contain outdated information (old role, old company).
- Search results contain duplicate information from different sources.
- Search results contain conflicting information (e.g., different titles).
- Guest has very limited online presence — few or no search results.
- Company name leads to zero results but guest name alone produces results.

## Requirements

### Functional Requirements

- **FR-01**: The system shall accept a Guest Name (required) and Company Name (optional) as input. When both values are available, the system shall search using both. If the company name is unavailable or produces fewer than 3 results, the system shall retry using only the guest name.
- **FR-02**: The system shall retrieve up to seven (7) publicly available search results. For each result, the system shall collect only the metadata provided by the search engine: Website Name, Page Title, Search Description (Snippet), and Source URL. The system shall not retrieve or analyze the content of the linked webpages.
- **FR-03**: The system shall analyze all collected search result metadata together to identify the guest's full name, current organization, current professional role, areas of expertise, publicly available achievements, and duplicated information across multiple results.
- **FR-04**: Using the collected search metadata, the system shall generate a structured guest profile containing: Full Name, Current Position, Organization, Professional Biography, Areas of Expertise, Confidence Level, and Sources Used. The professional biography shall summarize only the information supported by the collected search results.
- **FR-05**: If multiple search results contain conflicting information, the system shall prefer information that appears consistently across multiple results, ignore unsupported claims, avoid combining contradictory information, and lower the confidence level when conflicts cannot be resolved.
- **FR-06**: If one or more fields cannot be determined confidently, the system shall leave the field empty, continue generating the remaining profile, and never invent or assume missing information.
- **FR-07**: If the system cannot generate a reliable guest profile, the user shall be asked to manually provide the Professional Biography, Current Position, and Organization.

### Dependencies and Assumptions

- This feature depends on an existing Guest data model to represent the guest identity being searched for.
- The feature assumes a search provider is available that returns publicly accessible metadata only (no login required).
- "Insufficient results" in FR-01 is defined as fewer than 3 returned search results.
- Confidence Level is measured on a three-point scale: High (consistent, corroborated across sources), Medium (some corroboration), Low (single source or conflicting information).

### Business Rules

- Only publicly available search result metadata may be used.
- The system shall not require user login to external websites.
- The system shall not access private or restricted content.
- The system shall not permanently store guest information.
- Retrieved information shall exist only for the current campaign session.

### Key Entities

- **Guest Profile**: Represents the structured information about a guest or speaker. Contains Full Name, Current Position, Organization, Professional Biography, Areas of Expertise, Confidence Level, and Sources Used. Generated from search metadata and used during a single campaign generation session.
- **Search Result**: Represents a single publicly available search result. Contains Website Name, Page Title, Search Description (Snippet), and Source URL. Multiple search results are aggregated and analyzed to produce a Guest Profile.
- **Confidence Level**: Indicates the reliability of the generated profile based on consistency and quantity of search results. Lowered when conflicts are found or minimal data is available.

## Success Criteria

### Measurable Outcomes

- **SC-001**: A structured guest profile is generated for at least 80% of guests with a publicly discoverable online presence.
- **SC-002**: The generated biography accurately represents only the information supported by the collected search results — no invented or assumed details.
- **SC-003**: Duplicate information from multiple search results is merged into a single coherent profile (no repeated entries).
- **SC-004**: Conflicting information does not result in fabricated or misleading content — unresolved conflicts lower the confidence level instead.
- **SC-005**: Manual input is requested only when insufficient public information exists (no false fallbacks for searchable guests).
- **SC-006**: Generated campaign content from retrieved guest profiles is accepted by the marketing organizer without requiring re-research of publicly available information.
