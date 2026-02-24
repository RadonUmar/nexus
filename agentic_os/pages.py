from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates


router = APIRouter()
_templates: Optional[Jinja2Templates] = None


def init_templates(templates: Jinja2Templates) -> None:
    global _templates
    _templates = templates


@router.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    if _templates is None:
        raise RuntimeError("Templates not initialized")
    return _templates.TemplateResponse("index.html", {"request": request})


@router.get("/voice", response_class=HTMLResponse)
async def voice_chat_page(request: Request):
    if _templates is None:
        raise RuntimeError("Templates not initialized")
    return _templates.TemplateResponse("voice_chat.html", {"request": request})
