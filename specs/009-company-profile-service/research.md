# Research: Company Profile Service

## Research 1: Required Company Information for Brand-Consistent AI Campaign Generation

### Decision
Store company name, brand guidelines text, brand tone, and up to six brand reference images as the company profile data payload for campaign generation.

### Rationale
- **Brand guidelines text** provides explicit communication style rules (voice, formatting, key messages) that the LLM can consume as system-prompt context.
- **Brand tone** allows finer-grained stylistic control beyond guidelines (e.g., "professional but approachable" or "playful and energetic").
- **Brand reference images** give the image generation model concrete visual examples to emulate (logo style, color palette, imagery type).
- **Company name** is the primary human-readable identifier and uniqueness constraint.

### Alternatives Considered
- Storing only company name and relying on the LLM to infer brand identity from context — rejected: too unreliable for consistent output.
- Auto-generating brand guidelines from uploaded images — explicitly scoped out as a non-goal.
- Using a flexible JSON blob instead of structured fields — rejected: structured fields enable validation and targeted updates.

---

## Research 2: Best Practices for Managing Multiple Brand Reference Images per Company

### Decision
Treat brand reference images as a 1-to-many relationship from Company Profile to Brand Reference Image. Images are uploaded and stored in persistent blob storage. The profile maintains an ordered list of up to six image references. Users can add, replace, and remove individual images.

### Rationale
- Separation of image metadata from the image binary enables efficient listing (no need to download all images to see what's associated).
- Ordered list lets campaign generation prioritize the most representative images.
- A hard limit of six prevents unbounded storage growth while providing sufficient variety.
- Individual add/replace/remove operations give granular control without requiring full-resubmission of all images.

### Alternatives Considered
- Storing images as base64-encoded strings in the profile record — rejected: bloats database, kills query performance, no streaming.
- Single all-or-nothing image set update — rejected: forces re-upload of all images to change one.
- No ordering (unordered set) — rejected: campaign generation benefits from deterministic priority.

---

## Research 3: Business Rules for Validating Company Profiles Before Campaign Generation

### Decision
A company profile is considered "complete" (eligible for campaign generation) when it has a non-empty company name and non-empty brand guidelines text. Brand reference images and brand tone are optional.

### Rationale
- Text-based brand guidelines are sufficient for the LLM to generate on-brand copy.
- Images enhance visual consistency but are not strictly required for text-only campaigns.
- A hard minimum (name + guidelines) prevents incomplete profiles from producing off-brand output.
- Adding more required fields before a profile is "complete" would block valid use cases (e.g., text-only campaigns).

### Validation Rules Summary
| Rule | Enforcement |
|------|-------------|
| Company name required | On create and update |
| Company name unique | On create and update |
| Brand guidelines required | On create and update (must be non-empty) |
| Max 6 reference images | On image upload/associate |
| Images must be valid format | On image upload |
| Profile complete check | On campaign generation request |

### Alternatives Considered
- Requiring at least one brand reference image for completeness — rejected: text-only campaigns should not be blocked.
- Requiring brand tone for completeness — rejected: guidelines text is sufficient; tone is a refinement.
- Postponing validation to campaign generation time with inline errors — rejected: fail-fast principle; validation should happen at profile update time, not at generation time.
