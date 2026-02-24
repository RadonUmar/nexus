from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .clients import openai_client
from .files import DATA_DIR, find_files, read_files
from .logging import get_logger
from slide_templates import HTML_TEMPLATE, SLIDE_TEMPLATES, create_slide_content


logger = get_logger(__name__)
router = APIRouter()


class SlideshowRequest(BaseModel):
    prompt: str
    template_style: Optional[str] = None


async def execute_iterative_workflow(user_message: str, session_id: str):
    compilation_keywords = [
        "compile",
        "create a report",
        "generate a report",
        "analyze and create",
        "summarize",
        "create a summary",
    ]
    user_lower = user_message.lower()
    is_compilation_request = any(keyword in user_lower for keyword in compilation_keywords)

    if not is_compilation_request:
        yield {"type": "error", "message": "Not a compilation request"}
        return

    try:
        yield {"type": "progress", "message": "🔍 Step 1: Finding relevant documents...", "step": 1}
        await asyncio.sleep(0.1)

        search_prompt = (
            f"Based on this user request: \"{user_message}\"\n"
            "Extract the key search terms for finding relevant documents. "
            "Return only a comma-separated list of search terms.\n"
            "Examples: \"Q4 financial\" -> \"Q4,financial\", "
            "\"client status reports\" -> \"client,status\"\n"
            "Search terms:"
        )

        try:
            yield {"type": "progress", "message": "🔍 Analyzing request to determine search terms...", "step": 1}
            completion = openai_client.chat.completions.create(
                model="gpt-4.1-2025-04-14",
                messages=[{"role": "user", "content": search_prompt}],
                temperature=0.3,
                max_tokens=50,
            )
            search_terms = completion.choices[0].message.content.strip()
            pattern = search_terms.split(",")[0].strip() if "," in search_terms else search_terms
        except Exception as exc:
            logger.error("Error extracting search pattern: %s", exc)
            pattern = " ".join([word for word in user_lower.split() if len(word) > 3][:3])

        yield {"type": "progress", "message": f"🔍 Searching for documents matching: '{pattern}'...", "step": 1}
        await asyncio.sleep(0.1)

        found_matches = await asyncio.to_thread(find_files, pattern, True)
        found_files = [match.path for match in found_matches]

        if not found_files:
            yield {"type": "error", "message": f"No documents found matching '{pattern}'"}
            return

        yield {
            "type": "progress",
            "message": (
                f"✅ Found {len(found_files)} relevant document(s): "
                f"{', '.join([f.split('/')[-1] for f in found_files[:5]])}"
                f"{'...' if len(found_files) > 5 else ''}"
            ),
            "step": 1,
            "files": found_files[:10],
        }
        await asyncio.sleep(0.1)

        yield {"type": "progress", "message": f"📖 Step 2: Reading {min(len(found_files), 10)} document(s)...", "step": 2}
        await asyncio.sleep(0.1)

        file_contents = await asyncio.to_thread(read_files, found_files[:10])

        if not file_contents:
            yield {"type": "error", "message": "Could not read any documents"}
            return

        yield {
            "type": "progress",
            "message": (
                f"✅ Successfully read {len(file_contents)} document(s) "
                f"({sum(len(fc.content) for fc in file_contents)} total characters)"
            ),
            "step": 2,
        }
        await asyncio.sleep(0.1)

        yield {"type": "progress", "message": "🤖 Step 3: Analyzing documents and compiling comprehensive report...", "step": 3}
        await asyncio.sleep(0.1)

        documents_text = "\n\n".join(
            [f"=== {fc.path} ===\n{fc.content}" for fc in file_contents]
        )

        compile_prompt = (
            f"Based on the user request: \"{user_message}\"\n\n"
            "Here are the relevant documents:\n\n"
            f"{documents_text}\n\n"
            "Create a comprehensive, well-structured report that synthesizes all the information from these documents. "
            "The report should be professional, detailed, and include all key findings, metrics, and insights.\n\n"
            "Return the compiled report content:"
        )

        yield {"type": "progress", "message": "🤖 Generating report with AI (this may take a moment)...", "step": 3}

        try:
            completion = await asyncio.to_thread(
                openai_client.chat.completions.create,
                model="gpt-4.1-2025-04-14",
                messages=[{"role": "user", "content": compile_prompt}],
                temperature=0.7,
                max_tokens=4000,
            )
            compiled_content = completion.choices[0].message.content

            output_name = "Compiled_Report.md"
            if "Q4" in user_message or "quarter" in user_lower:
                output_name = "Q4_Financial_Report_Compiled.md"
            elif "client" in user_lower:
                output_name = "Client_Status_Summary.md"

            output_path = f"Desktop/{output_name}"
            target_file = DATA_DIR / output_path
            target_file.parent.mkdir(parents=True, exist_ok=True)
            target_file.write_text(compiled_content, encoding="utf-8")

            yield {
                "type": "complete",
                "message": (
                    "✅ Successfully compiled report!\n\n"
                    f"📄 File: {output_path}\n"
                    f"📊 Size: {len(compiled_content)} characters\n\n"
                    f"Preview:\n{compiled_content[:300]}..."
                ),
                "step": 3,
                "output_file": output_path,
                "preview": compiled_content[:500] + "..." if len(compiled_content) > 500 else compiled_content,
            }
        except Exception as exc:
            logger.error("Error compiling report: %s", exc)
            yield {"type": "error", "message": f"Error compiling report: {str(exc)}"}
    except Exception as exc:
        logger.error("Error in iterative workflow: %s", exc)
        yield {"type": "error", "message": f"Workflow error: {str(exc)}"}


