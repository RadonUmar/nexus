from __future__ import annotations

import asyncio
import base64
import json
import random
import re
import string
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel
from playwright.async_api import Browser, Page, async_playwright

from .clients import openai_client
from .files import DATA_DIR
from .logging import get_logger
from .state import (
    agent_task_registry,
    browser_agents,
    browser_contexts,
    browser_instance,
)


logger = get_logger(__name__)
router = APIRouter()


class BrowserNavigate(BaseModel):
    url: str
    session_id: Optional[str] = "default"
    agent_goal: Optional[str] = None


class BrowserNavigateMultiple(BaseModel):
    urls: list[str]
    session_ids: Optional[list[str]] = None
    agent_goals: Optional[list[str]] = []


class BrowserAction(BaseModel):
    action: str
    x: Optional[int] = None
    y: Optional[int] = None
    text: Optional[str] = None
    session_id: Optional[str] = "default"


class BrowserControl(BaseModel):
    command: str
    session_id: Optional[str] = "default"


async def init_browser() -> None:
    global browser_instance
    try:
        playwright = await async_playwright().start()
        browser_instance = await playwright.chromium.launch(headless=True)
        logger.info("Playwright browser initialized")
    except Exception as exc:
        logger.error("Failed to initialize browser: %s", exc)
        browser_instance = None


async def get_browser_page(session_id: str = "default") -> Optional[Page]:
    global browser_instance
    if not browser_instance:
        await init_browser()

    if not browser_instance:
        return None

    if session_id not in browser_contexts:
        browser_contexts[session_id] = await browser_instance.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )

    context = browser_contexts[session_id]
    pages = context.pages
    if pages:
        return pages[0]
    return await context.new_page()


