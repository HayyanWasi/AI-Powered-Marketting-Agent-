import logging

logger = logging.getLogger(__name__)

PROMPT_TEMPLATES: dict[str, str] = {}


class _SafeDict(dict[str, str]):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def render_template(name: str, variables: dict[str, str]) -> str:
    if name not in PROMPT_TEMPLATES:
        raise KeyError(f"Template '{name}' not found")
    template = PROMPT_TEMPLATES[name]
    rendered = template.format_map(_SafeDict(variables))
    logger.debug("Rendered template '%s'", name)
    return rendered


def register_template(name: str, template: str) -> None:
    if name in PROMPT_TEMPLATES:
        raise ValueError(f"Template '{name}' already exists")
    PROMPT_TEMPLATES[name] = template
    logger.debug("Registered template '%s'", name)
