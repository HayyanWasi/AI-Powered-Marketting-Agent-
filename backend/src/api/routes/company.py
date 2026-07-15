import io
import logging
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from fastapi import APIRouter, File, UploadFile, HTTPException
from PIL import Image

from src.models.company import CompanyProfileCreate, CompanyProfileUpdate
from src.services.supabase import (
    DuplicateCompanyError,
    NotFoundError,
    SupabaseService,
    IMAGE_TYPES,
    MAX_IMAGE_SIZE,
    MAX_IMAGES,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/company", tags=["company"])
service = SupabaseService()


@router.post("", status_code=201)
async def create_profile(body: CompanyProfileCreate) -> dict[str, Any]:
    try:
        result = service.create_profile(body.name.strip(), body.tone.strip())
        return result  # type: ignore[no-any-return]
    except DuplicateCompanyError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/{profile_id}")
async def get_profile(profile_id: str) -> dict[str, Any]:
    try:
        return service.get_profile(profile_id)  # type: ignore[no-any-return]
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{profile_id}")
async def update_profile(profile_id: str, body: CompanyProfileUpdate) -> dict[str, Any]:
    data = body.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(status_code=422, detail="No fields to update")
    try:
        return service.update_profile(profile_id, data)  # type: ignore[no-any-return]
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{profile_id}", status_code=204)
async def delete_profile(profile_id: str) -> None:
    try:
        service.delete_profile(profile_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{profile_id}/brand-images")
async def upload_brand_images(
    profile_id: str, images: list[UploadFile] = File(...)
) -> dict[str, Any]:
    if len(images) > MAX_IMAGES:
        raise HTTPException(status_code=400, detail=f"Maximum {MAX_IMAGES} images allowed")

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
                    "error": f"Unsupported format: {content_type}",
                }
            )
            continue

        contents = await image.read()
        if len(contents) > MAX_IMAGE_SIZE:
            failed.append(
                {
                    "file": image.filename or "unknown",
                    "error": f"File too large (max {MAX_IMAGE_SIZE // (1024*1024)}MB)",
                }
            )
            continue

        try:
            img = Image.open(io.BytesIO(contents))
            img.verify()
        except Exception:
            failed.append({"file": image.filename or "unknown", "error": "Invalid image file"})
            continue

        with NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(contents)
            tmp_path = tmp.name

        try:
            url = service.upload_image(Path(tmp_path), content_type)
            urls.append(url)
        except Exception as e:
            failed.append({"file": image.filename or "unknown", "error": str(e)})
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    current = service.get_profile(profile_id)
    existing_urls = current.get("reference_image_urls", [])
    all_urls = existing_urls + urls
    service.update_profile(profile_id, {"reference_image_urls": all_urls})

    return {"urls": urls, "failed": failed}