async def browser_agent_worker(session_id: str) -> None:
    logger.info("🤖 Browser agent [%s] STARTED - Running autonomously", session_id)

    try:
        while True:
            if session_id not in browser_agents:
                await asyncio.sleep(1)
                continue

            agent = browser_agents[session_id]

            if not agent.get("current_goal") and len(agent.get("tasks", deque())) == 0:
                agent["status"] = "idle"
                await asyncio.sleep(1)
                continue

            if agent.get("current_goal"):
                agent["status"] = "thinking"

                page = await get_browser_page(session_id)
                if not page:
                    logger.warning("⚠️  Agent [%s]: No browser page available", session_id)
                    await asyncio.sleep(2)
                    continue

                current_url = page.url
                logger.info("🤖 Agent [%s] at %s - Goal: %s", session_id, current_url, agent["current_goal"])

                agent["status"] = "analyzing"
                agent_log = {
                    "timestamp": datetime.now().isoformat(),
                    "action": "analyzing",
                    "message": f"Analyzing page at {current_url}",
                }
                agent["logs"].append(agent_log)

                await asyncio.sleep(1)
                screenshot_bytes = await page.screenshot(full_page=False)
                screenshot_base64 = base64.b64encode(screenshot_bytes).decode("utf-8")

                agent["status"] = "planning"
                agent_log = {
                    "timestamp": datetime.now().isoformat(),
                    "action": "planning",
                    "message": "Planning next action to achieve goal",
                }
                agent["logs"].append(agent_log)

                system_prompt = f"""You are an autonomous browser agent working on a specific task.

YOUR CURRENT GOAL: {agent.get('current_goal', 'Unknown')}

You must analyze the current page and decide what action to take next. Available actions:
1. click - Click on an element (provide x, y coordinates)
2. type - Type text in an input field (provide text and coordinates)
3. scroll - Scroll the page (provide x, y scroll amounts)
4. done - Mark task as complete if goal is achieved

IMPORTANT: If your goal involves extracting information and creating/saving files:
- Read the page content carefully
- Extract all relevant information systematically
- When ready to save, you can indicate completion and the system will help create the file
- Be thorough - extract all requested information before marking as done

You should:
- Work systematically toward your goal
- Read and understand page content thoroughly
- Extract information comprehensively if extraction is part of the goal
- Navigate pages as necessary (click links, scroll to see more content)
- Continue working until goal is achieved or you determine it cannot be completed
- Provide detailed progress updates

Return ONLY a JSON object:
{{
  "action": "click" | "type" | "scroll" | "done",
  "x": number (for click/scroll),
  "y": number (for click/scroll),
  "text": "string" (for type action),
  "description": "brief description of what you're doing",
  "goal_progress": "what progress have you made toward the goal? Include specific details of what information you've found.",
  "next_steps": "what will you do next?"
}}

Be precise with coordinates for the 1280x720 viewport."""

                vision_messages = [
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    f"Current URL: {current_url}\n\n"
                                    f"Analyze this page screenshot and determine the next action to work toward: {agent.get('current_goal', 'Unknown')}"
                                ),
                            },
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{screenshot_base64}"}},
                        ],
                    },
                ]

                try:
                    vision_response = openai_client.chat.completions.create(
                        model="gpt-5-2025-08-07",
                        messages=vision_messages,
                        reasoning_effort="medium",
                        verbosity="medium",
                        response_format={"type": "json_object"},
                    )

                    vision_result = json.loads(vision_response.choices[0].message.content)
                    action_type = vision_result.get("action", "wait")
                    description = vision_result.get("description", "")
                    goal_progress = vision_result.get("goal_progress", "")
                    next_steps = vision_result.get("next_steps", "")

                    agent_log = {
                        "timestamp": datetime.now().isoformat(),
                        "action": action_type,
                        "message": description,
                        "progress": goal_progress,
                        "next": next_steps,
                    }
                    agent["logs"].append(agent_log)
                    logger.info("🎯 Agent [%s]: %s", session_id, description)
                    if goal_progress:
                        logger.info("   📊 Progress: %s", goal_progress)
                    if next_steps:
                        logger.info("   ➡️  Next: %s", next_steps)

                    agent["status"] = "executing"

                    if action_type == "done":
                        logger.info("✅ Agent [%s]: Task complete! Goal achieved.", session_id)

                        goal_lower = agent.get("current_goal", "").lower()
                        if any(key in goal_lower for key in ["extract", "create", "save", "doc"]):
                            try:
                                page_text = await page.evaluate(
                                    """() => {
                                    const content = document.querySelector('main') ||
                                                   document.querySelector('article') ||
                                                   document.querySelector('#content') ||
                                                   document.querySelector('.mw-parser-output') ||
                                                   document.body;
                                    return content.innerText || content.textContent || '';
                                }"""
                                )

                                if page_text:
                                    extraction_prompt = (
                                        "Extract and format the information from this webpage content according to the goal: "
                                        f"{agent.get('current_goal', '')}\n\n"
                                        "Content:\n"
                                        f"{page_text[:15000]}\n\n"
                                        "Format the extracted information clearly and comprehensively. If creating a document, structure it appropriately."
                                    )

                                    extraction_response = openai_client.chat.completions.create(
                                        model="gpt-4.1-2025-04-14",
                                        messages=[
                                            {"role": "system", "content": "You are a document extraction assistant. Extract and format information clearly."},
                                            {"role": "user", "content": extraction_prompt},
                                        ],
                                        temperature=0.7,
                                    )

                                    extracted_content = extraction_response.choices[0].message.content

                                    page_title = await page.title()
                                    safe_title = re.sub(r"[^\w\s-]", "", page_title)[:30].replace(" ", "_")

                                    filename = "extracted_info.txt"
                                    if "word" in goal_lower or "doc" in goal_lower:
                                        filename = f"{safe_title}_info.txt"
                                    else:
                                        filename = f"{safe_title}_extracted.txt"

                                    safe_path = Path("Desktop") / filename
                                    target_file = DATA_DIR / safe_path
                                    target_file.parent.mkdir(parents=True, exist_ok=True)
                                    target_file.write_text(extracted_content, encoding="utf-8")

                                    logger.info("📄 Agent [%s]: Created file %s with extracted content", session_id, filename)
                                    agent["logs"].append(
                                        {
                                            "timestamp": datetime.now().isoformat(),
                                            "action": "done",
                                            "message": f"Task completed successfully. Created file: {filename}",
                                        }
                                    )
                                else:
                                    agent["logs"].append(
                                        {
                                            "timestamp": datetime.now().isoformat(),
                                            "action": "done",
                                            "message": "Task completed successfully",
                                        }
                                    )
                            except Exception as exc:
                                logger.error("❌ Agent [%s] error creating file: %s", session_id, exc)
                                agent["logs"].append(
                                    {
                                        "timestamp": datetime.now().isoformat(),
                                        "action": "error",
                                        "message": f"Error creating file: {str(exc)}",
                                    }
                                )
                        else:
                            agent["logs"].append(
                                {
                                    "timestamp": datetime.now().isoformat(),
                                    "action": "done",
                                    "message": "Task completed successfully",
                                }
                            )

                        agent["current_goal"] = None
                        agent["status"] = "completed"
                        await asyncio.sleep(5)
                    elif action_type == "click":
                        x = vision_result.get("x", 0)
                        y = vision_result.get("y", 0)
                        logger.info("🖱️  Agent [%s]: Clicking at (%s, %s)", session_id, x, y)
                        await page.mouse.click(x, y)
                        await page.wait_for_timeout(1500)
                    elif action_type == "type":
                        text = vision_result.get("text", "")
                        x = vision_result.get("x")
                        y = vision_result.get("y")

                        logger.info("⌨️  Agent [%s]: Typing '%s'", session_id, text)
                        if x is not None and y is not None:
                            await page.mouse.click(x, y)
                            await page.wait_for_timeout(300)

                        if text:
                            await page.keyboard.type(text, delay=50)
                            await page.wait_for_timeout(800)

                            if "search" in agent.get("current_goal", "").lower() or page.url == "https://www.google.com/" or "google.com" in page.url:
                                logger.info("🔍 Agent [%s]: Pressing Enter to search", session_id)
                                await page.keyboard.press("Enter")
                                await page.wait_for_timeout(3000)
                    elif action_type == "scroll":
                        scroll_x = vision_result.get("x", 0)
                        scroll_y = vision_result.get("y", 0)
                        logger.info("📜 Agent [%s]: Scrolling (%s, %s)", session_id, scroll_x, scroll_y)
                        await page.mouse.wheel(scroll_x, scroll_y)
                        await page.wait_for_timeout(1000)

                    await page.wait_for_timeout(1000)
                    agent["status"] = "idle"
                    await asyncio.sleep(1)

                except Exception as exc:
                    logger.error("❌ Agent [%s] error during action: %s", session_id, exc)
                    agent["logs"].append(
                        {
                            "timestamp": datetime.now().isoformat(),
                            "action": "error",
                            "message": f"Error: {str(exc)}",
                        }
                    )
                    agent["status"] = "error"
                    await asyncio.sleep(2)

            else:
                if len(agent.get("tasks", deque())) > 0:
                    task = agent["tasks"].popleft()
                    agent["current_goal"] = task.get("goal", task.get("command", ""))
                    logger.info("📋 Agent [%s]: New task queued - %s", session_id, agent["current_goal"])
                else:
                    agent["status"] = "idle"
                    await asyncio.sleep(1)

    except asyncio.CancelledError:
        logger.info("🛑 Browser agent [%s] STOPPED", session_id)
    except Exception as exc:
        logger.error("💥 Agent [%s] FATAL ERROR: %s", session_id, exc)
        if session_id in browser_agents:
            browser_agents[session_id]["status"] = "error"
            browser_agents[session_id]["logs"].append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "action": "fatal_error",
                    "message": f"Fatal error: {str(exc)}",
                }
            )


