from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict, List

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .logging import get_logger
from .settings import settings
from .state import (
    archive_notification,
    archived_processes,
    email_inbox,
    email_notifications,
    inbox_cache,
    inbox_cache_lock,
    load_processed_email_ids,
    processed_email_ids,
    save_processed_email_ids,
)


logger = get_logger(__name__)
router = APIRouter()


class ComposeEmail(BaseModel):
    instructions: str


async def send_email(instructions: str) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            settings.railway_email_api,
            json={"instructions": instructions},
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        result = response.json()

    logger.info("Railway API Response: %s", result)

    email_entry = {
        "id": result.get("agentmail_message_id", f"email_{len(email_inbox)}"),
        "message_id": result.get("agentmail_message_id"),
        "to": result.get("email", {}).get("to", ""),
        "subject": result.get("email", {}).get("subject", ""),
        "body": result.get("email", {}).get("body", ""),
        "status": result.get("status", "sent"),
        "timestamp": datetime.now().isoformat(),
        "sent": True,
    }
    email_inbox.insert(0, email_entry)

    asyncio.create_task(refresh_cache_from_api())

    return {"email": email_entry, "response": result}


async def refresh_cache_from_api() -> None:
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                settings.railway_email_inbox_api,
                params={"limit": 100, "summaries": True},
            )
            response.raise_for_status()
            result = response.json()

        await update_inbox_cache(result.get("emails", []))
    except Exception as exc:
        logger.error("Error refreshing inbox cache: %s", exc)


async def update_inbox_cache(received_emails: list) -> None:
    async with inbox_cache_lock:
        processed_received = []
        for email in received_emails or []:
            email_entry = {
                "id": email.get("message_id", f"email_{len(processed_received)}"),
                "message_id": email.get("message_id"),
                "from": email.get("from", ""),
                "subject": email.get("subject", "(No subject)"),
                "body": email.get("text", email.get("html", "")),
                "html": email.get("html", ""),
                "text": email.get("text", ""),
                "thread_id": email.get("thread_id"),
                "timestamp": email.get("received_at", datetime.now().isoformat()),
                "received_at": email.get("received_at"),
                "sent": False,
                "status": "received",
            }
            processed_received.append(email_entry)

        all_emails = processed_received + email_inbox

        def get_sort_key(email: Dict[str, Any]) -> str:
            ts = email.get("received_at") or email.get("timestamp", "")
            return ts if ts else "1970-01-01T00:00:00"

        all_emails.sort(key=get_sort_key, reverse=True)

        inbox_cache["emails"] = all_emails
        inbox_cache["last_updated"] = datetime.now().isoformat()
        inbox_cache["received_count"] = len(processed_received)
        inbox_cache["sent_count"] = len(email_inbox)


@router.post("/api/email/compose-send")
async def compose_and_send_email(email_data: ComposeEmail):
    result = await send_email(email_data.instructions)
    return {"success": True, **result}


@router.get("/api/email/inbox")
async def get_inbox(page: int = 1, per_page: int = 20, summaries: bool = True):
    try:
        async with inbox_cache_lock:
            all_emails = inbox_cache.get("emails", [])
            received_count = inbox_cache.get("received_count", 0)
            sent_count = inbox_cache.get("sent_count", 0)
            last_updated = inbox_cache.get("last_updated")

            total_count = len(all_emails)
            total_pages = (total_count + per_page - 1) // per_page if per_page > 0 else 1
            page = max(1, min(page, total_pages))

            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page

            paginated_emails = all_emails[start_idx:end_idx]

            logger.info(
                "📬 Serving inbox from cache: %s emails (page %s/%s), last updated: %s",
                len(paginated_emails),
                page,
                total_pages,
                last_updated,
            )

            return {
                "success": True,
                "emails": paginated_emails,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": total_count,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_prev": page > 1,
                },
                "received_count": received_count,
                "sent_count": sent_count,
                "cached": True,
                "last_updated": last_updated,
            }
    except Exception as exc:
        logger.error("Error fetching inbox from cache: %s", exc)
        total_count = len(email_inbox)
        per_page = max(1, per_page)
        total_pages = (total_count + per_page - 1) // per_page if per_page > 0 else 1
        page = max(1, min(page, total_pages))
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page

        return {
            "success": True,
            "emails": email_inbox[start_idx:end_idx],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total_count,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            },
            "received_count": 0,
            "sent_count": len(email_inbox),
            "cached": False,
            "error": str(exc),
        }