async def execute_slideshow_workflow(user_message: str, session_id: str):
    try:
        yield {"type": "progress", "message": "🔍 Step 1: Finding relevant documents and information...", "step": 1}
        await asyncio.sleep(0.1)

        search_decision_prompt = (
            f"Based on this user request: \"{user_message}\"\n"
            "Determine if we should search for relevant documents to gather information.\n"
            "If the request mentions specific topics, data, reports, or suggests using existing documents, return \"YES\" followed by search terms.\n"
            "If it's a general creative request, return \"NO\".\n"
            "Examples:\n"
            "- \"Create a presentation about Q4 financial results\" -> \"YES:Q4,financial,results\"\n"
            "- \"Make a slideshow about our company\" -> \"YES:company,about\"\n"
            "- \"Create a fun presentation about cats\" -> \"NO\"\n\n"
            "Response:"
        )

        try:
            yield {"type": "progress", "message": "🔍 Analyzing request to determine information sources...", "step": 1}
            completion = openai_client.chat.completions.create(
                model="gpt-4.1-2025-04-14",
                messages=[{"role": "user", "content": search_decision_prompt}],
                temperature=0.3,
                max_tokens=50,
            )
            search_decision = completion.choices[0].message.content.strip()
            should_search = search_decision.upper().startswith("YES")
            if should_search:
                pattern = (
                    search_decision.split(":")[-1].strip()
                    if ":" in search_decision
                    else " ".join([word for word in user_message.lower().split() if len(word) > 3][:3])
                )
            else:
                pattern = None
        except Exception as exc:
            logger.error("Error in search decision: %s", exc)
            pattern = " ".join([word for word in user_message.lower().split() if len(word) > 3][:3]) if len(user_message.split()) > 3 else None
            should_search = pattern is not None

        documents_text = ""
        if should_search and pattern:
            yield {"type": "progress", "message": f"🔍 Searching for documents matching: '{pattern}'...", "step": 1}
            await asyncio.sleep(0.1)

            found_matches = await asyncio.to_thread(find_files, pattern, True)
            found_files = [match.path for match in found_matches]

            if found_files:
                yield {
                    "type": "progress",
                    "message": f"✅ Found {len(found_files)} relevant document(s)",
                    "step": 1,
                    "files": found_files[:10],
                }
                await asyncio.sleep(0.1)

                yield {
                    "type": "progress",
                    "message": f"📖 Step 2: Reading {min(len(found_files), 10)} document(s)...",
                    "step": 2,
                }
                await asyncio.sleep(0.1)

                file_contents = await asyncio.to_thread(read_files, found_files[:10])

                if file_contents:
                    documents_text = "\n\n".join(
                        [f"=== {fc.path} ===\n{fc.content}" for fc in file_contents]
                    )
                    yield {
                        "type": "progress",
                        "message": f"✅ Successfully gathered information from {len(file_contents)} document(s)",
                        "step": 2,
                    }
                    await asyncio.sleep(0.1)
        else:
            yield {
                "type": "progress",
                "message": "ℹ️ Creating presentation from your description (no document search needed)",
                "step": 1,
            }
            await asyncio.sleep(0.1)

        yield {"type": "progress", "message": "🎨 Step 3: Generating professional presentation slides...", "step": 3}
        await asyncio.sleep(0.1)

        enhanced_prompt = user_message
        if documents_text:
            enhanced_prompt = (
                f"{user_message}\n\n"
                "Use the following information gathered from documents to create an accurate and comprehensive presentation:\n\n"
                f"{documents_text}\n\n"
                "Create a professional presentation that incorporates this information."
            )

        yield {"type": "progress", "message": "🤖 Using AI to design slides and generate content...", "step": 3}
        await asyncio.sleep(0.1)

        slideshow_response = await generate_slideshow_internal(enhanced_prompt)

        if not slideshow_response.get("success"):
            yield {"type": "error", "message": f"Error generating slideshow: {slideshow_response.get('error', 'Unknown error')}"}
            return

        yield {"type": "progress", "message": "💾 Step 4: Saving presentation file...", "step": 4}
        await asyncio.sleep(0.1)

        title = slideshow_response.get("title", "Presentation")
        safe_filename = "".join(c if c.isalnum() or c in (" ", "-", "_") else "" for c in title)
        safe_filename = safe_filename.replace(" ", "_")[:50]
        if not safe_filename:
            safe_filename = "Slideshow"

        output_path = f"Desktop/{safe_filename}.html"
        target_file = DATA_DIR / output_path
        target_file.parent.mkdir(parents=True, exist_ok=True)
        target_file.write_text(slideshow_response.get("html"), encoding="utf-8")

        yield {
            "type": "complete",
            "message": (
                "✅ Successfully created presentation!\n\n"
                f"📄 File: {output_path}\n"
                f"📊 Slides: {slideshow_response.get('slide_count', 0)}\n"
                f"📝 Title: {title}\n\n"
                "Double-click the file to open it in the browser."
            ),
            "step": 4,
            "output_file": output_path,
            "slide_count": slideshow_response.get("slide_count", 0),
            "title": title,
        }

    except Exception as exc:
        logger.error("Error in slideshow workflow: %s", exc, exc_info=True)
        yield {"type": "error", "message": f"Workflow error: {str(exc)}"}


