"""Tests for text content validation."""

from src.models.platform import Platform
from src.validators.text_validator import (
    CHARACTER_LIMIT_RULE_ID,
    CHARACTER_LIMIT_RULE_NAME,
    validate_text_content,
)


class TestValidateTextContent:
    """Tests for validate_text_content function."""

    def test_text_within_linkedin_limit(self) -> None:
        text = "A" * 1000
        result = validate_text_content(text, Platform.LINKEDIN)

        assert result.passed is True
        assert result.character_count == 1000
        assert result.character_limit == 3000
        assert result.violations == []

    def test_text_within_instagram_limit(self) -> None:
        text = "B" * 1500
        result = validate_text_content(text, Platform.INSTAGRAM)

        assert result.passed is True
        assert result.character_count == 1500
        assert result.character_limit == 2200
        assert result.violations == []

    def test_text_within_facebook_limit(self) -> None:
        text = "C" * 50000
        result = validate_text_content(text, Platform.FACEBOOK)

        assert result.passed is True
        assert result.character_count == 50000
        assert result.character_limit == 63206
        assert result.violations == []

    def test_text_exceeds_linkedin_limit(self) -> None:
        text = "D" * 3001
        result = validate_text_content(text, Platform.LINKEDIN)

        assert result.passed is False
        assert result.character_count == 3001
        assert result.character_limit == 3000
        assert len(result.violations) == 1
        assert result.violations[0].rule_id == CHARACTER_LIMIT_RULE_ID
        assert result.violations[0].rule_name == CHARACTER_LIMIT_RULE_NAME
        assert result.violations[0].current_value == 3001
        assert result.violations[0].expected_value == 3000

    def test_text_exceeds_instagram_limit(self) -> None:
        text = "E" * 2201
        result = validate_text_content(text, Platform.INSTAGRAM)

        assert result.passed is False
        assert result.character_count == 2201
        assert result.character_limit == 2200
        assert len(result.violations) == 1

    def test_text_exactly_at_limit(self) -> None:
        text = "F" * 3000
        result = validate_text_content(text, Platform.LINKEDIN)

        assert result.passed is True
        assert result.character_count == 3000
        assert result.violations == []

    def test_empty_text(self) -> None:
        result = validate_text_content("", Platform.LINKEDIN)

        assert result.passed is True
        assert result.character_count == 0
        assert result.violations == []

    def test_single_character(self) -> None:
        result = validate_text_content("X", Platform.INSTAGRAM)

        assert result.passed is True
        assert result.character_count == 1
        assert result.violations == []

    def test_text_with_unicode(self) -> None:
        text = "Hello World"
        result = validate_text_content(text, Platform.LINKEDIN)

        assert result.passed is True
        assert result.character_count == len(text)

    def test_violation_message_contains_details(self) -> None:
        text = "G" * 5000
        result = validate_text_content(text, Platform.LINKEDIN)

        assert result.passed is False
        message = result.violations[0].message
        assert "5000" in message
        assert "3000" in message
        assert "linkedin" in message.lower()

    def test_text_exactly_one_over_limit(self) -> None:
        text = "H" * 2201
        result = validate_text_content(text, Platform.INSTAGRAM)

        assert result.passed is False
        assert result.character_count == 2201
        assert result.character_limit == 2200
