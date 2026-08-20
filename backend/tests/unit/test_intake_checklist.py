"""Unit tests for Intake Checklist validation and Intake Chat Service."""

from src.models.intake import IntakeChecklist


def test_intake_checklist_completion():
    """Verify is_complete validation rules."""
    checklist = IntakeChecklist()
    assert checklist.is_complete() is False

    # Fill core required fields
    checklist.event_name = "AI Automation Seminar"
    checklist.target_audience = "Tech founders and COOs"
    checklist.outcome_deliverable = "Master real-world agentic workflows"

    # Core filled without guest -> Complete
    assert checklist.is_complete() is True

    # Has guest but not confirmed -> Incomplete
    checklist.has_guest = True
    checklist.guest_name = "Zia Ullah Khan"
    checklist.guest_confirmed = False
    assert checklist.is_complete() is False

    # Confirm guest -> Complete
    checklist.guest_confirmed = True
    assert checklist.is_complete() is True
