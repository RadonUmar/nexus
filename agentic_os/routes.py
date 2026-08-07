from __future__ import annotations

from fastapi import FastAPI

from .browser import router as browser_router
from .chat import router as chat_router
from .demo import router as demo_router
from .email import router as email_router
from .files_routes import router as files_router
from .hyperspell_routes import router as hyperspell_router
from .pages import router as pages_router
from .slideshow import router as slideshow_router
from .voice import router as voice_router


def register_routes(app: FastAPI) -> None:
    app.include_router(pages_router)
    app.include_router(chat_router)
    app.include_router(demo_router)
    app.include_router(files_router)
    app.include_router(email_router)
    app.include_router(hyperspell_router)
    app.include_router(browser_router)
    app.include_router(voice_router)
    app.include_router(slideshow_router)

    @app.get("/health")
    async def health_check():
        return {"status": "ok"}
