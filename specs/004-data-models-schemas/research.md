# Research: Data Models & Schemas

**Phase**: 0 — Outline & Research
**Branch**: `004-data-models-schemas`
**Date**: 2026-07-14

## Unknowns Resolution

No NEEDS CLARIFICATION markers existed in the spec. The following design decisions document the choices made during planning.

### D1: Dual Representation Pattern

**Decision**: Each entity will have both a `@dataclass` (internal representation) and one or more Pydantic `BaseModel` subclasses (API layer).

**Rationale**: Existing `company.py` already follows this pattern — a `CompanyProfile` dataclass for internal logic and `CompanyProfileCreate`/`CompanyProfileUpdate`/`CompanyProfileResponse` Pydantic models for API validation and serialization. Reusing this pattern ensures consistency across all three entities.

**Alternatives considered**:
- Single Pydantic model for all purposes — simpler but loses separation between internal state and API contract
- Single dataclass with manual validation — misses automatic serialization/error messages from Pydantic

### D2: Campaign Type Validation

**Decision**: Campaign type will be a plain string field with Pydantic validation checking against a known set of campaign types.

**Rationale**: The constitution mentions "6 campaign type agents" but the exact list is not finalized for this model layer. A validated string approach allows adding types without changing the data model — validation at the API boundary ensures only recognized types pass through.

**Alternatives considered**:
- `StrEnum` class — more rigid, requires code change for every new type
- Literal type — good for type checking but not for dynamic configuration

### D3: Campaign Status State Machine

**Decision**: Campaign status as a validated string field with allowed values: `draft`, `published`, `archived`.

**Rationale**: Covers the common campaign lifecycle. State transition validation will be enforced at the service layer, not in the model itself. The model merely validates that the status value is one of the allowed set.

**Alternatives considered**:
- Full state machine in model — over-engineering for V1 (KISS)
- No validation — risks invalid states persisting

### D4: URL Validation

**Decision**: Use Pydantic's built-in `HttpUrl` type for image URL fields, which validates URL format and scheme.

**Rationale**: Pydantic provides first-class URL validation that produces clear error messages for malformed URLs. Already available in the existing dependency stack.

**Alternatives considered**:
- Custom regex — reinventing the wheel
- `str` without validation — fails to catch malformed URLs early

### D5: Existing Company Model Compatibility

**Decision**: Keep existing `company.py` as-is. Guest and Campaign will follow the identical naming pattern (`Guest`/`GuestCreate`/`GuestUpdate`/`GuestResponse`, `Campaign`/`CampaignCreate`/`CampaignUpdate`/`CampaignResponse`).

**Rationale**: The existing company model already implements the spec's requirements correctly. Changing it would introduce risk without benefit.

## Dependency Analysis

### Internal Dependencies
- None — models layer has zero internal dependencies within the backend

### External Dependencies
- `pydantic` (already in `pyproject.toml`)
- `dataclasses` (stdlib, no import needed in Python 3.13)

### Integration Patterns
- All models importable via `backend/src/models/__init__.py`
- FastAPI route handlers use Pydantic schemas as request/response types
- Internal services use dataclasses
- No REST endpoints defined here — models are consumed by other features