def start_browser_agent(session_id: str, initial_goal: Optional[str] = None) -> None:
    if session_id in agent_task_registry:
        if initial_goal and session_id in browser_agents:
            browser_agents[session_id]["current_goal"] = initial_goal
            if "logs" not in browser_agents[session_id]:
                browser_agents[session_id]["logs"] = []
            browser_agents[session_id]["logs"].append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "action": "goal_set",
                    "message": f"New goal set: {initial_goal}",
                }
            )
            logger.info("📝 Agent [%s]: Goal updated to '%s'", session_id, initial_goal)
        return

    async def run_agent() -> None:
        await browser_agent_worker(session_id)

    task = asyncio.create_task(run_agent())
    agent_task_registry[session_id] = task
    browser_agents[session_id] = {
        "tasks": deque(),
        "status": "starting",
        "current_goal": initial_goal or "",
        "logs": [
            {
                "timestamp": datetime.now().isoformat(),
                "action": "started",
                "message": f"Agent started with goal: {initial_goal or 'No initial goal'}",
            }
        ],
    }
    logger.info("🚀 Started browser agent [%s] with goal: %s", session_id, initial_goal or "")


@router.get("/api/browser/agent/{session_id}")
async def get_browser_agent_status(session_id: str):
    if session_id not in browser_agents:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent = browser_agents[session_id]
    return {
        "session_id": session_id,
        "status": agent.get("status", "unknown"),
        "current_goal": agent.get("current_goal", ""),
        "logs": agent.get("logs", [])[-50:],
        "task_count": len(agent.get("tasks", deque())),
    }