@router.get("/api/email/last")
async def get_last_email():
    try:
        if not email_inbox:
            return {"success": True, "email": None, "message": "No emails in inbox"}

        return {"success": True, "email": email_inbox[0], "count": len(email_inbox)}
    except Exception as exc:
        logger.error("Error fetching last email: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/api/email/notifications")
async def get_email_notifications():
    try:
        notifications = email_notifications if email_notifications else []
        logger.debug("Returning %s email notifications", len(notifications))
        return {"success": True, "notifications": notifications, "count": len(notifications)}
    except Exception as exc:
        logger.error("Error fetching email notifications: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/api/email/archived")
async def get_archived_processes():
    try:
        archived = archived_processes if archived_processes else []
        archived.sort(key=lambda x: x.get("archived_at", x.get("timestamp", "")), reverse=True)
        logger.debug("Returning %s archived processes", len(archived))
        return {"success": True, "processes": archived, "count": len(archived)}
    except Exception as exc:
        logger.error("Error fetching archived processes: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/api/email/notifications/{notification_id}")
async def clear_email_notification(notification_id: str):
    try:
        notification = next((n for n in email_notifications if n.get("id") == notification_id), None)

        if notification and notification.get("type") == "command":
            if notification.get("status") in ["completed", "failed"]:
                archive_notification(notification)
                logger.info("📦 Archived process %s", notification_id)

        email_notifications[:] = [n for n in email_notifications if n.get("id") != notification_id]

        return {"success": True, "message": "Notification cleared"}
    except Exception as exc:
        logger.error("Error clearing notification: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


async def email_monitor_worker() -> None:
    load_processed_email_ids()

    for notif in email_notifications:
        if notif.get("id"):
            processed_email_ids.add(notif.get("id"))
    for archived in archived_processes:
        if archived.get("id"):
            processed_email_ids.add(archived.get("id"))

    if processed_email_ids:
        logger.info("📋 Initialized processed_email_ids with %s existing email IDs", len(processed_email_ids))
        save_processed_email_ids()

    while True:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    settings.railway_email_inbox_api,
                    params={"limit": 100, "summaries": True},
                )
                response.raise_for_status()
                result = response.json()

                emails = result.get("emails", [])
                logger.info(
                    "📬 Fetched %s emails from API. Currently tracking %s processed emails",
                    len(emails),
                    len(processed_email_ids),
                )

                await update_inbox_cache(emails)

                for email in emails:
                    email_id = email.get("message_id")
                    if not email_id:
                        continue

                    if email_id in processed_email_ids:
                        continue

                    if any(archived.get("id") == email_id for archived in archived_processes):
                        logger.info("✅ Skipping email already in archive: %s", email_id)
                        processed_email_ids.add(email_id)
                        save_processed_email_ids()
                        continue

                    processed_email_ids.add(email_id)
                    save_processed_email_ids()
                    logger.info("📧 Processing new email: %s from %s", email_id, email.get("from", "unknown"))

                    email_body = email.get("text", email.get("html", ""))
                    is_command_email = email_body.strip().upper().startswith("COMMAND: JARVIS")

                    if is_command_email:
                        logger.info("📬 Found command email from %s: %s", email.get("from", "unknown"), email_id)

                        command = email_body.strip()[len("COMMAND: JARVIS") :].strip()

                        notification = {
                            "id": email_id,
                            "type": "command",
                            "from": email.get("from", "Unknown"),
                            "subject": email.get("subject", "(No subject)"),
                            "command": command,
                            "body": email_body[:200],
                            "timestamp": datetime.now().isoformat(),
                            "received_at": email.get("received_at", datetime.now().isoformat()),
                            "status": "scheduled",
                        }
                        email_notifications.append(notification)

                        logger.info("🤖 Scheduling background task for command: %s...", command[:50])
                        asyncio.create_task(process_email_command(email_id, command, notification))
                    else:
                        logger.info("📬 New email from %s: %s", email.get("from", "unknown"), email_id)

                        notification = {
                            "id": email_id,
                            "type": "email",
                            "from": email.get("from", "Unknown"),
                            "subject": email.get("subject", "(No subject)"),
                            "body": email_body[:200],
                            "timestamp": datetime.now().isoformat(),
                            "received_at": email.get("received_at", datetime.now().isoformat()),
                            "status": "received",
                        }
                        email_notifications.append(notification)

        except Exception as exc:
            logger.error("Error in email monitor worker: %s", exc, exc_info=True)

        await asyncio.sleep(30)


