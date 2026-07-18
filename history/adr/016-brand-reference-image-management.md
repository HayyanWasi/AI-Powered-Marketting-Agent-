# ADR-016: Brand Reference Image Management Strategy

**Status:** Accepted
**Date:** 2026-07-16

## Context

Companies need to associate multiple visual brand assets (logos, color palettes, photography style references) with their profile for AI image generation. Key decisions:
- How to store images (database vs blob storage)?
- How to manage the 1-to-many relationship?
- What operations to support (add/replace/remove/reorder)?
- How to enforce limits and validate content?

## Decision

**Storage Architecture:**
- **Metadata** in Supabase PostgreSQL: `brand_reference_images` table (id, company_profile_id, storage_path, filename, content_type, file_size, sort_order, uploaded_at)
- **Binary content** in Supabase Storage: public bucket, path-based access
- **API returns** presigned/public URLs for image access

**Relationship Model:**
- CompanyProfile (1) ────── (0..6) BrandReferenceImage
- Ordered list via `sort_order` (0-5)
- Individual image operations supported

**API Operations:**
| Operation | Endpoint | Description |
|-----------|----------|-------------|
| Upload | POST /{profile_id}/images | Add image, auto-assign next sort_order |
| List | GET /{profile_id}/images | Return ordered list with URLs |
| Remove | DELETE /{profile_id}/images/{image_id} | Remove, compact sort_order |
| Reorder | PUT /{profile_id}/images/{image_id}/reorder | Change sort_order (0-5) |

**Validation at Upload:**
1. File type: JPEG, PNG, WebP only (MIME + extension check)
2. Resolution: Minimum 1080x1080 (Pillow validation)
3. Profile exists (404 if not)
4. Max 6 images per profile (409 if exceeded)

**Sort Order Management:**
- On upload: assign next available (COUNT existing)
- On remove: compact remaining (0,1,2... no gaps)
- On reorder: validate 0-5, swap with occupant, maintain uniqueness

## Consequences

**Positive:**
- Separation of metadata (queryable) from binary (streamable)
- Efficient listing without downloading binaries
- Granular operations: change one image without re-uploading all
- Deterministic priority via sort_order for generation prompts
- Hard limit (6) prevents storage abuse
- Resolution check ensures generation quality
- Public bucket enables direct CDN access

**Negative:**
- Two-system consistency (DB + Storage) - orphaned blobs possible
- Sort order compaction on delete is O(n) but n<=6
- Reorder requires swap logic (not simple move)
- No image replacement endpoint (delete + upload)
- Storage lifecycle management needed for deleted profiles

## Alternatives Considered

1. **Base64-encoded images in profile record**
   - Rejected: Bloats DB, kills query performance, no streaming, no CDN

2. **Single all-or-nothing image set update**
   - Rejected: Forces re-upload of all images to change one; poor UX

3. **Unordered set (no sort_order)**
   - Rejected: Generation benefits from deterministic priority (logo first)

4. **No limit on image count**
   - Rejected: Unbounded storage growth; 6 provides variety without excess

5. **Image replacement endpoint (PUT /images/{id})**
   - Deferred: Delete + upload achieves same; can add if UX demands

## References

- Plan.md: Service Contracts (Associate Brand Reference Images)
- Research.md: Research 2 (Best Practices for Managing Multiple Brand Reference Images)
- Data-model.md: BrandReferenceImage entity, Relationships, Validation Rules
- Contracts/openapi.yaml: Brand image endpoints, schemas, error codes
- ADR-014: Company Profile Service as Bounded Context
- ADR-015: Company Profile Data Model & Validation Rules