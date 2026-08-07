from __future__ import annotations

import asyncio
import io
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any, AsyncGenerator, Dict

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse

from .chat import process_chat_message
from .files import DATA_DIR
from .logging import get_logger


logger = get_logger(__name__)
router = APIRouter(prefix="/phone", tags=["phone-relay"])

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _iter_data_files() -> list[Path]:
    """Return all files under DATA_DIR sorted by modification time (newest first)."""
    return sorted(
        (p for p in DATA_DIR.rglob("*") if p.is_file()),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )


def _rel(path: Path) -> str:
    return path.relative_to(DATA_DIR).as_posix()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/command")
async def relay_command(request: Request) -> JSONResponse:
    """
    Accept a plain-text or JSON command from the phone and run it through
    the Agentic OS chat pipeline.

    Body (JSON):  {"message": "create a file hello.txt with hello world"}
    Body (text):  the raw command string
    """
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        body: Dict[str, Any] = await request.json()
        message = str(body.get("message", "")).strip()
    else:
        raw = await request.body()
        message = raw.decode("utf-8", errors="replace").strip()

    if not message:
        raise HTTPException(status_code=400, detail="No message provided")

    session_id = request.headers.get("X-Session-Id", "phone-relay")

    result = await process_chat_message(message, session_id, skip_streaming=True)

    if isinstance(result, StreamingResponse):
        # Shouldn't reach here (skip_streaming=True) but handle gracefully
        return JSONResponse({"response": "Command queued for streaming.", "action": None, "data": {}})

    return JSONResponse(content=result)


@router.post("/claude")
async def relay_to_claude(request: Request) -> StreamingResponse:
    """
    Run an arbitrary prompt directly through the `claude` CLI (Claude Code) and
    stream the output back line-by-line as SSE.

    Body (JSON):  {"prompt": "write a python script that …"}
    """
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        body = await request.json()
        prompt: str = str(body.get("prompt", "")).strip()
    else:
        raw = await request.body()
        prompt = raw.decode("utf-8", errors="replace").strip()

    if not prompt:
        raise HTTPException(status_code=400, detail="No prompt provided")

    async def _stream() -> AsyncGenerator[str, None]:
        yield f"data: {json.dumps({'type': 'start', 'prompt': prompt})}\n\n"

        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable, "-m", "claude_code", "--print", prompt,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=str(Path(__file__).resolve().parent.parent),
            )

            # Fall back: try `claude` binary on PATH
        except FileNotFoundError:
            try:
                proc = await asyncio.create_subprocess_exec(
                    "claude", "--print", prompt,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                    cwd=str(Path(__file__).resolve().parent.parent),
                )
            except FileNotFoundError:
                yield f"data: {json.dumps({'type': 'error', 'message': 'claude CLI not found on PATH'})}\n\n"
                return

        assert proc.stdout is not None
        async for line in proc.stdout:
            text = line.decode("utf-8", errors="replace").rstrip("\n")
            yield f"data: {json.dumps({'type': 'output', 'line': text})}\n\n"

        await proc.wait()
        yield f"data: {json.dumps({'type': 'done', 'returncode': proc.returncode})}\n\n"

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/files")
async def list_files_for_phone() -> JSONResponse:
    """List all files available for download."""
    files = []
    for path in _iter_data_files():
        stat = path.stat()
        files.append({
            "name": path.name,
            "path": _rel(path),
            "size": stat.st_size,
            "modified": stat.st_mtime,
            "download_url": f"/phone/download?path={_rel(path)}",
        })
    return JSONResponse({"files": files, "count": len(files)})


@router.get("/download")
async def download_file(path: str = Query(..., description="Relative path under data/")) -> Response:
    """Download a single file from the data directory."""
    target = (DATA_DIR / Path(path)).resolve()
    try:
        target.relative_to(DATA_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    content = target.read_bytes()
    media_type = "application/octet-stream"
    if target.suffix in {".txt", ".md", ".csv", ".log"}:
        media_type = "text/plain; charset=utf-8"
    elif target.suffix == ".json":
        media_type = "application/json"
    elif target.suffix == ".html":
        media_type = "text/html"
    elif target.suffix in {".png", ".jpg", ".jpeg", ".gif", ".webp"}:
        media_type = f"image/{target.suffix.lstrip('.')}"

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{target.name}"'},
    )


@router.get("/download-all")
async def download_all_as_zip() -> StreamingResponse:
    """Zip all files in the data directory and stream the archive."""

    def _build_zip() -> bytes:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for path in _iter_data_files():
                zf.write(path, arcname=_rel(path))
        return buf.getvalue()

    loop = asyncio.get_event_loop()
    zip_bytes = await loop.run_in_executor(None, _build_zip)

    return StreamingResponse(
        iter([zip_bytes]),
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="agentic_os_files.zip"'},
    )
