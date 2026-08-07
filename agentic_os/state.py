from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .logging import get_logger
from .settings import settings


logger = get_logger(__name__)

# Conversation memory storage (in-memory, per session)
conversation_history: Dict[str, List[Dict[str, str]]] = {}

# Email storage (in-memory)
email_inbox: List[Dict[str, Any]] = []

# Email monitoring for command emails
processed_email_ids: set[str] = set()
email_monitor_task = None
email_notifications: List[Dict[str, Any]] = []
archived_processes: List[Dict[str, Any]] = []

# Inbox cache for faster loading
inbox_cache: Dict[str, Any] = {
    "emails": [],
    "last_updated": None,
    "received_count": 0,
    "sent_count": 0,
}
inbox_cache_lock = asyncio.Lock()

# Browser state
browser_instance = None
browser_contexts: Dict[str, Any] = {}
browser_agents: Dict[str, Dict[str, Any]] = {}
agent_task_registry: Dict[str, Any] = {}

# Phone-to-PC demo dashboard state
demo_project_state: Dict[str, Any] = {
    "projects": [
        {
            "id": "mobile-demo",
            "name": "phone voice shell",
            "path": "/nexus/mobile-demo",
            "status": "active",
            "dirs": ["android-app/", "agentic_os/", "static/"],
            "scripts": ["deploy_preview.sh", "run_backend.sh", "inspect_device.sh"],
        },
        {
            "id": "web-dashboard",
            "name": "web dashboard",
            "path": "/projects/site-lab",
            "status": "watching",
            "dirs": ["templates/", "static/", "routes/"],
            "scripts": ["sync_agent_events.sh", "preview_ui.sh"],
        },
        {
            "id": "model-lab",
            "name": "agent model lab",
            "path": "/experiments/nexus-agent",
            "status": "idle",
            "dirs": ["prompts/", "evals/", "tools/"],
            "scripts": ["score_responses.sh", "package_context.sh"],
        },
    ],
    "events": [],
    "active_project": "mobile-demo",
    "last_updated": None,
}


PROCESSED_EMAILS_FILE: Path = settings.processed_emails_file


def save_processed_email_ids() -> None:
    try:
        with open(PROCESSED_EMAILS_FILE, "w", encoding="utf-8") as f:
            json.dump(list(processed_email_ids), f)
        logger.debug("💾 Saved %s processed email IDs to file", len(processed_email_ids))
    except Exception as exc:
        logger.error("Error saving processed email IDs: %s", exc, exc_info=True)


def load_processed_email_ids() -> None:
    global processed_email_ids
    try:
        if PROCESSED_EMAILS_FILE.exists():
            with open(PROCESSED_EMAILS_FILE, "r", encoding="utf-8") as f:
                email_ids = json.load(f)
                processed_email_ids = set(email_ids)
            logger.info("📂 Loaded %s processed email IDs from file", len(processed_email_ids))
        else:
            logger.info("📂 No processed email IDs file found, starting fresh")
    except Exception as exc:
        logger.error("Error loading processed email IDs: %s", exc, exc_info=True)
        processed_email_ids = set()


def get_conversation_history(session_id: str, max_pairs: int = 4) -> List[Dict[str, str]]:
    if session_id not in conversation_history:
        return []

    history = conversation_history[session_id]
    return history[-(max_pairs * 2) :] if len(history) > max_pairs * 2 else history


def add_to_conversation_history(session_id: str, user_message: str, assistant_response: str) -> None:
    if session_id not in conversation_history:
        conversation_history[session_id] = []

    conversation_history[session_id].append({"role": "user", "content": user_message})
    conversation_history[session_id].append({"role": "assistant", "content": assistant_response})

    max_messages = 4 * 2
    if len(conversation_history[session_id]) > max_messages:
        conversation_history[session_id] = conversation_history[session_id][-max_messages:]


def archive_notification(notification: Dict[str, Any]) -> None:
    archived = {
        **notification,
        "archived_at": datetime.now().isoformat(),
    }
    archived_processes.append(archived)
