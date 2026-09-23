"""The shared _Section base absorbs the type-loose JSON small/local models emit.

Weak models return a scalar text field as a number or one-item list, and
return "nothing" as explicit null instead of omitting the key. Under strict
Pydantic each raises and fails the whole specialist (→ a 502 with no data
actually at fault). These lock in the coercion — and its truthful limits.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.modules.planning.models.campaign_plan import (
    ChannelPlan,
    Competitive,
    CoreStrategy,
    Measurement,
    Persona,
    PhasePlan,
)


def test_numeric_text_field_is_coerced_to_string():
    plan = ChannelPlan.model_validate(
        {"platforms": [], "phases": [], "calendar_slots": [], "overall_cadence": 3}
    )
    assert plan.overall_cadence == "3"


def test_list_in_text_field_is_joined():
    comp = Competitive.model_validate(
        {"landscape": [], "differentiation_angle": ["Buyer rep", "Local expertise"]}
    )
    assert comp.differentiation_angle == "Buyer rep, Local expertise"


def test_explicit_null_falls_back_to_declared_default():
    phase = PhasePlan.model_validate(
        {"phase": "launch", "duration": None, "objective": "o", "key_message": None}
    )
    assert phase.duration == ""
    assert phase.key_message == ""


def test_null_in_tuple_field_falls_back_to_empty_tuple():
    core = CoreStrategy.model_validate({"objective": "o", "messaging_pillars": None})
    assert core.messaging_pillars == ()


def test_dict_in_text_field_is_still_rejected():
    # Structured garbage in a prose field is a real error, not type-looseness:
    # it must not be fabricated into a plausible string.
    with pytest.raises(ValidationError):
        Persona.model_validate({"name": {"invalid": True}, "description": "d"})


def test_valid_payload_is_unchanged():
    m = Measurement.model_validate(
        {"kpis": [], "tracking_plan": "t", "reporting_cadence": "r", "definition_of_success": "s"}
    )
    assert m.tracking_plan == "t"
    assert m.definition_of_success == "s"
