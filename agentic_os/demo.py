from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import APIRouter
from pydantic import BaseModel

from . import state


router = APIRouter(prefix="/api/demo", tags=["demo"])


class DemoCommandRequest(BaseModel):
    command: str
    kind: Optional[str] = None
    project_id: Optional[str] = None
    script: Optional[str] = None
    feedback: Optional[str] = None
    source: str = "phone"


def classify_demo_command(message: str) -> Dict[str, str]:
    text = message.lower()
    if any(phrase in text for phrase in ["feedback", "review", "comment", "note"]):
        return {
            "kind": "feedback",
            "script": "review_notes.md",
            "feedback": "Voice feedback captured for the active project.",
        }
    if any(phrase in text for phrase in ["inspect", "device", "phone"]):
        return {"kind": "script", "script": "inspect_device.sh"}
    if any(phrase in text for phrase in ["backend", "server"]):
        return {"kind": "script", "script": "run_backend.sh"}
    return {"kind": "script", "script": "deploy_preview.sh"}


def record_demo_command(payload: DemoCommandRequest | Dict[str, Any]) -> Dict[str, Any]:
    if isinstance(payload, dict):
        payload = DemoCommandRequest(**payload)

    classified = classify_demo_command(payload.command)
    kind = payload.kind or classified["kind"]
    script = payload.script or classified.get("script", "deploy_preview.sh")
    project_id = payload.project_id or state.demo_project_state["active_project"]
    feedback = payload.feedback or classified.get("feedback")

    project = next(
        (item for item in state.demo_project_state["projects"] if item["id"] == project_id),
        state.demo_project_state["projects"][0],
    )
    project["status"] = "feedback queued" if kind == "feedback" else "script queued"
    timestamp = datetime.now().isoformat(timespec="seconds")
    event = {
        "id": uuid4().hex[:8],
        "time": timestamp,
        "source": payload.source,
        "kind": kind,
        "project_id": project["id"],
        "project": project["name"],
        "script": script,
        "command": payload.command,
        "feedback": feedback,
        "status": "queued",
    }

    state.demo_project_state["events"].insert(0, event)
    state.demo_project_state["events"] = state.demo_project_state["events"][:12]
    state.demo_project_state["active_project"] = project["id"]
    state.demo_project_state["last_updated"] = timestamp
    return event


def is_demo_project_command(message: str) -> bool:
    text = message.lower()
    return any(
        phrase in text
        for phrase in [
            "run this script",
            "run the script",
            "run a script",
            "project script",
            "send a command",
            "command to my pc",
            "upload script",
            "upload code",
            "give feedback",
            "project feedback",
        ]
    )


@router.get("/projects")
async def get_demo_projects() -> Dict[str, Any]:
    return state.demo_project_state


@router.post("/commands")
async def create_demo_command(request: DemoCommandRequest) -> Dict[str, Any]:
    event = record_demo_command(request)
    return {"ok": True, "event": event, "state": state.demo_project_state}
