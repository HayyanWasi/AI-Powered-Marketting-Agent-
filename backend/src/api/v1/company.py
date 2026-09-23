"""Company Profile API routes — delegates to services/company/*.py."""

import io
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from PIL import Image
from pydantic import BaseModel

from src.api.dependencies import AuthenticatedUser, get_authenticated_user
from src.models.company import CompanyProfileCreate, CompanyProfileUpdate
from src.repositories.base import BaseRepository
from src.services.campaign_context_service import owned_profiles
from src.services.company.campaign_lookup_service import CampaignLookupService
from src.services.company.create_company_service import CreateCompanyService
from src.services.company.delete_company_service import DeleteCompanyService
from src.services.company.get_company_service import GetCompanyService
from src.services.company.list_company_service import ListCompanyService
from src.services.company.update_company_service import UpdateCompanyService
from src.services.supabase import (
    IMAGE_TYPES,
    MAX_IMAGE_SIZE,
    MAX_IMAGES,
    NotFoundError,
    SupabaseService,
)

router = APIRouter(prefix="/company", tags=["Company"])


async def _get_supabase_service(user: AuthenticatedUser = Depends(get_authenticated_user)) -> SupabaseService:
    return SupabaseService(user_id=user.id)


async def _get_create_service(user: AuthenticatedUser = Depends(get_authenticated_user)) -> CreateCompanyService:
    return CreateCompanyService(repository=owned_profiles(user.id))


async def _get_update_service(user: AuthenticatedUser = Depends(get_authenticated_user)) -> UpdateCompanyService:
    return UpdateCompanyService(repository=owned_profiles(user.id))


async def _get_get_service(user: AuthenticatedUser = Depends(get_authenticated_user)) -> GetCompanyService:
    return GetCompanyService(repository=owned_profiles(user.id))


async def _get_list_service(user: AuthenticatedUser = Depends(get_authenticated_user)) -> ListCompanyService:
    return ListCompanyService(repository=owned_profiles(user.id))


async def _get_delete_service(user: AuthenticatedUser = Depends(get_authenticated_user)) -> DeleteCompanyService:
    return DeleteCompanyService(repository=owned_profiles(user.id), supabase=SupabaseService(user_id=user.id))


async def _get_campaign_lookup_service(user: AuthenticatedUser = Depends(get_authenticated_user)) -> CampaignLookupService:
    return CampaignLookupService(repository=owned_profiles(user.id))


@router.post("", status_code=201)
async def create_profile(
    body: CompanyProfileCreate,
    create_service: CreateCompanyService = Depends(_get_create_service),
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, Any]:
    """Create a new company profile."""
    try:
        profile = create_service.execute(
            company_name=body.company_name.strip(),
            brand_guidelines=body.brand_guidelines.strip(),
            brand_tone=body.brand_tone.strip() if body.brand_tone else None,
        )
        return {
            "id": profile.id,
            "company_name": profile.company_name,
            "brand_guidelines": profile.brand_guidelines,
            "brand_tone": profile.brand_tone,
            "reference_image_urls": profile.reference_image_urls,
            "default_linkedin_account_id": profile.default_linkedin_account_id,
            "created_at": profile.created_at,
            "updated_at": profile.updated_at,
        }
    except ValueError as e:
        detail = str(e)
        if "already exists" in detail.lower():
            raise HTTPException(status_code=409, detail=detail)
        raise HTTPException(status_code=422, detail=detail)


