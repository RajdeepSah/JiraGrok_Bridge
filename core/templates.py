"""Instruction-template management.

Templates are the selectable system prompts that replace the old hardcoded
TASK_INSTRUCTIONS constant. They live in ``templates.json`` (data, not code), so a
new template is added by appending one object to that file - no code change.

The store loads and validates the file once and caches it. Only the bundled file is
ever read (never a user-supplied path), and it is parsed with the standard, safe
``json`` module.
"""

import json
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field

from .errors import TemplateNotFound

TEMPLATES_PATH = Path(__file__).with_name("templates.json")

# The default reproduces the original script's behavior (improve the ticket text).
DEFAULT_TEMPLATE_ID = "ticket-improvement"


class Template(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    instructions: str = Field(min_length=1)


class TemplateStore:
    """In-memory collection of validated templates, preserving file order."""

    def __init__(self, templates: list[Template]):
        if not templates:
            raise ValueError("templates.json contained no templates.")
        self._by_id: dict[str, Template] = {}
        for tpl in templates:
            if tpl.id in self._by_id:
                raise ValueError(f"Duplicate template id in templates.json: {tpl.id!r}")
            self._by_id[tpl.id] = tpl

    @classmethod
    def from_file(cls, path: Path = TEMPLATES_PATH) -> "TemplateStore":
        raw = json.loads(path.read_text(encoding="utf-8"))
        items = raw["templates"] if isinstance(raw, dict) else raw
        return cls([Template.model_validate(item) for item in items])

    def list(self) -> list[Template]:
        """All templates, in file order (full objects; callers project as needed)."""
        return list(self._by_id.values())

    def get(self, template_id: str) -> Template:
        try:
            return self._by_id[template_id]
        except KeyError:
            raise TemplateNotFound(template_id) from None

    def default(self) -> Template:
        return self._by_id.get(DEFAULT_TEMPLATE_ID) or next(iter(self._by_id.values()))


@lru_cache(maxsize=1)
def get_template_store() -> TemplateStore:
    """Cached singleton store loaded from the bundled templates.json."""
    return TemplateStore.from_file()
