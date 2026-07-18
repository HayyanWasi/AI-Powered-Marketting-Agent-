"""Text validation for campaign content against platform-specific rules."""

import logging

from src.models.platform import PLATFORM_TEXT_LIMITS, Platform
from src.models.validation import (
    RuleSeverity,
    RuleViolation,
    TextValidationResultInternal,
)

logger = logging.getLogger(__name__)

CHARACTER_LIMIT_RULE_ID = "TEXT_CHAR_LIMIT"
CHARACTER_LIMIT_RULE_NAME = "Character Limit"


def validate_text_content(
    text_content: str,
    platform: Platform,
) -> TextValidationResultInternal:
    """
    Validate campaign text against platform character limits.

    Args:
        text_content: The campaign text to validate
        platform: Target social media platform

    Returns:
        TextValidationResultInternal with validation status and any violations
    """
    character_count = len(text_content)
    character_limit = PLATFORM_TEXT_LIMITS[platform]

    violations: list[RuleViolation] = []

    if character_count > character_limit:
        violation = RuleViolation(
            rule_id=CHARACTER_LIMIT_RULE_ID,
            rule_name=CHARACTER_LIMIT_RULE_NAME,
            message=(
                f"Text content is {character_count} characters, "
                f"exceeding {platform.value} limit of {character_limit} characters"
            ),
            severity=RuleSeverity.ERROR,
            current_value=character_count,
            expected_value=character_limit,
        )
        violations.append(violation)
        logger.warning(
            "Text validation failed: %d/%d characters on %s",
            character_count,
            character_limit,
            platform.value,
        )
    else:
        logger.debug(
            "Text validation passed: %d/%d characters on %s",
            character_count,
            character_limit,
            platform.value,
        )

    return TextValidationResultInternal(
        passed=len(violations) == 0,
        character_count=character_count,
        character_limit=character_limit,
        violations=violations,
    )