@router.get("/api/browser/agents")
async def get_all_browser_agents():
    agents_status = {}
    for session_id, agent in browser_agents.items():
        agents_status[session_id] = {
            "status": agent.get("status", "unknown"),
            "current_goal": agent.get("current_goal", ""),
            "log_count": len(agent.get("logs", [])),
            "latest_log": agent.get("logs", [])[-1] if agent.get("logs") else None,
        }
    return {"agents": agents_status}


@router.post("/api/browser/navigate-multiple")
async def browser_navigate_multiple(nav_data: BrowserNavigateMultiple):
    try:
        urls = nav_data.urls or []
        agent_goals = nav_data.agent_goals or []

        if not urls:
            raise HTTPException(status_code=400, detail="No URLs provided")

        results = []

        for idx, target_url in enumerate(urls):
            if not target_url.startswith(("http://", "https://")):
                target_url = f"https://{target_url}"

            session_id = f"browser_{int(time.time() * 1000)}_{''.join(random.choices(string.ascii_lowercase + string.digits, k=10))}"

            page = await get_browser_page(session_id)
            if not page:
                raise HTTPException(status_code=500, detail="Browser not available")

            await page.goto(target_url, wait_until="domcontentloaded", timeout=30000)

            current_url = page.url
            title = await page.title()
            proxy_url = f"/api/browser/proxy/{session_id}/"

            agent_goal = None
            if idx < len(agent_goals) and agent_goals[idx]:
                agent_goal = f"Search for and find information about {agent_goals[idx]}"
                start_browser_agent(session_id, initial_goal=agent_goal)
                logger.info("🤖 Started agent [%s] with goal: %s", session_id, agent_goal)

            results.append(
                {
                    "session_id": session_id,
                    "url": current_url,
                    "title": title,
                    "proxy_url": proxy_url,
                    "agent_goal": agent_goal,
                }
            )

        return {"success": True, "results": results, "multiple": len(results) > 1}
    except Exception as exc:
        logger.error("Error navigating multiple browsers: %s", exc)
        raise HTTPException(status_code=500, detail=f"Error: {str(exc)}")


