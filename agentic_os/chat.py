from __future__ import annotations

import asyncio
import base64
import json
import re
from typing import Any, Dict, List
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

from .clients import anthropic_client
from .demo import DemoCommandRequest, is_demo_project_command, record_demo_command
from .email import send_email
from .files import (
    create_file,
    delete_item,
    find_files,
    get_available_files,
    list_files,
    read_files,
)
from .hyperspell_context import (
    detect_hyperspell_sources,
    fetch_hyperspell_context,
    format_hyperspell_context,
    schedule_hyperspell_record,
)
from .logging import get_logger
from .prompts import build_system_prompt
from .state import add_to_conversation_history, browser_contexts, get_conversation_history
from .slideshow import execute_iterative_workflow, execute_slideshow_workflow
from .browser import get_browser_page


logger = get_logger(__name__)
router = APIRouter()


VALID_ACTIONS = [
    "open_app",
    "close_all",
    "close_window",
    "minimize_window",
    "maximize_window",
    "create_file",
    "find_file",
    "read_files",
    "delete_file",
    "list_files",
    "compose_email",
    "navigate_browser",
    "control_browser",
]


def _is_compilation_request(user_message: str, recent_history: List[Dict[str, str]]) -> bool:
    user_lower = user_message.lower().strip()

    has_recent_find = any(
        msg.get("role") == "assistant"
        and (
            "found" in msg.get("content", "").lower()
            or "searching" in msg.get("content", "").lower()
            or "find_file" in str(msg)
        )
        for msg in recent_history
    )

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

    has_explicit_keyword = any(keyword in user_lower for keyword in compilation_keywords)

    has_report_pattern = (
        ("report" in user_lower and ("of" in user_lower or "from" in user_lower or "on" in user_lower))
        or ("make" in user_lower and "report" in user_lower)
        or ("compile" in user_lower and ("it" in user_lower or "them" in user_lower or "all" in user_lower))
        or ("summarize" in user_lower and ("it" in user_lower or "them" in user_lower))
    )

    has_report_keyword = any(kw in user_lower for kw in ["report", "compile", "summarize", "summary"])
    has_document_trigger = any(trig in user_lower for trig in ["documents", "files", "it", "them", "those", "all"])

    return has_explicit_keyword or has_report_pattern or (has_report_keyword and (has_document_trigger or has_recent_find))


def _is_slideshow_request(user_message: str) -> bool:
    user_lower = user_message.lower().strip()
    slideshow_keywords = [
        "create.*slideshow",
        "make.*presentation",
        "generate.*slideshow",
        "create.*presentation",
        "build.*presentation",
    ]
    return any(re.search(keyword.replace("*", ".*"), user_lower) for keyword in slideshow_keywords)


def _extract_json(raw_response: str) -> str:
    stripped = raw_response.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```[a-zA-Z]*\n?", "", stripped)
        stripped = re.sub(r"```\s*$", "", stripped)
    return stripped.strip()


def _validate_response(response_dict: Dict[str, Any]):
    if not isinstance(response_dict, dict):
        return False, "Response is not a dictionary"

    if "response" not in response_dict or not isinstance(response_dict["response"], str):
        return False, "Missing or invalid 'response' field"

    if "action" not in response_dict:
        return False, "Missing 'action' field"

    if "data" not in response_dict or not isinstance(response_dict["data"], dict):
        return False, "Missing or invalid 'data' field"

    action = response_dict.get("action")
    if action is not None:
        if not isinstance(action, str) or action not in VALID_ACTIONS:
            return False, f"Invalid action: {action}. Must be one of {VALID_ACTIONS} or null"

    return True, "Valid"


