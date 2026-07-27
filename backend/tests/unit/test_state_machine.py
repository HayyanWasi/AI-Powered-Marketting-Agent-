"""Unit tests for StateMachine."""

import pytest
from src.models.campaign import CampaignState
from src.services.state_machine import StateMachine


class TestStateMachine:
    """Tests for the deterministic state machine."""

    def test_valid_transitions_from_draft(self):
        """Test all valid transitions from Draft state."""
        valid = StateMachine.get_valid_next_states(CampaignState.DRAFT)
        assert CampaignState.READY in valid
        assert CampaignState.ARCHIVED in valid
        assert len(valid) == 2

    def test_valid_transitions_from_ready(self):
        """Test all valid transitions from Ready state."""
        valid = StateMachine.get_valid_next_states(CampaignState.READY)
        assert CampaignState.REVIEW in valid
        assert CampaignState.DRAFT in valid
        assert CampaignState.ARCHIVED in valid
        assert len(valid) == 3

    def test_valid_transitions_from_review(self):
        """Test all valid transitions from Review state."""
        valid = StateMachine.get_valid_next_states(CampaignState.REVIEW)
        assert CampaignState.APPROVED in valid
        assert CampaignState.READY in valid
        assert CampaignState.ARCHIVED in valid
        assert len(valid) == 3

    def test_valid_transitions_from_approved(self):
        """Test all valid transitions from Approved state."""
        valid = StateMachine.get_valid_next_states(CampaignState.APPROVED)
        assert CampaignState.PUBLISHED in valid
        assert CampaignState.REVIEW in valid
        assert CampaignState.ARCHIVED in valid
        assert len(valid) == 3

    def test_valid_transitions_from_published(self):
        """Test all valid transitions from Published state."""
        valid = StateMachine.get_valid_next_states(CampaignState.PUBLISHED)
        assert CampaignState.ARCHIVED in valid
        assert len(valid) == 1

    def test_valid_transitions_from_archived(self):
        """Test all valid transitions from Archived state (restore)."""
        valid = StateMachine.get_valid_next_states(CampaignState.ARCHIVED)
        assert CampaignState.DRAFT in valid
        assert CampaignState.READY in valid
        assert CampaignState.REVIEW in valid
        assert CampaignState.APPROVED in valid
        assert CampaignState.PUBLISHED in valid
        assert len(valid) == 5

    def test_invalid_transition_draft_to_published(self):
        """Test that Draft -> Published is rejected."""
        is_valid, error = StateMachine.validate_transition(
            CampaignState.DRAFT, CampaignState.PUBLISHED
        )
        assert is_valid is False
        assert "Cannot transition from Draft to Published" in error
        assert "Ready, Archived" in error

    def test_invalid_transition_review_to_draft(self):
        """Test that Review -> Draft is rejected."""
        is_valid, error = StateMachine.validate_transition(
            CampaignState.REVIEW, CampaignState.DRAFT
        )
        assert is_valid is False
        assert "Cannot transition from Review to Draft" in error

    def test_valid_transition_draft_to_ready(self):
        """Test that Draft -> Ready is accepted."""
        is_valid, error = StateMachine.validate_transition(CampaignState.DRAFT, CampaignState.READY)
        assert is_valid is True
        assert error == ""

    def test_valid_transition_approved_to_published(self):
        """Test that Approved -> Published is accepted."""
        is_valid, error = StateMachine.validate_transition(
            CampaignState.APPROVED, CampaignState.PUBLISHED
        )
        assert is_valid is True
        assert error == ""

    def test_valid_transition_archived_to_published(self):
        """Test that Archived -> Published (restore) is accepted."""
        is_valid, error = StateMachine.validate_transition(
            CampaignState.ARCHIVED, CampaignState.PUBLISHED
        )
        assert is_valid is True
        assert error == ""

    def test_can_edit_config(self):
        """Test config editing permissions by state."""
        assert StateMachine.can_edit_config(CampaignState.DRAFT) is True
        assert StateMachine.can_edit_config(CampaignState.READY) is False
        assert StateMachine.can_edit_config(CampaignState.REVIEW) is False
        assert StateMachine.can_edit_config(CampaignState.APPROVED) is False
        assert StateMachine.can_edit_config(CampaignState.PUBLISHED) is False
        assert StateMachine.can_edit_config(CampaignState.ARCHIVED) is False

    def test_all_transitions_defined(self):
        """Test that all states have transitions defined."""
        for state in CampaignState:
            valid = StateMachine.get_valid_next_states(state)
            # Every state should have at least one valid transition
            assert len(valid) > 0, f"State {state} has no valid transitions"
