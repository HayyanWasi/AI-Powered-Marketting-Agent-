"""Prompt template system contract.

Named system prompt templates stored in Python code (not DB).
Templates use {variable_name} syntax for placeholder injection.
"""

PROMPT_TEMPLATES: dict[str, str] = {
    # Example structure — actual templates added by campaign agents
    # "campaign_instagram": "You are an Instagram marketing expert...\nTone: {company_tone}\nGuest: {guest_name}",
    # "campaign_linkedin": "...",
}


def render_template(name: str, variables: dict[str, str]) -> str:
    """Look up template by name and substitute variables.

    Args:
        name: Template name (case-sensitive, must exist in PROMPT_TEMPLATES).
        variables: Dict of {placeholder_name: value}.

    Returns:
        Rendered prompt string. Missing placeholders left as-is.

    Raises:
        KeyError: if template name not found.
    """
    ...


def register_template(name: str, template: str) -> None:
    """Register a new template (used by campaign agents at import time).

    Args:
        name: Unique template name.
        template: Prompt string with {variable} placeholders.

    Raises:
        ValueError: if name already exists.
    """
    ...
