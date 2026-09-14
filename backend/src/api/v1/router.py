"""Aggregate v1 router — includes all version 1 endpoint routers."""

from fastapi import APIRouter

from src.api.routes import linkedin_review
from src.api.v1 import (
    ai_generation,
    autopilot,
    campaign_images,
    campaign_images_iterative,
    campaigns,
    company,
    guest,
    health,
    image_processing,
    intake,
    linkedin,
    linkedin_setup,
    linkedin_webhooks,
    operations,
    plans,
    validation,
    video,
    workflow,
)
from src.modules.research.api.v1 import research

router = APIRouter()

router.include_router(health.router)
router.include_router(campaigns.router)
router.include_router(company.router)
router.include_router(guest.router)
router.include_router(ai_generation.router)
router.include_router(campaign_images.router)
router.include_router(campaign_images_iterative.router)
router.include_router(validation.router)
router.include_router(workflow.router)
router.include_router(operations.router)
router.include_router(image_processing.router)
router.include_router(plans.router)
router.include_router(research.router)
router.include_router(linkedin.router)
router.include_router(linkedin_setup.router)
router.include_router(linkedin_webhooks.router)
router.include_router(linkedin_review.router)
router.include_router(autopilot.router)
router.include_router(intake.router)
router.include_router(video.router)
