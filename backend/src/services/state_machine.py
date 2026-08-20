"""Deterministic state machine for campaign lifecycle."""


from src.models.campaign import CampaignState


class StateMachine:
    """Deterministic state machine for campaign state transitions."""

    VALID_TRANSITIONS = {
        CampaignState.DRAFT: [CampaignState.READY, CampaignState.ARCHIVED],
        CampaignState.READY: [CampaignState.REVIEW, CampaignState.DRAFT, CampaignState.ARCHIVED],
        CampaignState.REVIEW: [CampaignState.APPROVED, CampaignState.READY, CampaignState.ARCHIVED],
        CampaignState.APPROVED: [
            CampaignState.PUBLISHED,
            CampaignState.REVIEW,
            CampaignState.ARCHIVED,
        ],
        CampaignState.PUBLISHED: [CampaignState.ARCHIVED],
        CampaignState.ARCHIVED: [
            CampaignState.DRAFT,
            CampaignState.READY,
            CampaignState.REVIEW,
            CampaignState.APPROVED,
            CampaignState.PUBLISHED,
        ],
    }

    # Preconditions for specific transitions
    TRANSITION_PRECONDITIONS = {
        (CampaignState.DRAFT, CampaignState.READY): "requires_complete_config",
        (CampaignState.APPROVED, CampaignState.PUBLISHED): "requires_assets",
    }

    @classmethod
    def validate_transition(
        cls, from_state: CampaignState, to_state: CampaignState
    ) -> tuple[bool, str]:
        """Validate if a state transition is allowed.

        Returns:
            Tuple of (is_valid, error_message)
        """
        valid_next = cls.VALID_TRANSITIONS.get(from_state, [])

        if to_state not in valid_next:
            valid_str = ", ".join(s.value for s in valid_next)
            return (
                False,
                f"Cannot transition from {from_state.value} to {to_state.value}. Valid next states: {valid_str}",
            )

        return True, ""

    @classmethod
    def get_valid_next_states(cls, from_state: CampaignState) -> list[CampaignState]:
        """Get list of valid next states from current state."""
        return cls.VALID_TRANSITIONS.get(from_state, [])

    @classmethod
    def get_precondition(cls, from_state: CampaignState, to_state: CampaignState) -> str | None:
        """Get precondition required for transition."""
        return cls.TRANSITION_PRECONDITIONS.get((from_state, to_state))

    @classmethod
    def can_transition(cls, from_state: CampaignState, to_state: CampaignState) -> bool:
        """Check if transition is valid (boolean only)."""
        valid, _ = cls.validate_transition(from_state, to_state)
        return valid

    @classmethod
    def can_edit_config(cls, state: CampaignState) -> bool:
        """Check if campaign configuration can be edited in given state."""
        return state == CampaignState.DRAFT
