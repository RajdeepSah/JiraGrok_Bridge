"""Small, explicit exception types raised by the core package.

Jira and Groq network errors are intentionally NOT wrapped here - callers (the CLI
and the backend's exception handlers) already know how to translate the native
``requests.HTTPError`` / ``groq`` exceptions, and wrapping them would lose detail.
"""


class ConfigError(RuntimeError):
    """Raised by config.load_config() when a required server-side setting is missing."""


class TemplateNotFound(KeyError):
    """Raised by TemplateStore.get() when no template has the requested id."""

    def __init__(self, template_id: str):
        self.template_id = template_id
        super().__init__(template_id)

    def __str__(self) -> str:  # KeyError repr adds quotes; give a plain message
        return f"No instruction template with id {self.template_id!r}."
