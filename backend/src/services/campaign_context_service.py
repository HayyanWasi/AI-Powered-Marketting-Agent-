"""Resolve trusted brand and intake context through the campaign's owned database FK."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from fastapi import HTTPException

from src.models.audience import AudienceProfile
from src.models.brand_context import BrandContext
from src.models.campaign import Campaign
from src.modules.planning.models.brief import PlanBrief
from src.repositories.base import BaseRepository
from src.repositories.campaign_repository import CampaignRepository
from src.repositories.company_repository import CompanyNotFoundError, CompanyRepository
from src.services.supabase import SupabaseService


def compute_brand_fingerprint(brand: Any) -> str:
    """Deterministic hash of strategy-relevant brand details."""
    if not brand:
        return ""
    try:
        if hasattr(brand, "as_prompt") and callable(brand.as_prompt):
            raw = brand.as_prompt()
            content = str(raw) if not isinstance(raw, str) else raw
        else:
            content = str(brand)
        content = content.strip()
    except Exception:
        content = str(brand)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def compute_intake_fingerprint(
    intake: dict[str, Any] | None, campaign: Campaign | None = None
) -> str:
    """Deterministic hash of strategy-relevant campaign and intake fields.

    Ignores non-strategy fields such as timestamps, message histories, and UI state.
    """
    data = intake or {}

    campaign_name = (
        data.get("campaign_name")
        or data.get("event_name")
        or (getattr(campaign, "name", "") if campaign else "")
        or ""
    )
    objective = (
        data.get("objective")
        or (
            campaign.goals.primary
            if campaign and campaign.goals and getattr(campaign.goals, "primary", None)
            else ""
        )
        or ""
    )
    cta_url = data.get("cta_url") or data.get("registration_link") or ""
    value_proposition = data.get("value_proposition") or data.get("outcome_deliverable") or ""

    has_guest = bool(data.get("has_guest"))
    guest_name = str(data.get("guest_name") or "") if has_guest else ""
    guest_title = str(data.get("guest_title") or "") if has_guest else ""

    platforms: tuple[str, ...] = ()
    if campaign and getattr(campaign, "platforms", None):
        platforms = tuple(sorted(str(p) for p in campaign.platforms))
    elif data.get("platforms"):
        p_val = data.get("platforms")
        if isinstance(p_val, (list, tuple)):
            platforms = tuple(sorted(str(p) for p in p_val))
        elif isinstance(p_val, str):
            platforms = tuple(sorted(p.strip() for p in p_val.split(",") if p.strip()))

    campaign_schedule = getattr(campaign, "schedule", None) if campaign else None
    start_date = getattr(campaign_schedule, "start_date", None)
    end_date = getattr(campaign_schedule, "end_date", None)

    canonical_payload = {
        "campaign_type": str(data.get("campaign_type") or "").strip(),
        "campaign_name": str(campaign_name).strip(),
        "objective": str(objective).strip(),
        "value_proposition": str(value_proposition).strip(),
        "outcome_deliverable": str(data.get("outcome_deliverable") or "").strip(),
        "cta_url": str(cta_url).strip(),
        "registration_link": str(data.get("registration_link") or "").strip(),
        "target_audience": str(data.get("target_audience") or "").strip(),
        "audience_profile": data.get("audience_profile") or {},
        "category": str(data.get("category") or "").strip(),
        "curriculum_breakdown": str(data.get("curriculum_breakdown") or "").strip(),
        "ticket_price": str(data.get("is_free_or_paid") or "").strip(),
        "event_date": str(data.get("event_date") or "").strip(),
        "venue": str(data.get("venue") or "").strip(),
        "guest_name": guest_name.strip(),
        "guest_title": guest_title.strip(),
        "platforms": list(platforms),
        "campaign_start": start_date.isoformat() if start_date else "",
        "campaign_end": end_date.isoformat() if end_date else "",
        "campaign_timezone": getattr(campaign_schedule, "timezone", "") or "",
    }

    serialized = json.dumps(
        canonical_payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def check_plan_freshness(plan: Any, inputs: CampaignInputs) -> tuple[bool, str | None]:
    """Check if a stored plan is stale relative to current campaign/intake/brand state.

    Returns:
        (is_stale, reason)
    """
    ident = getattr(plan, "input_identity", None)
    if not ident:
        return True, "Plan lacks identity tracking (legacy version)."

    current_company_id = str(getattr(inputs.brand, "company_profile_id", ""))
    plan_company_id = str(ident.company_profile_id) if ident.company_profile_id else ""
    if plan_company_id != current_company_id:
        return True, "Brand/Company changed."

    # Brand freshness
    current_brand_fp = compute_brand_fingerprint(inputs.brand)
    if ident.brand_version != current_brand_fp:
        return True, "Brand profile was updated."

    # Campaign/intake freshness
    current_intake_fp = compute_intake_fingerprint(inputs.intake, inputs.campaign)
    if ident.intake_hash != current_intake_fp:
        return True, "Campaign details were updated."

    return False, None


def owned_profiles(user_id: str) -> CompanyRepository:
    return CompanyRepository(SupabaseService(user_id=user_id))


def require_profile(profile_id: UUID, user_id: str) -> BrandContext:
    try:
        profile = owned_profiles(user_id).get_by_id(str(profile_id))
    except CompanyNotFoundError as exc:
        raise HTTPException(404, "Company profile not found or access denied.") from exc
    if not profile.is_complete:
        raise HTTPException(422, "Complete Brand Setup before generating a campaign.")
    return BrandContext.from_profile(profile)


@dataclass(frozen=True)
class CampaignInputs:
    campaign: Campaign
    brand: BrandContext
    intake: dict[str, Any]

    def to_brief(self, user_goal: str = "") -> PlanBrief:
        data = self.intake
        campaign_schedule = getattr(self.campaign, "schedule", None)
        start_date = getattr(campaign_schedule, "start_date", None)
        end_date = getattr(campaign_schedule, "end_date", None)
        guests = ()
        if data.get("has_guest") is True and data.get("guest_name"):
            guests = (" — ".join(str(data[k]) for k in ("guest_name", "guest_title") if data.get(k)),)
        return PlanBrief(
            user_goal=user_goal or (self.campaign.goals.primary if self.campaign.goals else ""),
            campaign_id=str(self.campaign.id),
            company_profile_id=str(self.brand.company_profile_id),
            brand_version=compute_brand_fingerprint(self.brand),
            intake_hash=compute_intake_fingerprint(data, self.campaign),
            brand=self.brand,
            company_name=self.brand.company_name,
            brand_tone=self.brand.brand_tone,
            brand_guidelines=self.brand.as_prompt(),
            campaign_type=data.get("campaign_type") or "",
            campaign_name=data.get("campaign_name") or data.get("event_name") or getattr(self.campaign, "name", "") or "",
            objective=data.get("objective") or "",
            value_proposition=data.get("value_proposition") or "",
            cta_url=data.get("cta_url") or "",
            category=data.get("category") or "",
            target_audience=data.get("target_audience") or (
                (data.get("audience_profile") or {}).get("summary", "")
            ),
            audience_profile=AudienceProfile.model_validate(data["audience_profile"])
            if data.get("audience_profile") else None,
            campaign_start=(start_date.date().isoformat() if start_date else ""),
            campaign_end=(end_date.date().isoformat() if end_date else ""),
            campaign_timezone=(getattr(campaign_schedule, "timezone", None) or "UTC"),
            curriculum_breakdown=data.get("curriculum_breakdown") or "",
            outcome_deliverable=data.get("outcome_deliverable") or "",
            ticket_price=data.get("is_free_or_paid") or "",
            event_date=data.get("event_date") or "", venue=data.get("venue") or "",
            registration_link=data.get("registration_link") or "",
            platforms=tuple(self.campaign.platforms), guests=guests,
        )


class CampaignContextResolver:
    async def resolve(self, campaign_id: UUID, user_id: str) -> CampaignInputs:
        campaign = await CampaignRepository().get_by_id(campaign_id, UUID(user_id))
        if campaign is None:
            raise HTTPException(404, "Campaign not found or access denied.")
        if not campaign.company_profile_id:
            raise HTTPException(422, "Select Brand Setup for this campaign before generation.")
        brand = require_profile(campaign.company_profile_id, user_id)
        repo = BaseRepository("intake_checklists")
        result = repo.client.table(repo.table_name).select("*").eq(
            "campaign_id", str(campaign_id)
        ).execute()
        return CampaignInputs(campaign, brand, result.data[0] if result.data else {})