@router.get("")
async def list_profiles(
    list_service: ListCompanyService = Depends(_get_list_service),
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> list[dict[str, Any]]:
    """List all company profiles."""
    return list_service.execute()


@router.get("/{profile_id}")
async def get_profile(
    profile_id: str,
    get_service: GetCompanyService = Depends(_get_get_service),
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, Any]:
    """Get a company profile by ID."""
    try:
        UUID(profile_id)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid profile ID format: {profile_id}")
    try:
        return get_service.execute(profile_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{profile_id}")
async def update_profile(
    profile_id: str,
    body: CompanyProfileUpdate,
    update_service: UpdateCompanyService = Depends(_get_update_service),
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, Any]:
    """Update a company profile."""
    data = body.model_dump(exclude_none=True)
    try:
        profile = update_service.execute(profile_id, data)
        return {
            "id": profile.id,
            "company_name": profile.company_name,
            "brand_guidelines": profile.brand_guidelines,
            "brand_tone": profile.brand_tone,
            "reference_image_urls": profile.reference_image_urls,
            "default_linkedin_account_id": profile.default_linkedin_account_id,
            "created_at": profile.created_at,
            "updated_at": profile.updated_at,
        }
    except ValueError as e:
        detail = str(e)
        if "not found" in detail.lower() or "deleted" in detail.lower():
            raise HTTPException(status_code=404, detail=detail)
        if "already exists" in detail.lower() or "already in use" in detail.lower():
            raise HTTPException(status_code=409, detail=detail)
        raise HTTPException(status_code=422, detail=detail)


class SetBrandLinkedInAccountRequest(BaseModel):
    """Set or clear a brand's default LinkedIn publishing account.

    ``account_id`` is the internal ``linkedin_accounts.id`` (never a raw Unipile
    id supplied blindly). ``None`` clears the brand's default account.
    """

    account_id: str | None = None


@router.put("/{profile_id}/linkedin-account")
async def set_brand_linkedin_account(
    profile_id: str,
    body: SetBrandLinkedInAccountRequest,
    get_service: GetCompanyService = Depends(_get_get_service),
    update_service: UpdateCompanyService = Depends(_get_update_service),
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, Any]:
    """Set (or clear) the brand's default LinkedIn account.

    Ownership is enforced server-side on BOTH sides: the brand must belong to the
    caller (owned repository), and the LinkedIn account must be a row the caller
    owns and that is currently ``connected``. A foreign, unknown, or disconnected
    account is rejected and nothing is changed. Passing ``account_id: null``
    clears the association.
    """
    try:
        UUID(profile_id)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid profile ID format: {profile_id}")

    # 1. Verify the brand exists AND belongs to this user (owned repository).
    try:
        get_service.execute(profile_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    account_id = (body.account_id or "").strip() or None

    # 2. When setting (not clearing), the account must be owned + connected.
    if account_id is not None:
        try:
            UUID(account_id)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid LinkedIn account id format.")
        repo = BaseRepository("linkedin_accounts")
        try:
            res = (
                repo.client.table("linkedin_accounts")
                .select("*")
                .eq("id", account_id)
                .eq("user_id", str(user.id))
                .limit(1)
                .execute()
            )
            rows = res.data or []
        except Exception as e:  # noqa: BLE001 - surfaced as 503
            raise HTTPException(
                status_code=503,
                detail=f"linkedin_accounts table not available. Run migration first. ({e})",
            ) from e
        if not rows:
            # Not owned by this user, or does not exist. Never reveal which.
            raise HTTPException(
                status_code=404,
                detail="LinkedIn account not found for your account.",
            )
        if rows[0].get("status") != "connected":
            raise HTTPException(
                status_code=409,
                detail="That LinkedIn account is not connected. Reconnect it before assigning it to a brand.",
            )

    # 3. Persist on the owned brand (user-scoped update; cross-user cannot write).
    try:
        profile = update_service.execute(
            profile_id, {"default_linkedin_account_id": account_id}
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {
        "id": profile.id,
        "company_name": profile.company_name,
        "brand_guidelines": profile.brand_guidelines,
        "brand_tone": profile.brand_tone,
        "reference_image_urls": profile.reference_image_urls,
        "default_linkedin_account_id": profile.default_linkedin_account_id,
        "created_at": profile.created_at,
        "updated_at": profile.updated_at,
    }


@router.get("/{profile_id}/brand-info")
async def get_brand_info(
    profile_id: str,
    campaign_lookup_service: CampaignLookupService = Depends(_get_campaign_lookup_service),
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, Any]:
    """Get brand info for campaign generation (requires a complete profile)."""
    try:
        return campaign_lookup_service.execute(profile_id)
    except ValueError as e:
        if "incomplete" in str(e).lower():
            raise HTTPException(status_code=422, detail=str(e))
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{profile_id}", status_code=204)
async def delete_profile(
    profile_id: str,
    delete_service: DeleteCompanyService = Depends(_get_delete_service),
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> None:
    """Delete a company profile (rejected if referenced by active campaigns)."""
    try:
        delete_service.execute(profile_id)
    except ValueError as e:
        detail = str(e)
        if "campaign" in detail.lower() or "active" in detail.lower():
            raise HTTPException(status_code=409, detail=detail)
        raise HTTPException(status_code=404, detail=detail)


@router.post("/{profile_id}/brand-images")
async def upload_brand_images(
    profile_id: str,
    images: list[UploadFile] = File(...),
    service: SupabaseService = Depends(_get_supabase_service),
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, Any]:
    """Upload one or more brand reference images for a company profile."""
    if len(images) > MAX_IMAGES:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {MAX_IMAGES} images allowed per upload",
        )

    try:
        service.get_profile(profile_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Company profile not found")

    urls: list[str] = []
    failed: list[dict[str, str]] = []

    for image in images:
        content_type = image.content_type or "application/octet-stream"
        if content_type not in IMAGE_TYPES:
            failed.append(
                {
                    "file": image.filename or "unknown",
                    "error": f"Unsupported format: {content_type}. Accepted: JPEG, PNG, WebP",
                }
            )
            continue

        contents = await image.read()
        if len(contents) > MAX_IMAGE_SIZE:
            failed.append(
                {
                    "file": image.filename or "unknown",
                    "error": f"File too large (max {MAX_IMAGE_SIZE // (1024 * 1024)}MB)",
                }
            )
            continue

        try:
            img = Image.open(io.BytesIO(contents))
            img.verify()
        except Exception:
            failed.append(
                {"file": image.filename or "unknown", "error": "Invalid or corrupt image file"}
            )
            continue

        with NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(contents)
            tmp_path = tmp.name

        try:
            url = service.upload_image(Path(tmp_path), content_type, profile_id)
            urls.append(url)
        except Exception as e:
            failed.append({"file": image.filename or "unknown", "error": str(e)})
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    current = service.get_profile(profile_id)
    existing_urls = current.get("reference_image_urls", [])
    all_urls = existing_urls + urls
    service.update_profile(profile_id, {"reference_image_urls": all_urls})

    return {"urls": urls, "failed": failed, "total": len(existing_urls) + len(urls)}


@router.delete("/{profile_id}/brand-images/{image_index}")
async def remove_brand_image(
    profile_id: str,
    image_index: int,
    service: SupabaseService = Depends(_get_supabase_service),
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, Any]:
    """Remove a brand image at the given index."""
    try:
        profile = service.get_profile(profile_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Company profile not found")

    urls = profile.get("reference_image_urls", [])
    if image_index < 0 or image_index >= len(urls):
        raise HTTPException(
            status_code=404,
            detail=f"Image at index {image_index} not found. Profile has {len(urls)} images.",
        )

    urls.pop(image_index)
    service.update_profile(profile_id, {"reference_image_urls": urls})

    return {"removed": True, "remaining": len(urls)}


@router.post("/{profile_id}/brand-images/{image_index}/replace")
async def replace_brand_image(
    profile_id: str,
    image_index: int,
    image: UploadFile = File(...),
    service: SupabaseService = Depends(_get_supabase_service),
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, Any]:
    """Replace a brand image at the given index."""
    try:
        profile = service.get_profile(profile_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Company profile not found")

    urls = profile.get("reference_image_urls", [])
    if image_index < 0 or image_index >= len(urls):
        raise HTTPException(
            status_code=404,
            detail=f"Image at index {image_index} not found. Profile has {len(urls)} images.",
        )

    content_type = image.content_type or "application/octet-stream"
    if content_type not in IMAGE_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported format: {content_type}. Accepted: JPEG, PNG, WebP",
        )

    contents = await image.read()
    if len(contents) > MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=422,
            detail=f"File too large (max {MAX_IMAGE_SIZE // (1024 * 1024)}MB)",
        )

    try:
        img = Image.open(io.BytesIO(contents))
        img.verify()
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid or corrupt image file")

    with NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        new_url = service.upload_image(Path(tmp_path), content_type, profile_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    urls[image_index] = new_url
    service.update_profile(profile_id, {"reference_image_urls": urls})

    return {"url": new_url, "index": image_index, "total": len(urls)}


@router.put("/{profile_id}/brand-images/reorder")
async def reorder_brand_images(
    profile_id: str,
    body: dict[str, Any],
    service: SupabaseService = Depends(_get_supabase_service),
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, Any]:
    """Reorder brand images according to the given index order."""
    new_order: list[int] | None = body.get("order")
    if not new_order:
        raise HTTPException(
            status_code=422, detail="'order' field with array of indices is required"
        )

    try:
        profile = service.get_profile(profile_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Company profile not found")

    urls = profile.get("reference_image_urls", [])
    if sorted(new_order) != list(range(len(urls))):
        raise HTTPException(
            status_code=422,
            detail=f"Order must contain each index 0-{len(urls) - 1} exactly once",
        )

    reordered = [urls[i] for i in new_order]
    service.update_profile(profile_id, {"reference_image_urls": reordered})

    return {"reordered": True, "total": len(reordered)}
