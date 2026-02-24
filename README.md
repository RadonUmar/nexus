# Agentic OS

An AI-powered OS interface that lets you control files, apps, email, and the browser through natural language. Built as a hackathon showcase with a live UI, autonomous browser agents, voice interaction, and optional Hyperspell context.

## Demo
- YouTube walkthrough:
  ```
  https://www.youtube.com/watch?v=ZXX_ghUk0jg
  ```

## Highlights
- Natural-language OS control (files, apps, browser).
- Autonomous browser agents for multi-tab tasks.
- Voice pipeline: STT → LLM → TTS.
- Report/slideshow generation workflows.
- Optional Hyperspell context from external sources.

## Architecture (Refactored)
The project is now organized into a clear backend package:
- `agentic_os/app.py`: app factory and startup/shutdown wiring.
- `agentic_os/chat.py`: LLM routing + JSON action handling.
- `agentic_os/browser.py`: Playwright automation + autonomous agents.
- `agentic_os/email.py`: email compose + inbox cache + background monitor.
- `agentic_os/files.py`: safe filesystem helpers.
- `agentic_os/slideshow.py`: slideshow/report workflows.
- `agentic_os/voice.py`: voice API and WebSocket pipeline.
- `agentic_os/hyperspell_context.py`: Hyperspell context helpers.
- `agentic_os/settings.py`: config and paths.
- `agentic_os/state.py`: runtime state and caches.

Entry point remains `main.py`.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Create a `.env` file in the repo root:
   ```
   OPENAI_API_KEY=your_openai_api_key_here

   # Optional:
   HYPERSPELL_API_KEY=your_hyperspell_api_key_here
   HYPERSPELL_AS_USER=
   HYPERSPELL_USER_TOKEN=
   HYPERSPELL_BASE_URL=https://api.hyperspell.com
   HYPERSPELL_QUERY_PATH=/memories/query
   HYPERSPELL_RECORD_PATH=
   HYPERSPELL_TIMEOUT_SECONDS=10
   
   # Optional override for email endpoints
   RAILWAY_EMAIL_API=https://web-production-02ec.up.railway.app/compose-send
   RAILWAY_EMAIL_INBOX_API=https://web-production-02ec.up.railway.app/emails
   ```

3. Run the server:
   ```bash
   uvicorn main:app --reload
   ```

4. Open the UI:
   ```
   http://127.0.0.1:8000
   ```

## Usage Examples
- “Create a file called `notes.txt` with my meeting notes.”
- “Find files containing `budget`.”
- “Compile a report from Q4 documents.”
- “Open google.com and search for competitive analysis.”
- “Create a presentation about our product roadmap.”

## Notes
- Hyperspell is optional. If `HYPERSPELL_API_KEY` is not set, it runs in mock/disabled mode.
- Email features use the Railway endpoints listed above. You can replace them via `.env`.

## Development Tips
- Most logic is now inside `agentic_os/` to keep `main.py` thin and clear.
- If you want to add features, prefer adding a new module + route rather than expanding `main.py`.

## License
MIT
