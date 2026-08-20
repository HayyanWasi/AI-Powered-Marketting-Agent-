"""AI Generation Engine API endpoints for FastAPI."""

from datetime import datetime

from backend.src.modules.ai_generation.services.ai_generation_service import AIGenerationService
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

router = APIRouter()


# Pydantic models for API request/response
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
    user_intent: dict | None = Field(
        None, description="Additional instructions for specific content variations or emphasis"
    )


class StrategyRequest(BaseModel):
    generation_context: GenerationContext


class CopyRequest(BaseModel):
    strategy_artifact: dict
    platform: str
    context: dict | None = Field(None, description="Context for regeneration if applicable")


class ImagePromptRequest(BaseModel):
    strategy_artifact: dict
    copy_artifact: dict
    platform: str


class ImageRequest(BaseModel):
    image_prompt_artifact: dict


class ValidationRequest(BaseModel):
    artifacts: dict


class RegenerationRequest(BaseModel):
    existing_context: dict
    user_instructions: dict | None = Field(
        None, description="Instructions for what aspects to regenerate"
    )


# API Endpoints
@router.post("/generate", status_code=status.HTTP_201_CREATED)
async def generate_full_campaign(
    request: GenerationContext, generation_service: AIGenerationService = Depends()
) -> dict:
    """
    Generate a complete marketing campaign including strategy, copy, image prompts, and campaign images.

    **Purpose**: Generate all campaign artifacts in one API call
    **Input**: Complete generation context with all required fields
    **Output**: Complete campaign artifacts (strategy, copy, images) and validation results
    """
    try:
        result = await generation_service.generate(request.dict())
        return {"status": "success", "artifacts": result, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Campaign generation failed: {str(e)}"
        )


@router.post("/regenerate/text", status_code=status.HTTP_200_OK)
async def regenerate_text_content(
    request: RegenerationRequest, generation_service: AIGenerationService = Depends()
) -> dict:
    """
    Regenerate text content (copy) while preserving approved strategy and existing images.

    **Purpose**: Update marketing copy for specified platforms while keeping strategy and images intact
    **Input**: Existing generation context and regeneration instructions
    **Output**: Updated copy artifacts and validation results
    """
    try:
        result = await generation_service.regenerate_text(request.dict())
        return {"status": "success", "artifacts": result, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Text regeneration failed: {str(e)}"
        )


@router.post("/regenerate/image", status_code=status.HTTP_200_OK)
async def regenerate_images(
    request: RegenerationRequest, generation_service: AIGenerationService = Depends()
) -> dict:
    """
    Regenerate campaign images while preserving approved strategy and existing copy.

    **Purpose**: Update visual assets for specified platforms while keeping strategy and copy intact
    **Input**: Existing generation context and regeneration instructions
    **Output**: Updated image artifacts and validation results
    """
    try:
        result = await generation_service.regenerate_image(request.dict())
        return {"status": "success", "artifacts": result, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Image regeneration failed: {str(e)}"
        )


@router.post("/regenerate/strategy", status_code=status.HTTP_200_OK)
async def regenerate_strategy(
    request: GenerationContext, generation_service: AIGenerationService = Depends()
) -> dict:
    """
    Regenerate campaign strategy and all dependent artifacts.

    **Purpose**: Update campaign strategy and automatically regenerate all content based on new strategy
    **Input**: Updated generation context with new strategy requirements
    **Output**: New strategy, copy, and image artifacts with validation results
    """
    try:
        result = await generation_service.generate(request.dict())
        return {"status": "success", "artifacts": result, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Strategy regeneration failed: {str(e)}",
        )


@router.post("/validate", status_code=status.HTTP_200_OK)
async def validate_artifacts(
    request: ValidationRequest, generation_service: AIGenerationService = Depends()
) -> dict:
    """
    Validate all generated campaign artifacts against business rules and platform requirements.

    **Purpose**: Validate strategy, copy, image prompts, and images for compliance
    **Input**: Dictionary containing all campaign artifacts
    **Output**: Comprehensive validation results and recommendations
    """
    try:
        result = await generation_service.validate_all_artifacts(request.dict())
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
    """
    Return service information and capabilities.

    **Purpose**: Provide metadata about the AI Generation Engine service
    **Output**: Service name, version, capabilities, and supported operations
    """
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
            "GET /health",
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