async def generate_slideshow_internal(prompt: str, template_style: Optional[str] = None):
    try:
        system_prompt = (
            "You are an expert slideshow designer and HTML/CSS developer. \n"
            "Given a user's request, create a professional slideshow presentation.\n\n"
            "Return a JSON object with this structure:\n"
            "{\n"
            "  \"title\": \"Presentation Title\",\n"
            "  \"template_style\": \"modern|minimal|dark|corporate|creative\",\n"
            "  \"slides\": [\n"
            "    {\n"
            "      \"type\": \"title|content|list|stats|image|chart\",\n"
            "      \"title\": \"Slide Title\",\n"
            "      \"content\": \"Main content text (can include HTML for formatting)\",\n"
            "      \"items\": [\"List item 1\", \"List item 2\"] (for list type),\n"
            "      \"stats\": [{\"value\": \"12.5M\", \"label\": \"Revenue\"}] (for stats type),\n"
            "      \"chart_data\": {\n"
            "        \"type\": \"bar|line|pie|doughnut\",\n"
            "        \"labels\": [\"Label1\", \"Label2\", \"Label3\"],\n"
            "        \"datasets\": [{\n"
            "          \"label\": \"Dataset Label\",\n"
            "          \"data\": [10, 20, 30],\n"
            "          \"backgroundColor\": [\"#667eea\", \"#764ba2\", \"#f093fb\"] (for pie/doughnut) or \"#667eea\" (for bar/line)\n"
            "        }]\n"
            "      } (for chart type - use when user requests charts or visualizations)\n"
            "    }\n"
            "  ]\n"
            "}\n\n"
            "Guidelines:\n"
            "- Create 5-10 slides for comprehensive presentations\n"
            "- Use appropriate slide types: title slide, content slides, list slides, stats slides, charts\n"
            "- When user requests \"charts\", \"visualizations\", \"graphs\", or \"pie charts\", use type \"chart\" with chart_data\n"
            "- For chart_data: use \"pie\" or \"doughnut\" for pie charts, use \"bar\" for bar charts, \"line\" for line charts\n"
            "- Chart colors should match the template style (use gradients for modern/creative, solid colors for corporate)\n"
            "- For financial/business presentations, use \"corporate\" style with bar or line charts\n"
            "- For creative/pitch presentations, use \"modern\" or \"creative\" style\n"
            "- For technical presentations, use \"minimal\" or \"dark\" style\n"
            "- Make content professional, engaging, and well-structured\n"
            "- Include relevant metrics and data when appropriate\n"
            "- Use clear, concise language"
        )

        try:
            completion = openai_client.chat.completions.create(
                model="gpt-4.1-2025-04-14",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Create a slideshow presentation for: {prompt}"},
                ],
                temperature=0.7,
                response_format={"type": "json_object"},
                max_tokens=3000,
            )

            slideshow_data = json.loads(completion.choices[0].message.content)
        except Exception as exc:
            logger.error("Error generating slideshow structure: %s", exc)
            return {"success": False, "error": f"Error generating slideshow structure: {str(exc)}"}

        title = slideshow_data.get("title", "Presentation")
        final_template_style = template_style or slideshow_data.get("template_style", "modern")
        slides_data = slideshow_data.get("slides", [])

        if not slides_data:
            return {"success": False, "error": "No slides generated"}

        slides_html = []
        for slide_data in slides_data:
            slide_content = create_slide_content(slide_data, final_template_style)
            slide_html = SLIDE_TEMPLATES.get(final_template_style, SLIDE_TEMPLATES["modern"]).format(
                slide_class="slide",
                content=slide_content,
            )
            slides_html.append(slide_html)

        full_html = HTML_TEMPLATE.format(
            title=title,
            slides="\n".join(slides_html),
            slide_count=len(slides_html),
        )

        navigation_js = """
        <script>
            let currentSlide = 0;
            const slides = document.querySelectorAll('.slide');
            const indicator = document.querySelector('.slide-indicator');
            const totalSlides = slides.length;

            function showSlide(index) {
                if (index < 0 || index >= totalSlides) return;
                slides.forEach((slide, i) => {
                    slide.style.display = i === index ? 'flex' : 'none';
                });
                currentSlide = index;
                if (indicator) {
                    indicator.textContent = `${currentSlide + 1} / ${totalSlides}`;
                }
            }

            function nextSlide() {
                showSlide(Math.min(currentSlide + 1, totalSlides - 1));
            }

            function previousSlide() {
                showSlide(Math.max(currentSlide - 1, 0));
            }

            document.addEventListener('keydown', (e) => {
                if (e.key === 'ArrowRight' || e.key === ' ') {
                    e.preventDefault();
                    nextSlide();
                } else if (e.key === 'ArrowLeft') {
                    e.preventDefault();
                    previousSlide();
                } else if (e.key === 'Escape') {
                    // Fullscreen toggle could go here
                }
            });

            let touchStartX = 0;
            let touchEndX = 0;

            document.addEventListener('touchstart', (e) => {
                touchStartX = e.changedTouches[0].screenX;
            });

            document.addEventListener('touchend', (e) => {
                touchEndX = e.changedTouches[0].screenX;
                handleSwipe();
            });

            function handleSwipe() {
                const swipeThreshold = 50;
                const diff = touchStartX - touchEndX;
                if (Math.abs(diff) > swipeThreshold) {
                    if (diff > 0) {
                        nextSlide();
                    } else {
                        previousSlide();
                    }
                }
            }

            const chartInstances = new Map();

            function initializeCharts() {
                if (typeof Chart === 'undefined') {
                    setTimeout(initializeCharts, 100);
                    return;
                }

                document.querySelectorAll('canvas[id^="chart_"]').forEach(canvas => {
                    const chartId = canvas.id;
                    if (!chartInstances.has(chartId)) {
                        try {
                            const scriptTag = document.querySelector(`script[data-chart-id="${chartId}"]`);
                            if (scriptTag) {
                                const config = JSON.parse(scriptTag.textContent);
                                const chart = new Chart(canvas, config);
                                chartInstances.set(chartId, chart);
                            }
                        } catch (e) {
                            console.error('Error initializing chart:', e);
                        }
                    }
                });
            }

            showSlide(0);

            setTimeout(initializeCharts, 500);

            let hideControlsTimer;
            function resetHideTimer() {
                clearTimeout(hideControlsTimer);
                const controls = document.querySelector('.slide-controls');
                if (controls) controls.style.opacity = '1';
                hideControlsTimer = setTimeout(() => {
                    if (controls) controls.style.opacity = '0.3';
                }, 3000);
            }

            document.addEventListener('mousemove', resetHideTimer);
            resetHideTimer();
        </script>
        """

        full_html = full_html.replace("</body>", navigation_js + "\n</body>")

        return {
            "success": True,
            "html": full_html,
            "slide_count": len(slides_html),
            "title": title,
        }

    except Exception as exc:
        logger.error("Error generating slideshow: %s", exc, exc_info=True)
        return {"success": False, "error": str(exc)}


@router.post("/api/slideshow/generate")
async def generate_slideshow(request_data: SlideshowRequest):
    result = await generate_slideshow_internal(
        request_data.prompt,
        request_data.template_style,
    )

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))

    return result
