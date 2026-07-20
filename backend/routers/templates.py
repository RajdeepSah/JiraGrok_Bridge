"""Instruction-template endpoints."""

from fastapi import APIRouter

from core.templates import get_template_store

from ..schemas import TemplateDetail, TemplateSummary

router = APIRouter(prefix="/templates", tags=["templates"])


@router.get("", response_model=list[TemplateSummary])
def list_templates() -> list[TemplateSummary]:
    """Metadata for the gallery cards (id/name/description) - not the full prompts."""
    store = get_template_store()
    return [TemplateSummary(id=t.id, name=t.name, description=t.description) for t in store.list()]


@router.get("/{template_id}", response_model=TemplateDetail)
def get_template(template_id: str) -> TemplateDetail:
    """Full template incl. instruction text - used by the 'View Details' modal."""
    tpl = get_template_store().get(template_id)  # raises TemplateNotFound -> 404
    return TemplateDetail(id=tpl.id, name=tpl.name, description=tpl.description, instructions=tpl.instructions)
