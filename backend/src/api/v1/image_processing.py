"""Image Processing API routes."""

from fastapi import APIRouter, Depends

from src.api.dependencies import AuthenticatedUser, get_authenticated_user
from src.api.response import success_response

router = APIRouter(prefix="/image-processing", tags=["Image Processing"])


@router.post("/validate")
async def validate_image(
    image_url: str,
    user: AuthenticatedUser = Depends(get_authenticated_user),
):
    return success_response(data={"url": image_url, "valid": True}, message="Image validated")
