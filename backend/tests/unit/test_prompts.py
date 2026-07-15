import pytest

from src.config.prompts import (
    PROMPT_TEMPLATES,
    register_template,
    render_template,
)


class TestRenderTemplate:
    def setup_method(self) -> None:
        PROMPT_TEMPLATES.clear()

    def test_render_with_variables(self) -> None:
        PROMPT_TEMPLATES["test"] = "Hello {name}, you are {role}"
        result = render_template("test", {"name": "Alice", "role": "admin"})
        assert result == "Hello Alice, you are admin"

    def test_render_missing_variable_left_as_is(self) -> None:
        PROMPT_TEMPLATES["test"] = "Hello {name}, role: {role}"
        result = render_template("test", {"name": "Alice"})
        assert result == "Hello Alice, role: {role}"

    def test_render_no_variables(self) -> None:
        PROMPT_TEMPLATES["test"] = "Static prompt"
        result = render_template("test", {})
        assert result == "Static prompt"

    def test_render_unknown_template_raises_key_error(self) -> None:
        with pytest.raises(KeyError, match="nonexistent"):
            render_template("nonexistent", {})

    def test_render_special_characters_in_value(self) -> None:
        PROMPT_TEMPLATES["test"] = "Content: {body}"
        result = render_template("test", {"body": "<b>bold</b> &amp;"})
        assert result == "Content: <b>bold</b> &amp;"


class TestRegisterTemplate:
    def setup_method(self) -> None:
        PROMPT_TEMPLATES.clear()

    def test_register_new_template(self) -> None:
        register_template("my_template", "Hello {name}")
        assert "my_template" in PROMPT_TEMPLATES
        assert PROMPT_TEMPLATES["my_template"] == "Hello {name}"

    def test_register_duplicate_raises_value_error(self) -> None:
        register_template("dup", "First")
        with pytest.raises(ValueError, match="already exists"):
            register_template("dup", "Second")

    def test_register_then_render(self) -> None:
        register_template("render_test", "Hi {user}")
        result = render_template("render_test", {"user": "Bob"})
        assert result == "Hi Bob"
