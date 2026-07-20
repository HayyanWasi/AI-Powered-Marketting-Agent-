# Feature Specification: Pollinations AI Brand Image Generation

**Feature Branch**: `007-pollinations-brand-images`  
**Created**: 2026-07-15  
**Status**: Draft  
**Input**: User description: "Integrate Pollinations AI to generate campaign images using their API (https://image.pollinations.ai/prompt/) with the "kontext" model. Use company profile context for brand style conditioning. Generate campaign images with brand style. Return image URL. Handle errors with retries and fallback. Return image URL for frontend use."
## User Scenarios & Testing *(mandatory)*

### User Story 1 - Generate a Brand-Aligned Campaign Image (Priority: P1)

As a marketing organizer,

I want the system to generate a campaign image that reflects my company's visual identity,

so that I can quickly create professional marketing materials without designing them manually.

**Why this priority:** Generating visually consistent campaign images is the primary purpose of this feature and enables the overall campaign generation workflow.

**Independent Test:** Can be fully tested by providing a valid campaign image request and verifying that a campaign image is successfully generated and made available for campaign preview.

#### Acceptance Scenarios

1. **Given** a valid campaign image request and available company brand information,  
   **When** image generation completes successfully,  
   **Then** the system shall generate a campaign image that reflects both the campaign intent and the company's visual identity.

2. **Given** no company brand information is available,  
   **When** image generation completes successfully,  
   **Then** the system shall generate a campaign image using only the campaign image prompt and notify the user that brand styling could not be applied.

3. **Given** a generated campaign image satisfies all campaign validation requirements,  
   **When** campaign generation is completed,  
   **Then** the image shall be available for campaign preview and human review.

---

### User Story 2 - Handle Image Generation Failures (Priority: P1)

As a marketing organizer,

I want the system to recover gracefully from image generation failures,

so that temporary issues do not interrupt campaign creation.

**Why this priority:** Reliable image generation is essential to maintaining a smooth campaign creation experience.

**Independent Test:** Can be tested by simulating image generation failures and verifying that the user receives appropriate feedback and can retry the request.

#### Acceptance Scenarios

1. **Given** image generation cannot be completed,  
   **When** the generation process finishes,  
   **Then** the system shall notify the user that image generation failed and allow the request to be retried.

2. **Given** image generation succeeds after a temporary failure,  
   **When** processing completes,  
   **Then** the generated campaign image shall continue through the normal campaign workflow.

3. **Given** image generation cannot be completed after all recovery attempts,  
   **When** the generation process ends,  
   **Then** the campaign shall remain incomplete until a valid campaign image is successfully generated.

---

### User Story 3 - Maintain Company Brand Consistency (Priority: P2)

As a marketing organizer,

I want the system to automatically apply my company's branding during image generation,

so that every campaign maintains a consistent visual identity without additional manual effort.

**Why this priority:** Consistent branding improves campaign quality and reduces manual prompt customization.

**Independent Test:** Can be tested by generating campaign images for multiple companies and verifying that each generated image reflects the corresponding company branding.

#### Acceptance Scenarios

1. **Given** company brand information is available,  
   **When** a campaign image is generated,  
   **Then** the system shall apply the available brand information during image generation.

2. **Given** multiple company reference images are available,  
   **When** image generation begins,  
   **Then** the system shall use the available reference images to improve brand consistency.

3. **Given** company brand information is incomplete,  
   **When** image generation begins,  
   **Then** the system shall use all available brand information without preventing image generation.

### Edge Cases

- Company brand information does not exist.
- Company brand information is incomplete (e.g., missing brand guidelines or reference images).
- Multiple company reference images represent inconsistent visual styles.
- The campaign image prompt is empty or lacks sufficient information to generate a meaningful image.
- The requested campaign contains content that cannot be used to generate an image.
- The generated campaign image does not satisfy the required campaign image validation criteria.
- Image generation cannot be completed due to a temporary service interruption.
- Image generation cannot be completed after all recovery attempts.
- The user retries image generation after a previous failure.
- The user requests a new image for the same campaign after rejecting the previous one during human review.

---

## Requirements *(mandatory)*

## Functional Requirements

### FR-01: Campaign Image Request

The system shall accept a campaign image generation request containing:

- Campaign image prompt
- Selected company
- Campaign context

The campaign image prompt shall be produced by the Campaign Generation workflow before image generation begins.

---

### FR-02: Brand Information Usage

The system shall use the selected company's available brand information to maintain visual consistency throughout the generated campaign image.

Brand information includes:

- Company brand guidelines
- Company reference images