async def process_email_command(email_id: str, command: str, notification: dict) -> None:
    try:
        logger.info("⚙️ Processing email command %s: %s...", email_id, command[:50])
        notification["status"] = "processing"

        session_id = f"email_command_{email_id}"

        command_lower = command.lower().strip()
        import re

        compilation_keywords = [
            "compile",
            "create a report",
            "generate a report",
            "make a report",
            "make report",
            "analyze and create",
            "summarize",
            "create a summary",
            "generate a summary",
            "report of",
            "report from",
            "report on",
            "compile from",
            "compile all",
            "gather and compile",
            "collect and summarize",
            "report of it",
            "compile it",
            "make a report of",
            "create a report of",
            "summarize it",
            "compile them",
        ]
        slideshow_keywords = [
            "create.*slideshow",
            "make.*presentation",
            "generate.*slideshow",
            "create.*presentation",
            "build.*presentation",
            "prepare.*presentation",
        ]

        is_compilation = any(keyword in command_lower for keyword in compilation_keywords)
        is_slideshow = any(re.search(keyword.replace("*", ".*"), command_lower) for keyword in slideshow_keywords)

        if is_compilation:
            from .slideshow import execute_iterative_workflow

            try:
                logger.info("📋 Detected compilation workflow for command: %s...", command[:50])
                full_output: List[str] = []

                async for update in execute_iterative_workflow(command, session_id):
                    if update.get("type") == "status":
                        notification["progress"] = update.get("message", "")
                        logger.info("📊 Progress: %s", update.get("message", ""))
                    elif update.get("type") == "result":
                        full_output.append(update.get("content", ""))
                    elif update.get("type") == "error":
                        raise Exception(update.get("message", "Workflow error"))

                notification["status"] = "completed"
                notification["completed_at"] = datetime.now().isoformat()
                notification["response"] = "\n".join(full_output) if full_output else "Report compilation completed successfully"
                logger.info("✅ Email command %s completed successfully (compilation workflow)", email_id)
            except Exception as exc:
                notification["status"] = "failed"
                notification["failed_at"] = datetime.now().isoformat()
                notification["error"] = str(exc)
                logger.error("❌ Email command %s failed (compilation workflow): %s", email_id, exc)
        elif is_slideshow:
            from .slideshow import execute_slideshow_workflow

            try:
                logger.info("🎬 Detected slideshow workflow for command: %s...", command[:50])
                full_output: List[str] = []

                async for update in execute_slideshow_workflow(command, session_id):
                    if update.get("type") == "status":
                        notification["progress"] = update.get("message", "")
                        logger.info("📊 Progress: %s", update.get("message", ""))
                    elif update.get("type") == "result":
                        full_output.append(update.get("content", ""))
                    elif update.get("type") == "error":
                        raise Exception(update.get("message", "Workflow error"))

                notification["status"] = "completed"
                notification["completed_at"] = datetime.now().isoformat()
                notification["response"] = "\n".join(full_output) if full_output else "Slideshow created successfully"
                logger.info("✅ Email command %s completed successfully (slideshow workflow)", email_id)
            except Exception as exc:
                notification["status"] = "failed"
                notification["failed_at"] = datetime.now().isoformat()
                notification["error"] = str(exc)
                logger.error("❌ Email command %s failed (slideshow workflow): %s", email_id, exc)
        else:
            try:
                from .chat import process_chat_message

                result = await process_chat_message(command, session_id, skip_streaming=True)

                notification["status"] = "completed"
                notification["completed_at"] = datetime.now().isoformat()
                notification["response"] = result.get("response", "Command executed successfully")
                logger.info("✅ Email command %s completed successfully", email_id)
            except Exception as exc:
                notification["status"] = "failed"
                notification["failed_at"] = datetime.now().isoformat()
                notification["error"] = str(exc)
                logger.error("❌ Email command %s failed: %s", email_id, exc, exc_info=True)

    except Exception as exc:
        logger.error("Error processing email command %s: %s", email_id, exc, exc_info=True)
        notification["status"] = "failed"
        notification["failed_at"] = datetime.now().isoformat()
        notification["error"] = str(exc)

    if email_id not in processed_email_ids:
        processed_email_ids.add(email_id)
        save_processed_email_ids()
        logger.debug("✅ Added %s to processed_email_ids to prevent reprocessing", email_id)
