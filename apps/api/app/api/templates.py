from __future__ import annotations

from fastapi import APIRouter

from app.schemas.errors import friendly_error
from app.schemas.templates import TemplateDetail
from app.services.template_repository import get_template

router = APIRouter(prefix="/api/templates", tags=["templates"])


@router.get("/{template_id}", response_model=TemplateDetail)
def template_detail(template_id: str) -> dict:
    template = get_template(template_id)
    if template is None:
        raise friendly_error(404, "Khong tim thay mau thiet bi. Vui long chon lai.", "manual_select")
    return template