@router.post("/api/browser/navigate")
async def browser_navigate(nav_data: BrowserNavigate):
    try:
        page = await get_browser_page(nav_data.session_id)
        if not page:
            raise HTTPException(status_code=500, detail="Browser not available")

        url = nav_data.url
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        await page.goto(url, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(1000)

        current_url = page.url
        title = await page.title()

        parsed_url = urlparse(current_url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        browser_contexts[nav_data.session_id + "_base_url"] = base_url
        browser_contexts[nav_data.session_id + "_current_url"] = current_url

        agent_goal = nav_data.agent_goal
        if agent_goal:
            start_browser_agent(nav_data.session_id, initial_goal=agent_goal)
            logger.info("🤖 Started agent [%s] with goal: %s", nav_data.session_id, agent_goal)

        return {
            "success": True,
            "url": current_url,
            "title": title,
            "proxy_url": f"/api/browser/proxy/{nav_data.session_id}/",
            "agent_goal": agent_goal,
        }
    except Exception as exc:
        logger.error("Error navigating browser: %s", exc)
        raise HTTPException(status_code=500, detail=f"Error: {str(exc)}")


@router.get("/api/browser/proxy/{session_id}/")
async def browser_proxy_page(session_id: str, request: Request):
    try:
        page = await get_browser_page(session_id)
        if not page:
            raise HTTPException(status_code=500, detail="Browser not available")

        html_content = await page.content()
        current_url = page.url
        base_url = browser_contexts.get(session_id + "_base_url", current_url)

        import re as re_module

        def rewrite_url(match):
            attr = match.group(1)
            quote = match.group(2)
            url = match.group(3)

            if not url:
                return match.group(0)

            if url.startswith(("data:", "javascript:", "mailto:", "#", "about:", "{")):
                return match.group(0)

            if url.startswith("//"):
                url = urlparse(current_url).scheme + ":" + url
            elif url.startswith("/"):
                url = base_url + url
            elif not url.startswith(("http://", "https://")):
                url = urljoin(current_url, url)

            from urllib.parse import quote as url_quote

            proxy_path = f"/api/browser/resource/{session_id}"
            encoded_url = url_quote(url, safe="")
            return f"{attr}={quote}{proxy_path}?url={encoded_url}{quote}"

        html_content = re_module.sub(r"(src|href)=(['\"])([^'\"]+)\2", rewrite_url, html_content)

        if "<head>" in html_content:
            html_content = html_content.replace("<head>", f"<head><base href=\"{current_url}\">")

        return HTMLResponse(content=html_content)
    except Exception as exc:
        logger.error("Error proxying page: %s", exc)
        raise HTTPException(status_code=500, detail=f"Error: {str(exc)}")


@router.get("/api/browser/resource/{session_id}")
async def browser_proxy_resource(session_id: str, url: str, request: Request):
    try:
        page = await get_browser_page(session_id)
        if not page:
            raise HTTPException(status_code=500, detail="Browser not available")

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            headers = {}
            cookies = await page.context.cookies()
            for cookie in cookies:
                client.cookies.set(cookie["name"], cookie["value"], domain=cookie.get("domain", ""))

            response = await client.get(url, headers=headers)
            response.raise_for_status()

            content_type = response.headers.get("content-type", "application/octet-stream")

            return Response(
                content=response.content,
                media_type=content_type,
                headers={"Cache-Control": "public, max-age=3600"},
            )
    except Exception as exc:
        logger.error("Error proxying resource %s: %s", url, exc)
        raise HTTPException(status_code=500, detail=f"Error: {str(exc)}")


@router.post("/api/browser/control")
async def browser_control(control_data: BrowserControl):
    try:
        command = control_data.command
        session_id_param = control_data.session_id or "default"

        page = await get_browser_page(session_id_param)
        if not page:
            raise HTTPException(status_code=500, detail="Browser not available")

        screenshot_bytes = await page.screenshot(full_page=False)
        screenshot_base64 = base64.b64encode(screenshot_bytes).decode("utf-8")

        vision_messages = [
            {
                "role": "system",
                "content": """You are a browser automation assistant. Analyze the screenshot and user command to determine what action to take.

Available actions:
1. click - Click on an element (provide x, y coordinates)
2. type - Type text (provide text to type, and optionally x, y coordinates of input field)
3. scroll - Scroll the page (provide x, y scroll amounts)

Return ONLY a JSON object with this exact format:
{
  "action": "click" | "type" | "scroll",
  "x": number (for click, or x scroll amount),
  "y": number (for click, or y scroll amount),
  "text": "string" (for type action only),
  "description": "brief description of what you're doing"
}

For clicking, identify the element described in the command and provide its approximate center coordinates.
For typing, identify the input field and provide coordinates to click it first, then the text to type.
For scrolling, provide appropriate scroll amounts (typically y: -300 to scroll down, y: 300 to scroll up).
Be precise with coordinates - they should match pixel positions in the 1280x720 viewport.""",
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"User command: {command}\n\nAnalyze this browser screenshot and determine the appropriate action with coordinates.",
                    },
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{screenshot_base64}"}},
                ],
            },
        ]

        vision_response = openai_client.chat.completions.create(
            model="gpt-5-2025-08-07",
            messages=vision_messages,
            reasoning_effort="medium",
            verbosity="medium",
            response_format={"type": "json_object"},
        )

        vision_result = json.loads(vision_response.choices[0].message.content)
        action_type = vision_result.get("action", "wait")

        if action_type == "click":
            x = vision_result.get("x", 0)
            y = vision_result.get("y", 0)
            await page.mouse.click(x, y)
            await page.wait_for_timeout(500)
        elif action_type == "type":
            text = vision_result.get("text", "")
            x = vision_result.get("x")
            y = vision_result.get("y")

            if x is not None and y is not None:
                await page.mouse.click(x, y)
                await page.wait_for_timeout(300)

            if text:
                await page.keyboard.type(text)
                await page.wait_for_timeout(500)
        elif action_type == "scroll":
            scroll_x = vision_result.get("x", 0)
            scroll_y = vision_result.get("y", 0)
            await page.mouse.wheel(scroll_x, scroll_y)
            await page.wait_for_timeout(500)

        await page.wait_for_timeout(1000)

        current_url = page.url
        title = await page.title()

        return {
            "success": True,
            "url": current_url,
            "title": title,
            "proxy_url": f"/api/browser/proxy/{session_id_param}/",
        }
    except Exception as exc:
        logger.error("Error in browser control: %s", exc)
        raise HTTPException(status_code=500, detail=f"Error: {str(exc)}")