async def process_chat_message(user_message: str, session_id: str, skip_streaming: bool = False) -> Dict[str, Any]:
    if not user_message:
        return {"response": "Please enter a command.", "action": None, "data": None}

    if is_demo_project_command(user_message):
        event = record_demo_command(
            DemoCommandRequest(command=user_message, source="phone" if session_id == "default" else "dashboard")
        )
        add_to_conversation_history(session_id, user_message, "Script uploaded." if event["kind"] == "script" else "Feedback queued.")
        return {
            "response": "Script uploaded." if event["kind"] == "script" else "Feedback queued.",
            "action": None,
            "data": {"demo_event": event},
        }

    recent_history = get_conversation_history(session_id, max_pairs=2)

    if not skip_streaming:
        if _is_compilation_request(user_message, recent_history):
            async def generate():
                try:
                    logger.info("Starting iterative workflow for: %s", user_message)
                    async for update in execute_iterative_workflow(user_message, session_id):
                        logger.info("Yielding update: %s", update)
                        yield f"data: {json.dumps(update)}\n\n"
                        yield ""
                except Exception as exc:
                    logger.error("Error in streaming workflow: %s", exc, exc_info=True)
                    yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"

            return StreamingResponse(
                generate(),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
            )

        if _is_slideshow_request(user_message):
            async def generate():
                try:
                    logger.info("Starting slideshow workflow for: %s", user_message)
                    async for update in execute_slideshow_workflow(user_message, session_id):
                        logger.info("Yielding update: %s", update)
                        yield f"data: {json.dumps(update)}\n\n"
                        yield ""
                except Exception as exc:
                    logger.error("Error in streaming slideshow workflow: %s", exc, exc_info=True)
                    yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"

            return StreamingResponse(
                generate(),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
            )

    available_files = get_available_files()
    files_context = "\n".join([f"- {f['path']}" for f in available_files[:20]])
    system_prompt = build_system_prompt(files_context)

    hyperspell_sources: List[str] = []
    hyperspell_context_memories: List[Any] = []

    try:
        logger.info("=" * 80)
        logger.info("SYSTEM PROMPT:")
        logger.info("=" * 80)
        logger.info(system_prompt)
        logger.info("=" * 80)
        logger.info("USER MESSAGE: %s", user_message)
        logger.info("=" * 80)

        max_retries = 3
        llm_response = None
        raw_response = None

        history_messages = get_conversation_history(session_id, max_pairs=4)

        hyperspell_sources = detect_hyperspell_sources(user_message, history_messages)
        if hyperspell_sources:
            hyperspell_context_memories = await fetch_hyperspell_context(
                session_id,
                user_message,
                hyperspell_sources,
                limit=6,
            )
            if hyperspell_context_memories:
                logger.info(
                    "Retrieved %s Hyperspell memories for session %s from sources: %s",
                    len(hyperspell_context_memories),
                    session_id,
                    ", ".join(hyperspell_sources),
                )

        formatted_hyperspell_context = format_hyperspell_context(hyperspell_context_memories)

        system_blocks = [system_prompt]
        if formatted_hyperspell_context:
            system_blocks.append(
                "Context retrieved from Hyperspell "
                f"(sources: {', '.join(hyperspell_sources)}):\n"
                f"{formatted_hyperspell_context}"
            )
        system_blocks.append(
            "Respond with ONLY the raw JSON object described above — no markdown code "
            "fences, no commentary before or after it."
        )
        system_prompt_combined = "\n\n".join(system_blocks)

        messages = list(history_messages)
        messages.append({"role": "user", "content": user_message})

        for attempt in range(1, max_retries + 1):
            try:
                logger.info("API Call Attempt %s/%s", attempt, max_retries)

                completion = anthropic_client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=1024,
                    temperature=0.7,
                    system=system_prompt_combined,
                    messages=messages,
                )

                raw_response = "".join(
                    block.text for block in completion.content if block.type == "text"
                ).strip()

                logger.info("=" * 80)
                logger.info("LLM REPLY (Attempt %s):", attempt)
                logger.info("=" * 80)
                logger.info(raw_response)
                logger.info("=" * 80)

                try:
                    llm_response = json.loads(_extract_json(raw_response))
                except json.JSONDecodeError as exc:
                    error_msg = f"Invalid JSON on attempt {attempt}: {str(exc)}"
                    logger.warning(error_msg)
                    if attempt < max_retries:
                        logger.info("Retrying... (%s/%s)", attempt + 1, max_retries)
                        continue
                    raise Exception(f"Failed to parse JSON after {max_retries} attempts: {str(exc)}")

                is_valid, validation_msg = _validate_response(llm_response)
                if not is_valid:
                    error_msg = f"Invalid response on attempt {attempt}: {validation_msg}"
                    logger.warning(error_msg)
                    logger.warning("Response was: %s", json.dumps(llm_response, indent=2))
                    if attempt < max_retries:
                        logger.info("Retrying... (%s/%s)", attempt + 1, max_retries)
                        continue

                    logger.error("Failed validation after %s attempts. Using fallback.", max_retries)
                    llm_response = {
                        "response": f"I encountered an error processing your request after {max_retries} attempts. Please try rephrasing your request.",
                        "action": None,
                        "data": {},
                    }
                    break

                logger.info("Valid response received on attempt %s", attempt)
                break

            except Exception as exc:
                error_msg = f"Error on attempt {attempt}: {str(exc)}"
                logger.error(error_msg)
                if attempt < max_retries:
                    logger.info("Retrying... (%s/%s)", attempt + 1, max_retries)
                    continue
                raise Exception(f"Failed after {max_retries} attempts: {str(exc)}")

        if llm_response is None:
            llm_response = {"response": "I encountered an error processing your request. Please try again.", "action": None, "data": {}}

        action = llm_response.get("action")
        action_data = llm_response.get("data", {})

        if action == "create_file":
            try:
                file_path = action_data.get("path", "")
                file_content = action_data.get("content", "")

                if not file_path:
                    llm_response["response"] = "Error: No file path specified for file creation."
                    llm_response["action"] = None
                else:
                    safe_path = create_file(file_path, file_content)
                    llm_response["response"] = f"Successfully created file '{safe_path}'."
            except FileExistsError:
                llm_response["response"] = f"Error: File '{action_data.get('path', '')}' already exists."
                llm_response["action"] = None
            except Exception as exc:
                llm_response["response"] = f"Error creating file: {str(exc)}"
                llm_response["action"] = None

        elif action == "find_file":
            try:
                pattern = action_data.get("pattern", "")
                search_in_content = action_data.get("search_content", True)

                if not pattern:
                    llm_response["response"] = "Error: No search pattern specified."
                    llm_response["action"] = None
                else:
                    found_files = find_files(pattern, search_in_content)

                    if found_files:
                        results_text = []
                        for match in found_files[:15]:
                            if match.match_type == "filename":
                                results_text.append(f"- {match.path} (filename match)")
                            else:
                                sample_lines = match.sample_lines or []
                                line_info = (
                                    f" (found in content at lines {', '.join(map(str, sample_lines))}"
                                    + (
                                        f", and {match.line_count - len(sample_lines)} more"
                                        if match.line_count > len(sample_lines)
                                        else ""
                                    )
                                    + ")"
                                )
                                results_text.append(f"- {match.path}{line_info}")

                        files_list = "\n".join(results_text)
                        total_count = len(found_files)
                        llm_response["response"] = f"Found {total_count} file(s) matching '{pattern}':\n{files_list}"
                        llm_response["data"] = {
                            "files": [match.path for match in found_files[:15]],
                            "details": [match.__dict__ for match in found_files[:15]],
                        }
                    else:
                        llm_response["response"] = f"No files found matching '{pattern}' in filename or content."
                        llm_response["data"] = {"files": [], "details": []}
            except Exception as exc:
                llm_response["response"] = f"Error finding files: {str(exc)}"
                llm_response["action"] = None

        elif action == "read_files":
            try:
                file_paths = action_data.get("paths", [])
                if not file_paths or not isinstance(file_paths, list):
                    llm_response["response"] = "Error: No file paths specified or paths must be an array."
                    llm_response["action"] = None
                else:
                    file_contents = read_files(file_paths)
                    errors = []

                    missing_paths = [p for p in file_paths if p not in {fc.path for fc in file_contents}]
                    errors.extend([f"File not found: {path}" for path in missing_paths])

                    if file_contents:
                        response_parts = [f"Successfully read {len(file_contents)} file(s):"]
                        for fc in file_contents:
                            response_parts.append(f"\n--- {fc.path} ({fc.lines} lines, {fc.size} chars) ---")
                            response_parts.append(fc.content)

                        if errors:
                            response_parts.append(f"\n\nErrors: {', '.join(errors)}")

                        llm_response["response"] = "\n".join(response_parts)
                        llm_response["data"] = {
                            "files": [fc.__dict__ for fc in file_contents],
                            "errors": errors,
                        }
                    else:
                        llm_response["response"] = f"No files could be read. Errors: {', '.join(errors) if errors else 'All files were invalid or not found.'}"
                        llm_response["data"] = {"files": [], "errors": errors}
            except Exception as exc:
                llm_response["response"] = f"Error reading files: {str(exc)}"
                llm_response["action"] = None

        elif action == "delete_file":
            try:
                file_path = action_data.get("path", "")
                if not file_path:
                    llm_response["response"] = "Error: No file path specified for deletion."
                    llm_response["action"] = None
                else:
                    delete_item(file_path)
                    llm_response["response"] = f"Successfully deleted '{file_path}'."
            except Exception as exc:
                llm_response["response"] = f"Error deleting file: {str(exc)}"
                llm_response["action"] = None

        elif action == "list_files":
            try:
                list_path = action_data.get("path", "")
                items = list_files(list_path)

                if items:
                    items_list = "\n".join([f"- {item['name']} ({item['type']})" for item in items[:20]])
                    llm_response["response"] = f"Files in '{list_path or 'root'}':\n{items_list}"
                    llm_response["data"] = {"items": items[:20]}
                else:
                    llm_response["response"] = f"Directory '{list_path or 'root'}' is empty."
                    llm_response["data"] = {"items": []}
            except Exception as exc:
                llm_response["response"] = f"Error listing files: {str(exc)}"
                llm_response["action"] = None

        elif action == "compose_email":
            instructions = action_data.get("instructions", "")
            if not instructions:
                llm_response["response"] = "Error: No email instructions provided."
                llm_response["action"] = None
            else:
                result = await send_email(instructions)
                email_entry = result.get("email")
                recipient = email_entry.get("to", "recipient") if email_entry else "recipient"
                subject = email_entry.get("subject", "email") if email_entry else "email"
                llm_response["response"] = f"Email sent successfully to {recipient}!\nSubject: {subject}\nThe email has been added to your inbox."
                llm_response["data"] = {"email": email_entry}

        elif action == "navigate_browser":
            try:
                urls = action_data.get("urls", [])
                url = action_data.get("url", "")

                if urls and isinstance(urls, list) and len(urls) > 0:
                    if len(urls) == 1:
                        url = urls[0]
                        urls = []

                if urls and len(urls) > 1:
                    url_list = [u.strip() for u in urls if u.strip()]
                    if not url_list:
                        llm_response["response"] = "Error: No valid URLs provided."
                        llm_response["action"] = None
                    else:
                        search_terms = []
                        user_lower = user_message.lower()
                        search_patterns = [
                            "find out about",
                            "search for",
                            "look up",
                            "find information about",
                            "get information on",
                            "learn about",
                        ]
                        has_search_intent = any(pattern in user_lower for pattern in search_patterns)

                        if has_search_intent:
                            patterns = [
                                r"(?:find out about|search for|look up|find information about|learn about)\s+(.+?)(?:\s+and\s+|\s*,\s*|\s*$|$)",
                                r"in separate browsers?\s+(?:find out about|search for|look up)?\s*(.+?)(?:\s+and\s+|\s*,\s*|\s*$)",
                            ]

                            terms_str = ""
                            for pattern in patterns:
                                search_matches = re.findall(pattern, user_lower)
                                if search_matches:
                                    terms_str = search_matches[0]
                                    break

                            if terms_str:
                                terms = re.split(r",|\sand\s+", terms_str)
                                search_terms = [t.strip() for t in terms if t.strip() and len(t.strip()) > 1][: len(url_list)]

                                if len(search_terms) < len(url_list):
                                    about_match = re.search(r"about\s+(.+)", user_lower)
                                    if about_match:
                                        terms_str = about_match.group(1)
                                        terms = re.split(r",|\sand\s+", terms_str)
                                        search_terms = [t.strip() for t in terms if t.strip() and len(t.strip()) > 1][: len(url_list)]

                        sites_list = ", ".join(url_list[:3])
                        if len(url_list) > 3:
                            sites_list += f" and {len(url_list) - 3} more"
                        response_msg = f"Opening {len(url_list)} browser windows with autonomous agents: {sites_list}!"
                        if has_search_intent and search_terms:
                            response_msg += f" Each agent will search for: {', '.join(search_terms)}"
                        llm_response["response"] = response_msg
                        llm_response["action"] = "open_app"
                        llm_response["data"] = {
                            "app": "browser",
                            "title": f"Browser - {url_list[0]}",
                            "navigate_to": url_list,
                            "multiple_urls": url_list,
                            "search_terms": search_terms,
                            "auto_search": has_search_intent,
                            "agent_goals": search_terms if has_search_intent else [],
                        }
                elif url:
                    user_lower = user_message.lower()

                    task_patterns = [
                        r"extract.*(?:info|information|data|text|content)",
                        r"create.*(?:doc|document|file|word|txt)",
                        r"save.*(?:info|information|data|text|content)",
                        r"get.*(?:info|information|data).*(?:and|then).*(?:create|save|make|write)",
                        r"summarize.*(?:and|then).*(?:save|create|write)",
                        r"read.*(?:and|then).*(?:extract|save|create)",
                    ]

                    has_task_intent = any(re.search(pattern, user_lower) for pattern in task_patterns)
                    agent_goal = None

                    if has_task_intent:
                        extract_match = re.search(r"(extract|get|read|save|summarize).*?(?:\sand\s|,\s|$|and\s+create|and\s+save|and\s+make|then)", user_lower)
                        create_match = re.search(r"(create|make|write|save).*?(?:doc|document|file|word|txt|\.docx|\.txt)", user_lower)

                        if extract_match or create_match:
                            task_parts = []
                            if extract_match:
                                task_parts.append(extract_match.group(0).strip())
                            if create_match:
                                task_parts.append(create_match.group(0).strip())

                            agent_goal = " ".join(task_parts) if task_parts else user_message
                            agent_goal = re.sub(r"\s+", " ", agent_goal).strip()
                        else:
                            agent_goal = user_message

                    try:
                        from urllib.parse import urlparse

                        parsed = urlparse(url if url.startswith(("http://", "https://")) else f"https://{url}")
                        domain = parsed.netloc or url.split("/")[0]
                        title = f"Browser - {domain}"
                    except Exception:
                        title = f"Browser - {url[:30]}"

                    if agent_goal:
                        llm_response["response"] = (
                            f"Opening browser to {url} and starting an autonomous agent to complete the task. "
                            "The agent will work in the background and provide progress updates."
                        )
                    else:
                        llm_response["response"] = f"Opening browser and navigating to {url}..."

                    llm_response["action"] = "open_app"
                    llm_response["data"] = {
                        "app": "browser",
                        "title": title,
                        "navigate_to": url,
                        "agent_goal": agent_goal,
                    }
                else:
                    llm_response["response"] = "Error: No URL provided for navigation."
                    llm_response["action"] = None
            except Exception as exc:
                llm_response["response"] = f"Error navigating browser: {str(exc)}"
                llm_response["action"] = None

        elif action == "control_browser":
            try:
                command = action_data.get("command", "")
                session_id_param = action_data.get("session_id", None)

                if not command:
                    llm_response["response"] = "Error: No command provided for browser control."
                    llm_response["action"] = None
                else:
                    if not session_id_param or session_id_param == "default":
                        active_sessions = [
                            k
                            for k in browser_contexts.keys()
                            if not k.endswith("_base_url") and not k.endswith("_current_url")
                        ]
                        if active_sessions:
                            session_id_param = active_sessions[-1]
                        else:
                            session_id_param = "default"

                    page = await get_browser_page(session_id_param)
                    if not page:
                        llm_response["response"] = "Error: No browser window is currently open."
                        llm_response["action"] = None
                    else:
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
4. wait - Wait for something (just return wait action)