If multiple reference images are available, the system shall use all available reference images during image generation.

---

### FR-03: Missing Brand Information

If no company brand information is available, the system shall continue image generation using only the campaign image prompt.

The system shall notify the user that brand-specific styling could not be applied.

---

### FR-04: Campaign Image Generation

The system shall generate a single campaign image representing the campaign described by the provided image prompt.

The generated image shall reflect the campaign intent while incorporating available company brand information.

---

### FR-05: Image Validation

The system shall verify that every generated image satisfies the minimum campaign image requirements before making it available for campaign preview.

Images that fail validation shall not be presented for campaign review.

---

### FR-06: Campaign Preview

For every successfully validated image, the system shall make the generated campaign image available for user preview and human review before publishing.

---

### FR-07: Image Generation Failure

If image generation cannot be completed successfully, the system shall:

- Notify the user that image generation failed.
- Prevent campaign approval until a valid image is available.
- Allow the user to retry image generation.

---

### FR-08: Brand Integrity

The system shall treat all company brand information as read-only input.

The image generation process shall never modify, overwrite, or permanently alter any stored company brand information.

## Business Rules

### BR-01: Brand Information

Brand information consists of:

- Company Brand Guidelines
- Company Reference Images

The system shall use available brand information whenever generating campaign images.

---

### BR-02: Image Ownership

Each image generation request shall produce one campaign image for the current campaign.

---

### BR-03: Session Scope

Generated campaign images shall remain available throughout the current campaign workflow until the campaign is either approved, rejected, or the session ends.

---

### BR-04: Read-Only Brand Assets

Company brand information shall be treated as read-only input and shall never be modified by the image generation feature.


### Key Entities

- **CompanyProfile**: Represents a company's brand identity including brand colors (hex codes), typography preferences, logo URL/description, brand personality descriptors, style guidelines, and industry category
- **CampaignImageRequest**: Represents a request to generate a campaign image, containing company_profile_id and campaign_prompt
- **CampaignImageResponse**: Represents the response containing the generated image_url and optional metadata (model used, generation time, fallback_used flag)
- **BrandStyleContext**: Derived entity containing extracted brand attributes formatted for prompt conditioning (color palette, style descriptors, logo reference)

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 95% of image generation requests return a valid image URL within 30 seconds (including retries)
- **SC-002**: Fallback mechanism activates in <5% of requests (indicating reliable primary API)
- **SC-003**: 90% of generated images are rated "on-brand" by users in post-generation surveys
- **SC-004**: API response time (excluding Pollinations generation time) is under 500ms p95
- **SC-005**: Zero unhandled exceptions - all error paths return structured error responses
- **SC-006**: Retry logic successfully recovers from transient failures in >80% of retry attempts

---

## Assumptions & Clarifications

1. **Pollinations API**: Assumes the Pollinations API at `https://image.pollinations.ai/prompt/{prompt}?model=kontext` is publicly accessible and doesn't require API key authentication (based on public documentation)
2. **Company Profile Storage**: Assumes company profiles are already stored in Supabase `company_profiles` table (from feature 002) with brand fields populated
3. **Brand Fields**: Assumes company profile includes at minimum: `brand_colors` (JSON array of hex codes), `brand_personality` (text), `style_guide` (text), `logo_url` (optional), `typography_style` (optional)
4. **Pollinations Prompt Format**: Assumes Pollinations accepts natural language prompts with model parameter; brand conditioning is achieved through prompt engineering
5. **Fallback Images**: Fallback will use a Pollinations-generated branded placeholder (e.g., `https://image.pollinations.ai/prompt/placeholder%20with%20brand%20colors%20{colors}?model=kontext`) or a static branded placeholder
6. **Rate Limits**: Assumes Pollinations has reasonable rate limits; implements respectful backoff
7. **No Authentication**: Assumes this service runs in a trusted backend environment; authentication/authorization handled at API gateway level
8. **Image Persistence**: Generated images are served directly from Pollinations CDN; no local storage/download required

---

## Dependencies

- **Supabase**: Company profile storage (feature 002)
- **Pollinations AI API**: External image generation service
- **Session Cache** (feature 003): For potential request-scoped caching
- **LLM Service** (feature 006): Potential future use for prompt enhancement

---

## Out of Scope

- Image storage/persistence in Supabase Storage (Pollinations URLs are used directly)
- User authentication/authorization (handled at API gateway)
- Campaign management CRUD (separate feature)
- Batch/multiple image generation in single request
- Image editing/variations (single generation per request)
- A/B testing of generated images
- Custom model fine-tuning