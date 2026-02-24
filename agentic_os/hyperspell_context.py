from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from .logging import get_logger
from .settings import settings
from hyperspell_integration import (
    HyperspellMemory,
    format_memories_for_prompt,
    get_hyperspell_client,
)


logger = get_logger(__name__)

HYPERSPELL_CALENDAR_KEYWORDS = {
    "calendar",
    "schedule",
    "meeting",
    "meetings",
    "appointments",
    "appointment",
    "availability",
    "event",
    "events",
    "reminder",
    "reminders",
}

HYPERSPELL_NOTION_KEYWORDS = {
    "notion",
    "workspace",
    "wiki",
    "knowledge base",
    "knowledgebase",
    "notes",
    "note",
    "docs",
    "document",
    "documents",
    "page",
    "pages",
    "database",
    "roadmap",
    "spec",
    "specs",
    "project plan",
}


def detect_hyperspell_sources(
    user_message: str,
    recent_history: Optional[List[Dict[str, str]]] = None,
) -> List[str]:
    search_targets = [user_message]

    if recent_history:
        user_turns = [msg.get("content", "") for msg in recent_history if msg.get("role") == "user"]
        for content in reversed(user_turns[-2:]):
            search_targets.append(content)

    sources: List[str] = []
    for text in search_targets:
        lowered = text.lower()
        if any(keyword in lowered for keyword in HYPERSPELL_CALENDAR_KEYWORDS):
            if "calendar" not in sources:
                sources.append("calendar")
        if any(keyword in lowered for keyword in HYPERSPELL_NOTION_KEYWORDS):
            if "notion" not in sources:
                sources.append("notion")

    return sources


async def fetch_hyperspell_context(
    session_id: str,
    user_message: str,
    sources: List[str],
    *,
    limit: int = 5,
) -> List[HyperspellMemory]:
    if not (settings.hyperspell_enabled and sources):
        return []

    client = get_hyperspell_client()
    if not client.is_configured:
        return []

    return await client.fetch_context(session_id, user_message, sources=sources, limit=limit)


def schedule_hyperspell_record(
    session_id: str,
    user_message: str,
    assistant_message: str,
    *,
    sources: Optional[List[str]] = None,
    context_used: Optional[List[HyperspellMemory]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    if not settings.hyperspell_enabled:
        return

    client = get_hyperspell_client()
    if not client.supports_recording:
        return

    payload_metadata: Dict[str, Any] = {}
    if metadata:
        payload_metadata.update(metadata)
    if sources:
        payload_metadata.setdefault("sources", sources)
    if context_used:
        payload_metadata["context_used"] = [
            {
                "source": memory.source,
                "title": memory.title,
                "url": memory.url,
                "timestamp": memory.timestamp,
            }
            for memory in context_used
        ]

    async def _record() -> None:
        try:
            await client.record_interaction(
                session_id,
                user_message=user_message,
                assistant_message=assistant_message,
                sources=sources,
                metadata=payload_metadata or None,
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to record interaction with Hyperspell: %s", exc)

    try:
        asyncio.create_task(_record())
    except RuntimeError:
        asyncio.run(_record())


def format_hyperspell_context(memories: List[HyperspellMemory]) -> str:
    if not memories:
        return ""
    return format_memories_for_prompt(memories)
