"""Aggregate v1 router — includes all version 1 endpoint routers."""

from fastapi import APIRouter

from src.api.v1 import (
    ai_generation,
    campaign_images,
    campaigns,
    company,
    guest,
    health,
    image_processing,
    operations,
    validation,
    workflow,
)

router = APIRouter()

router.include_router(health.router)
router.include_router(campaigns.router)
router.include_router(company.router)
router.include_router(guest.router)
router.include_router(ai_generation.router)
router.include_router(campaign_images.router)
router.include_router(validation.router)
router.include_router(workflow.router)
router.include_router(operations.router)
router.include_router(image_processing.router)