Return ONLY a JSON object with this exact format:
{
  "action": "click" | "type" | "scroll" | "wait",
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

                            if action_type == "click":
                                x = vision_result.get("x", 0)
                                y = vision_result.get("y", 0)
                                await page.mouse.click(x, y)
                                await page.wait_for_timeout(500)
                                description = vision_result.get("description", "Clicked on the page")
                                llm_response["response"] = f"{description}. Action completed!"
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
                                description = vision_result.get("description", "Typed text")
                                llm_response["response"] = f"{description}. Action completed!"
                            elif action_type == "scroll":
                                scroll_x = vision_result.get("x", 0)
                                scroll_y = vision_result.get("y", 0)
                                await page.mouse.wheel(scroll_x, scroll_y)
                                await page.wait_for_timeout(500)
                                description = vision_result.get("description", "Scrolled the page")
                                llm_response["response"] = f"{description}. Action completed!"
                            else:
                                llm_response["response"] = "Waiting or no action needed."

                            current_url = page.url
                            title = await page.title()

                            llm_response["data"] = {
                                "url": current_url,
                                "title": title,
                                "proxy_url": f"/api/browser/proxy/{session_id_param}/",
                            }

                        except Exception as exc:
                            logger.error("Error in vision analysis: %s", exc)
                            llm_response["response"] = f"Error analyzing page: {str(exc)}. Please try being more specific."
                            llm_response["action"] = None
            except Exception as exc:
                llm_response["response"] = f"Error controlling browser: {str(exc)}"
                llm_response["action"] = None

        if llm_response:
            metadata: Dict[str, Any] = {}
            action_field = llm_response.get("action")
            if action_field is not None:
                metadata["action"] = action_field

            schedule_hyperspell_record(
                session_id,
                user_message,
                llm_response.get("response", ""),
                sources=hyperspell_sources or None,
                context_used=hyperspell_context_memories or None,
                metadata=metadata or None,
            )

        if llm_response and raw_response:
            add_to_conversation_history(session_id, user_message, raw_response)
            logger.info("Stored conversation exchange for session: %s", session_id)

        return llm_response

    except json.JSONDecodeError as exc:
        return {"response": f"I encountered an error parsing the response. Please try again. Error: {str(exc)}", "action": None, "data": None}
    except Exception as exc:
        return {"response": f"I encountered an error: {str(exc)}. Please make sure your Anthropic API key is valid.", "action": None, "data": None}


@router.post("/api/chat")
async def chat_endpoint(request: Request):
    data = await request.json()
    user_message = data.get("message", "").strip()
    session_id = data.get("session_id", "default")

    result = await process_chat_message(user_message, session_id)
    if isinstance(result, StreamingResponse):
        return result
    return JSONResponse(content=result)


@router.post("/api/chat/stream")
async def chat_stream_endpoint(request: Request):
    data = await request.json()
    user_message = data.get("message", "").strip()
    session_id = data.get("session_id", "default")

    if not user_message:
        return JSONResponse(content={"error": "No message provided"})

    async def generate():
        async for update in execute_iterative_workflow(user_message, session_id):
            yield f"data: {json.dumps(update)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
