"""AI Generation Engine API routes — delegates to AIGenerationService."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.api.dependencies import AuthenticatedUser, get_authenticated_user
from src.modules.ai_generation.services.ai_generation_service import AIGenerationService

router = APIRouter(tags=["AI Generation"])


async def _get_generation_service() -> AIGenerationService:
    return AIGenerationService()


class GenerationContext(BaseModel):
    campaign_context: dict = Field(
        ...,
        description="Campaign parameters including goals, target audience segments, budget, timeline",
    )
    company_profile: dict = Field(
        ..., description="Company brand information, voice, values, positioning"
    )
    audience: dict = Field(
        ..., description="Target audience demographics, interests, pain points, buying behavior"
    )
    platforms: list[str] = Field(
        ..., description="List of target platforms (e.g., LinkedIn, Instagram, Twitter)"
    )
    brand_guidelines: dict = Field(
        ..., description="Brand voice tone, style guidelines, logo specifications, color palette"
    )
    reference_materials: list[dict] = Field(
        ..., description="Relevant assets, benchmarks, competitor examples, previous campaigns"
    )
    user_intent: Optional[dict] = Field(
        None, description="Additional instructions for specific content variations or emphasis"
    )


class ValidationRequest(BaseModel):
    artifacts: dict


class RegenerationRequest(BaseModel):
    existing_context: dict
    user_instructions: Optional[dict] = Field(
        None, description="Instructions for what aspects to regenerate"
    )


@router.post("/generate", status_code=status.HTTP_201_CREATED)
async def generate_full_campaign(
    request: GenerationContext,
    generation_service: AIGenerationService = Depends(_get_generation_service),
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict:
    """Generate a complete marketing campaign: strategy, copy, image prompts, and images."""
    try:
        result = await generation_service.generate(request.model_dump())
        return {"status": "success", "artifacts": result, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Campaign generation failed: {str(e)}"
        )


@router.post("/regenerate/text", status_code=status.HTTP_200_OK)
async def regenerate_text_content(
    request: RegenerationRequest,
    generation_service: AIGenerationService = Depends(_get_generation_service),
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict:
    """Regenerate text content (copy) while preserving approved strategy and existing images."""
    try:
        result = await generation_service.regenerate_text(
            request.existing_context, request.user_instructions
        )
        return {"status": "success", "artifacts": result, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Text regeneration failed: {str(e)}"
        )


@router.post("/regenerate/image", status_code=status.HTTP_200_OK)
async def regenerate_images(
    request: RegenerationRequest,
    generation_service: AIGenerationService = Depends(_get_generation_service),
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict:
    """Regenerate campaign images while preserving approved strategy and existing copy."""
    try:
        result = await generation_service.regenerate_image(
            request.existing_context, request.user_instructions
        )
        return {"status": "success", "artifacts": result, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Image regeneration failed: {str(e)}"
        )


@router.post("/regenerate/strategy", status_code=status.HTTP_200_OK)
async def regenerate_strategy(
    request: GenerationContext,
    generation_service: AIGenerationService = Depends(_get_generation_service),
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict:
    """Regenerate campaign strategy and all dependent artifacts."""
    try:
        result = await generation_service.generate(request.model_dump())
        return {"status": "success", "artifacts": result, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Strategy regeneration failed: {str(e)}",
        )


@router.post("/validate", status_code=status.HTTP_200_OK)
async def validate_artifacts(
    request: ValidationRequest,
    generation_service: AIGenerationService = Depends(_get_generation_service),
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict:
    """Validate all generated campaign artifacts against business rules and platform requirements."""
    try:
        result = await generation_service.validate_all_artifacts(request.artifacts)
        return {"status": "success", "validation": result, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Validation failed: {str(e)}"
        )


@router.post("/health")
async def health_check() -> dict:
    """Health check endpoint to verify API status."""
    return {
        "status": "healthy",
        "service": "AI Generation Engine API",
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/info")
async def service_info() -> dict:
    """Return service information and capabilities."""
    return {
        "service": "AI Generation Engine API",
        "version": "1.0.0",
        "description": "Deterministic marketing campaign generation service",
        "capabilities": [
            "Complete campaign generation (strategy, copy, images)",
            "Text-only content regeneration",
            "Image-only content regeneration",
            "Strategy revision and regeneration",
            "Comprehensive content validation",
            "Platform-specific formatting",
            "Brand alignment validation",
        ],
        "supported_operations": [
            "POST /generate",
            "POST /regenerate/text",
            "POST /regenerate/image",
            "POST /regenerate/strategy",
            "POST /validate",
            "POST /health",
            "GET /info",
        ],
        "modules": [
            "Context Builder",
            "Strategy Planner",
            "Copy Generator",
            "Image Prompt Editor",
            "Image Generator",
            "Validator",
            "Intent Analyzer",
        ],
        "timestamp": datetime.now().isoformat(),
    }
