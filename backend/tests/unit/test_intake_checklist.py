"""Unit tests for Intake Checklist validation and Intake Chat Service."""

from src.models.intake import IntakeChecklist


def test_intake_checklist_completion():
    """Verify is_complete validation rules."""
    checklist = IntakeChecklist()
    assert checklist.is_complete() is False

    # Fill core required fields for a webinar
    checklist.campaign_type = "webinar"
    checklist.campaign_name = "AI Automation Seminar"
    checklist.objective = "Master real-world agentic workflows"
    checklist.target_audience = "Tech founders and COOs"
    checklist.event_date = "2026-09-01"
    checklist.venue = "Online"

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
    
    # Test App Launch
    app_checklist = IntakeChecklist()
    app_checklist.campaign_type = "app_launch"
    app_checklist.campaign_name = "New App"
    app_checklist.objective = "Get downloads"
    app_checklist.target_audience = "Everyone"
    assert app_checklist.is_complete() is False
    
    app_checklist.value_proposition = "It's awesome"
    assert app_checklist.is_complete() is True