@router.post("/api/browser/action")
async def browser_action(action_data: BrowserAction):
    try:
        page = await get_browser_page(action_data.session_id)
        if not page:
            raise HTTPException(status_code=500, detail="Browser not available")

        if action_data.action == "click":
            if action_data.x is not None and action_data.y is not None:
                await page.mouse.click(action_data.x, action_data.y)
            else:
                raise HTTPException(status_code=400, detail="x and y coordinates required for click")
        elif action_data.action == "type":
            if action_data.text:
                await page.keyboard.type(action_data.text)
            else:
                raise HTTPException(status_code=400, detail="text required for type action")
        elif action_data.action == "scroll":
            scroll_x = action_data.x or 0
            scroll_y = action_data.y or 0
            await page.mouse.wheel(scroll_x, scroll_y)
        elif action_data.action == "back":
            await page.go_back()
        elif action_data.action == "forward":
            await page.go_forward()
        elif action_data.action == "reload":
            await page.reload()
            current_url = page.url
            parsed_url = urlparse(current_url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            browser_contexts[action_data.session_id + "_base_url"] = base_url
            browser_contexts[action_data.session_id + "_current_url"] = current_url
        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {action_data.action}")

        await page.wait_for_timeout(500)

        current_url = page.url
        title = await page.title()

        return {
            "success": True,
            "url": current_url,
            "title": title,
            "proxy_url": f"/api/browser/proxy/{action_data.session_id}/",
        }
    except Exception as exc:
        logger.error("Error performing browser action: %s", exc)
        raise HTTPException(status_code=500, detail=f"Error: {str(exc)}")
