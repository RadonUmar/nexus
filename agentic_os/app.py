from __future__ import annotations

import asyncio

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .browser import init_browser
from .email import email_monitor_worker
from .logging import configure_logging, get_logger
from .pages import init_templates
from .routes import register_routes
from .settings import settings
from . import state
from voice_agent import VoiceConfig, initialize_voice_agent


logger = get_logger(__name__)


def create_app() -> FastAPI:
    configure_logging()

    app = FastAPI(title="Agentic OS")

    app.mount("/static", StaticFiles(directory=str(settings.static_dir)), name="static")
    templates = Jinja2Templates(directory=str(settings.templates_dir))
    init_templates(templates)

    voice_config = VoiceConfig(
        tts_voice="nova",
        max_history=10,
        system_prompt=(
            "You are Nexus, a natural voice assistant for an AI phone UI.\n"
            "Keep replies warm, direct, and short enough to say aloud.\n"
            "Default to one sentence under 14 words.\n"
            "For UI actions, acknowledge briefly without explaining what is visible."
        ),
    )
    initialize_voice_agent(settings.openai_api_key, voice_config)
    logger.info("Voice Agent initialized successfully")

    register_routes(app)

    @app.on_event("startup")
    async def startup_event() -> None:
        await init_browser()

        try:
            state.email_monitor_task = asyncio.create_task(email_monitor_worker())
            logger.info("✅ Email monitor task started")
        except Exception as exc:
            logger.error("Failed to start email monitor task: %s", exc, exc_info=True)

    @app.on_event("shutdown")
    async def shutdown_event() -> None:
        for session_id, task in state.agent_task_registry.items():
            task.cancel()
        state.agent_task_registry.clear()

        if state.email_monitor_task:
            state.email_monitor_task.cancel()
            logger.info("Email monitor task cancelled")

        if state.browser_instance:
            await state.browser_instance.close()
            logger.info("Browser closed")

    return app
