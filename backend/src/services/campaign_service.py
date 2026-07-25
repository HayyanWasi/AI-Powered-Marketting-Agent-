"""Campaign service - core business logic."""

from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from src.models.campaign import Campaign, CampaignState, Goals, TargetAudience, Schedule
from src.models.history import EventType
from src.repositories.campaign_repository import CampaignRepository
from src.repositories.asset_repository import AssetRepository
from src.services.state_machine import StateMachine
from src.services.history_service import HistoryService
from src.services.asset_service import AssetService
from src.models.errors import (
    NotFoundError,
    StateTransitionError,
    VersionConflictError,
    DuplicateNameError,
    PreconditionFailedError,
    ValidationError,
)


class CampaignService:
    """Service for campaign business logic."""

    def __init__(
        self,
        campaign_repository: CampaignRepository | None = None,
        asset_repository: AssetRepository | None = None,
        history_service: HistoryService | None = None,
        state_machine: StateMachine | None = None,
        asset_service: AssetService | None = None,
    ):
        self.campaign_repository = campaign_repository or CampaignRepository()
        self.asset_repository = asset_repository or AssetRepository()
        self.history_service = history_service or HistoryService()
        self.state_machine = state_machine or StateMachine()
        self.asset_service = asset_service or AssetService()

    async def create_campaign(
        self,
        name: str,
        goals: dict,
        target_audience: dict,
        platforms: List[str],
        schedule: dict,
        metadata: Optional[dict] = None,
        company_profile_id: Optional[UUID] = None,
        organization_id: UUID = None,
        actor_id: UUID = None,
    ) -> Campaign:
        """Create a new campaign in Draft state."""
        # Check for duplicate name
        existing = await self.campaign_repository.get_by_name(name, organization_id)
        if existing:
            raise DuplicateNameError(name)

        # Build campaign object
        campaign = Campaign(
            organization_id=organization_id,
            company_profile_id=company_profile_id,
            name=name,
            goals=Goals(
                primary=goals.get("primary", ""),
                metrics=goals.get("metrics", []),
                targets=goals.get("targets", {}),
            ),
            target_audience=TargetAudience(
                segments=target_audience.get("segments", []),
                demographics=target_audience.get("demographics", {}),
                interests=target_audience.get("interests", []),
            ),
            platforms=platforms,
            schedule=Schedule(
                start_date=datetime.fromisoformat(schedule["start_date"].replace("Z", "+00:00")),
                end_date=datetime.fromisoformat(schedule["end_date"].replace("Z", "+00:00")),
                timezone=schedule.get("timezone", "UTC"),
                recurrence_rule=schedule.get("recurrence_rule"),
            ),
            metadata=metadata or {},
            created_by=actor_id,
            updated_by=actor_id,
        )

        # Persist
        created = await self.campaign_repository.create(campaign)

        # Log creation
        await self.history_service.log_creation(created, actor_id)

        return created

    async def get_campaign(
        self, campaign_id: UUID, organization_id: UUID | None = None
    ) -> Campaign:
        """Get campaign by ID."""
        campaign = await self.campaign_repository.get_by_id(campaign_id)
        if not campaign:
            raise NotFoundError("Campaign", str(campaign_id))
        return campaign

    async def get_campaign_with_assets(
        self, campaign_id: UUID, organization_id: UUID | None = None
    ) -> Campaign:
        """Get campaign with assets."""
        campaign = await self.campaign_repository.get_with_assets(campaign_id)
        if not campaign:
            raise NotFoundError("Campaign", str(campaign_id))
        return campaign

    async def list_campaigns(
        self,
        organization_id: UUID,
        state: Optional[CampaignState] = None,
        page: int = 1,
        page_size: int = 20,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        owner_id: Optional[UUID] = None,
    ) -> tuple[List[Campaign], int]:
        """List campaigns with filters."""
        return await self.campaign_repository.list(
            organization_id=organization_id,
            state=state,
            page=page,
            page_size=page_size,
            start_date=start_date,
            end_date=end_date,
            owner_id=owner_id,
        )

    async def update_campaign(
        self,
        campaign_id: UUID,
        updates: Dict[str, Any],
        expected_version: int,
        actor_id: UUID,
    ) -> Campaign:
        """Update campaign configuration (Draft only, atomic)."""
        campaign = await self.get_campaign(campaign_id)

        # Check state
        if campaign.state != CampaignState.DRAFT:
            raise StateTransitionError(
                current_state=campaign.state.value,
                attempted_state="update",
                valid_states=["Draft"],
            )

        # Check version for optimistic locking
        if campaign.version != expected_version:
            raise VersionConflictError(expected_version, campaign.version)

        # Build updates dict
        update_data = {}
        changed_fields = {}

        for field, new_value in updates.items():
            if hasattr(campaign, field):
                old_value = getattr(campaign, field)
                if old_value != new_value:
                    update_data[field] = new_value
                    changed_fields[field] = {"old": old_value, "new": new_value}

        if not update_data:
            return campaign  # No changes

        # Apply updates
        for field, value in update_data.items():
            setattr(campaign, field, value)

        campaign.updated_by = actor_id
        expected_version = campaign.version
        campaign.version += 1

        # Persist
        updated = await self.campaign_repository.update(campaign, expected_version=expected_version)

        # Log configuration change
        await self.history_service.log_configuration_change(updated, actor_id, changed_fields)

        return updated

    async def transition_campaign(
        self,
        campaign_id: UUID,
        to_state: CampaignState,
        actor_id: UUID,
        reason: Optional[str] = None,
    ) -> Campaign:
        """Transition campaign to new state with validation."""
        campaign = await self.get_campaign(campaign_id)
        from_state = campaign.state

        # Validate transition
        valid, error = self.state_machine.validate_transition(from_state, to_state)
        if not valid:
            raise StateTransitionError(
                from_state.value,
                to_state.value,
                [s.value for s in self.state_machine.get_valid_next_states(from_state)],
            )

        # Check preconditions
        precondition = self.state_machine.get_precondition(from_state, to_state)
        if precondition == "requires_complete_config" and not self._is_config_complete(campaign):
            raise PreconditionFailedError(
                "Campaign configuration incomplete. Required: goals, target_audience, platforms, schedule"
            )

        if precondition == "requires_assets" and not await self._has_required_assets(campaign):
            raise PreconditionFailedError("Campaign must have at least one asset before publishing")

        # Apply transition
        campaign.state = to_state
        campaign.updated_by = actor_id
        expected_version = campaign.version
        campaign.version += 1

        # Set timestamps
        if to_state == CampaignState.PUBLISHED:
            campaign.published_at = datetime.utcnow()
        elif to_state == CampaignState.ARCHIVED:
            campaign.archived_at = datetime.utcnow()
            campaign.previous_state = from_state

        # Persist
        updated = await self.campaign_repository.update(campaign, expected_version=expected_version)

        # Log state transition
        await self.history_service.log_state_transition(
            updated, actor_id, from_state, to_state, reason
        )

        return updated

    async def archive_campaign(
        self,
        campaign_id: UUID,
        actor_id: UUID,
        reason: Optional[str] = None,
        organization_id: UUID | None = None,
    ) -> Campaign:
        """Archive a campaign."""
        return await self.transition_campaign(campaign_id, CampaignState.ARCHIVED, actor_id, reason)

    async def restore_campaign(
        self,
        campaign_id: UUID,
        actor_id: UUID,
        organization_id: UUID | None = None,
    ) -> Campaign:
        """Restore an archived campaign to its previous state."""
        campaign = await self.get_campaign(campaign_id)

        if campaign.state != CampaignState.ARCHIVED:
            raise StateTransitionError(
                current_state=campaign.state.value,
                attempted_state="restore",
                valid_states=["Archived"],
            )

        previous_state = campaign.previous_state or CampaignState.DRAFT

        campaign.state = previous_state
        campaign.archived_at = None
        campaign.previous_state = None
        campaign.updated_by = actor_id
        expected_version = campaign.version
        campaign.version += 1

        updated = await self.campaign_repository.update(campaign, expected_version=expected_version)
        await self.history_service.log_restore(updated, actor_id)

        return updated

    async def delete_campaign(self, campaign_id: UUID, actor_id: UUID) -> None:
        """Delete a campaign (Draft only)."""
        campaign = await self.get_campaign(campaign_id)

        if campaign.state != CampaignState.DRAFT:
            raise StateTransitionError(
                current_state=campaign.state.value,
                attempted_state="delete",
                valid_states=["Draft"],
            )

        await self.campaign_repository.delete(campaign_id, campaign.organization_id)

    def _is_config_complete(self, campaign: Campaign) -> bool:
        """Check if campaign has all required configuration."""
        return bool(
            campaign.goals
            and campaign.goals.primary
            and campaign.target_audience
            and campaign.target_audience.segments
            and campaign.platforms
            and campaign.schedule
            and campaign.schedule.start_date
            and campaign.schedule.end_date
        )

    async def _has_required_assets(self, campaign: Campaign) -> bool:
        """Check if campaign has required assets for publishing."""
        assets = await self.asset_repository.get_by_campaign(campaign.id)
        return len(assets) > 0
