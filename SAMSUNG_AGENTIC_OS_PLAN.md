# Samsung Agentic OS — Build Plan

Target device: **Samsung Galaxy S25 (Snapdragon 8 Elite)**
Reference design language: Isa Usmanov's "Alex" (OpenAI Voice Hack Night winner) — voice-first, orb-centric, minimal list of core functions, agent does the work instead of the user tapping through apps.

This plan describes a **native Android app (Kotlin + Jetpack Compose)** that reuses the existing Python backend's agent logic where practical, replaces the desktop-web UI with a native OS-shell, and adds the animated orb + card-based result surfaces described in your reference.

---

## 1. Product shape (what we're building)

A launcher-style Android app (not necessarily a true system launcher for v1 — see §7) with:

- **Home screen**: near-black background, vertical white-text list of core functions — Messages, Calendar, Navigate, Search, Tasks, Mail.
- **Orb**: persistent animated agent avatar (idle / listening / thinking / working / done states), floating bottom-center, draggable/overlay-capable.
- **Voice-first input**: tap-and-hold or wake-word to talk to the orb; agent transcribes, reasons, acts.
- **Card surfaces**: structured result views (contact card, email draft w/ confirm, product comparison list, flight/fare scanner, auto-populating research table) rendered as Compose cards, not raw chat text.
- **Confirmation gating**: irreversible actions (send email, place call, buy) always show a review card before executing; everything else runs autonomously in the background.
- **Screen-context awareness**: v1 = share-sheet / accessibility-service based "look at what's on screen" hook (see §6 for feasibility notes — this is the hardest and most permission-sensitive feature).

For your demo, the KPI to optimize for is the same as the reference: **minimize taps/time-to-result, maximize agent-completed work**, shown through a couple of scripted end-to-end flows (see §8).

---

## 2. Architecture overview

```
┌─────────────────────────────┐        ┌──────────────────────────────┐
│   Samsung S25 (Android)     │  HTTPS  │   Backend (reused/adapted)   │
│   Kotlin + Jetpack Compose  │◄──────► │   FastAPI (Python)          │
│   - Orb UI / animations     │  WS     │   - chat.py (LLM router)    │
│   - Voice capture (mic)     │         │   - action handlers         │
│   - Card renderers          │         │   - email/files/etc.        │
│   - Native TTS/STT (opt.)   │         └──────────────────────────────┘
│   - Notification/Email      │                 │
│     intents                 │                 ▼
└─────────────────────────────┘         OpenAI API, Mail provider API,
                                         (drop Playwright browser automation)
```

Key decision: **keep the "brain" server-side, rebuild only the "body" (UI + device I/O) natively.** The existing `agentic_os/chat.py` action-dispatch pattern (LLM → structured JSON action → executed handler) is exactly the right shape for this and should be reused almost unchanged — you're swapping the *renderer* (2,900-line `app.js` desktop UI) for native Compose, not the *reasoning* layer.

### What transfers directly
- `agentic_os/chat.py` — LLM prompt/action-routing logic (the JSON action schema pattern).
- `agentic_os/files.py` — sandboxed file ops, if you keep a "Tasks/Files" feature.
- `agentic_os/email.py` — compose flow logic (swap the Railway HTTP target for a real mail API — see §5).
- `agentic_os/voice.py`'s STT→LLM→TTS **orchestration shape** (the WebSocket message protocol: `audio` → `transcription` → `response_chunk` → `audio_response` → `complete`) — very reusable as your Android↔backend voice protocol.
- `agentic_os/prompts.py` (system prompt structure) — needs a rewrite for the "Alex"-style persona and expanded action set (contacts, calls, shopping, calendar, research tables) but the pattern holds.

### What gets dropped or replaced
- `agentic_os/browser.py` (Playwright) — no Android equivalent; replace "browse the web for me" with a lightweight server-side search/scrape tool (e.g., a search API + `httpx` fetch) that returns structured data instead of screenshots.
- `templates/index.html` + `static/app.js` — fully replaced by the native app.
- `slideshow.py` — likely irrelevant to a phone demo, drop unless you want it.
- Railway email endpoints — fine to keep for the demo, but flag them as a stand-in, not production.

---

## 3. Android app structure (Kotlin + Compose)

```
app/
  ui/
    home/            HomeScreen.kt         — vertical function list + orb host
    orb/
      Orb.kt                                — Compose Canvas/AGSL shader orb, state machine
      OrbState.kt                           — Idle | Listening | Thinking | Working | Done
    cards/
      ContactCard.kt
      EmailDraftCard.kt                     — "Ready to send?" confirm card
      ProductComparisonCard.kt
      FareScannerCard.kt
      ResearchTableCard.kt                  — Notion-like auto-populating table
    theme/           Color.kt, Type.kt      — near-black, high-contrast, glow accents
  voice/
    VoiceCaptureManager.kt                  — mic capture, VAD (voice activity detection)
    VoiceSocketClient.kt                    — WebSocket client mirroring voice.py protocol
    NativeTts.kt (optional fallback)        — Android TextToSpeech for offline/low-latency bits
  agent/
    AgentClient.kt                          — REST/WS client to backend, action dispatch
    ActionExecutor.kt                       — maps backend "action" JSON → native device calls
                                               (open Mail intent, dial Intent.ACTION_CALL, etc.)
  data/
    ConversationStore.kt                    — local history, Room or in-memory
  MainActivity.kt                           — single-Activity, edge-to-edge, Compose host
```

### The orb, specifically
This is the single most important visual element and worth getting right:
- Implement with **Compose `Canvas` + custom shader (AGSL/RuntimeShader)** for the plasma/particle glow effect, or a pre-rendered **Lottie** animation per state if you want to move faster than hand-rolled shaders. Given your timeline, I'd default to **Lottie** (After Effects → Bodymovin export, or find/commission a suitable glowing-orb animation) for v1, and only invest in a custom AGSL shader if Lottie doesn't hit the "plasma/neural" look you want.
- State transitions (idle → listening → thinking → working → done, with a green tint on completion) driven by a simple `enum` + `AnimatedContent`/crossfade between Lottie compositions, so animation logic never touches business logic.
- Snapdragon 8 Elite has plenty of headroom for this — a shader-based orb at 120fps is not a performance concern on this hardware; the risk is design/animation time, not device capability.

### Visual language
- Background: `#000000`–`#0A0A0A`, single accent blue (`#3B82F6`-ish, matched to the orb's glow) for active states, green accent (`#22C55E`-ish) for completion.
- Typography: system font (Roboto/Samsung One UI Sans) at high contrast, generous vertical spacing, no icons on the home list — text only, per your reference.
- Cards: dark elevated surfaces (`#141414` on `#000000`), subtle blue-glow border, rounded corners (~16dp), matches the "sci-fi but restrained" brief.

---

## 4. Voice pipeline

Two viable options, and they're not mutually exclusive:

**Option A — Reuse server-side STT/TTS (fastest to build, matches existing backend)**
Android captures mic audio → sends over WebSocket to `/ws/voice` (already exists) → backend does Whisper STT + GPT + TTS → streams `audio_response` back → Android plays it. This is a near-direct port of the existing protocol; on-device work is just "record, send, play."

**Option B — Native STT with server-side reasoning (lower latency, more "on-device" feel)**
Android uses Android's built-in `SpeechRecognizer` (or on-device Whisper via a mobile-optimized model, feasible on Snapdragon 8 Elite's NPU) for transcription, sends *text* to backend for reasoning, backend returns text/action, Android uses native `TextToSpeech` for the reply. Feels snappier, less network-dependent for the STT leg, and is a better long-term architecture for something meant to feel like "part of the OS."

**Recommendation**: Start with Option A to get an end-to-end demo working fastest (it's a near-direct reuse of `voice.py`), then swap in native STT/TTS (Option B) once the flow works, for a snappier final demo. I'd plan for B for the actual presentation if time allows — round-trip audio-to-audio over network adds noticeable latency that undercuts the "seamless" feel you're going for.

---

## 5. Feature-by-feature mapping to your reference description

| Reference feature | Feasibility on S25 for a demo | Approach |
|---|---|---|
| Voice-first command bar / orb | High | Native Compose + voice pipeline above |
| Messages | Medium | Use `RoleManager`/SMS `Telephony` APIs (requires default SMS app role) or simulate with a mock dataset for demo safety — real SMS role-taking is heavyweight for a demo |
| Mail — find contact, draft in user's voice, confirm, send | Medium-High | Gmail API (OAuth) or `Intent.ACTION_SEND` to hand off to Gmail app; agent drafts server-side, Android renders `EmailDraftCard`, confirm → send via API or intent |
| Calls — agent calls on your behalf | Low for true "agent talks on the phone"; Medium for "agent dials for you" | `Intent.ACTION_CALL` gets you dialing-on-behalf; a fully autonomous phone-call agent (agent *speaks* to the other party) is a much bigger project (telephony + real-time voice agent) — scope this as "agent prepares and dials" for the demo unless you want to go deep |
| Background research → structured table | High | Backend tool-call: search API (e.g., Tavily/Bing/SerpAPI) + LLM extraction → JSON rows → `ResearchTableCard` renders live as rows arrive (stream via WebSocket) |
| Product/shopping — "where to buy" | High | Same pattern: image or text query → backend search/compare tool → `ProductComparisonCard` |
| Travel/fare scanning | Medium | Needs a flights API (e.g., Amadeus, Skyscanner partner API, or mocked data for demo) → `FareScannerCard` with animated progress |
| Calendar / Tasks / Navigate | Medium | Calendar: Android `CalendarContract` provider (read/write with permission). Navigate: `Intent` to Google Maps/Samsung Maps with query. Tasks: simple local store, no need for deep OS integration |
| Screen-context awareness ("agent sees what's on screen") | Low-Medium — hardest item | See §6 |

For a demo, I'd **prioritize Mail, Research-table, and Product-comparison** as your three hero flows — they're the most visually impressive, most feasible in your timeframe, and most clearly show the "agent completes work" KPI. Calls and true screen-context are stretch goals.

---

## 6. Screen-context awareness — feasibility note

This is the single hardest thing to replicate faithfully and deserves a clear-eyed take before you commit to it in the demo script:

- **`AccessibilityService`** can read on-screen text/view hierarchy from other apps (with a scary-looking but grantable permission) — this is the realistic route to "agent sees what's on screen," and is how most "read the screen" Android automation tools work.
- **`MediaProjection`** (screen capture API) can literally screenshot the current screen and send it to a vision-capable LLM (e.g., GPT-4o/GPT-5 vision) for interpretation — more robust than parsing view trees for content like product photos/social posts, and matches "agent looks at a product image" from your reference much more directly.
- Both require a **persistent foreground-service permission dialog** the user must accept once per session (`MediaProjection`) or once globally (`AccessibilityService`) — expect a permission prompt in your demo; plan the script around it rather than around it being invisible.
- **Recommendation for a demo**: use `MediaProjection` + a manual trigger (e.g., orb long-press = "look at this") rather than a fully passive always-watching service. This gets you the "agent sees what's on screen and researches it" wow-moment reliably, without building a continuous background-scanning system (which is both a bigger engineering lift and a battery/privacy concern you don't need to solve for a demo).

---

## 7. Do you need a launcher replacement?

Not for a first demo. Two levels, pick based on how much "replaces the phone" you want to show live:

- **Level 1 (recommended for demo)**: Standard app, launched like any other app. Fastest to build, zero risk of breaking the demo device's usability, still lets you show the full experience.
- **Level 2 (stretch)**: Register as a `HOME` intent-filter launcher (`<category android:name="android.intent.category.HOME" />`) so it can be set as the default home screen, genuinely replacing the app grid like the reference. This is straightforward to add later — it's a manifest change plus handling the back-stack/recents correctly — so don't block on it, but it's worth doing near the end if time allows, since "swipe home and this is what you see" is a strong demo beat.

---

## 8. Suggested demo script (2–3 hero flows)

1. **Mail flow**: "Draft an email to [contact] about rescheduling tomorrow's meeting." → orb thinking → `EmailDraftCard` appears with "Ready to send?" → confirm → sent. Mirrors the reference almost exactly and is fully buildable with your existing backend's email logic + Gmail intent/API.
2. **Research flow**: Point the orb (long-press / `MediaProjection` capture) at a product photo or article → orb works → `ResearchTableCard` auto-populates rows (price, source, notes) while you keep talking. This is your strongest visual "agent does work in the background" moment.
3. **Product comparison**: "Find me the best price for [product]." → `ProductComparisonCard` with matches, alt options, buy buttons.

Keep Calls/Calendar/Navigate/Tasks as home-list items that are functional but not necessarily part of the scripted demo — reduces risk.

---

## 9. Tooling & environment setup

You do **not** strictly need an emulator — the S25 as a physical device is a better test target for voice, haptics, real GPU/NPU behavior, and permission prompts, all of which matter for this project. Emulator is optional/secondary.

**Required:**
- **Android Studio** (latest stable, "Ladybug"/current) — provides the Kotlin/Compose tooling, Gradle, ADB, and Layout Inspector.
- **JDK 17+** (bundled with Android Studio).
- **ADB + USB debugging**: enable Developer Options on the S25 (Settings → About phone → tap Build number ×7), enable USB debugging, connect via USB or use **wireless debugging** (Android 11+, no cable needed — convenient for a demo device you'll be walking around with).
- **A backend host**: run the existing FastAPI backend on your dev machine (or deploy to a small cloud box) reachable from the phone — either same-Wi-Fi LAN IP for dev, or a public HTTPS endpoint (e.g., a cheap Railway/Fly.io deploy, consistent with the existing Railway email dependency) so the demo isn't tied to your laptop being on the same network.
- **OpenAI API key** (already required by the existing backend).
- API keys for whichever research/shopping/flights providers you pick for the research & shopping flows (can start mocked, swap to real for a polished demo).

**Optional:**
- **Android Emulator** (via Android Studio's Device Manager) — useful for fast layout iteration without the phone plugged in, or for testing on a different screen size, but not required since you have the target device.
- **Lottie** files/editor if you go the Lottie route for the orb — After Effects isn't required, you can find/commission suitable pre-made "glowing orb" Lottie JSON files.
- **Figma** (or similar) if you want to mock up card layouts before building them in Compose — optional but often speeds up getting the "sci-fi but restrained" look right before writing UI code.

---

## 10. Rough phasing

1. **Backend adaptation**: strip Playwright/browser routes, add research/shopping tool-calls, adjust system prompt for the new action set and persona. Keep FastAPI + existing chat/email/voice route shapes.
2. **Android skeleton**: single-Activity Compose app, home list screen, navigation shell, network client hitting `/health` and a basic chat endpoint.
3. **Orb + voice pipeline (Option A)**: get end-to-end voice round-trip working against the existing `/ws/voice`-style protocol.
4. **Card surfaces**: build `EmailDraftCard` first (most reused backend logic), then `ResearchTableCard`, then `ProductComparisonCard`.
5. **Screen-context capture**: `MediaProjection` manual-trigger flow feeding into the research card.
6. **Polish pass**: orb animation quality, transitions, haptics, dark-mode contrast, optional native STT/TTS swap (Option B), optional HOME-launcher registration.
7. **Demo rehearsal**: script the 2–3 hero flows above, pre-warm any external API calls that are slow, have a fallback/mocked path for anything network-dependent in case of bad demo-day Wi-Fi.

---

## Open questions for you

1. **Mail provider**: is this your real Gmail/Samsung email account for the demo, or a mocked inbox (like the current Railway stand-in)? Determines OAuth setup effort.
2. **Calls**: do you want "agent dials for you" (`ACTION_CALL`, low effort) or an actual "agent speaks to the other party" real-time voice-call agent (much larger scope — telephony integration + realtime voice)? Recommend the former for a demo unless this is a must-have hero feature.
3. **Screen-context trigger**: manual long-press-to-capture (robust, low-risk) vs. always-on background watching (bigger build, battery/privacy tradeoffs) — I'm assuming manual for the demo unless you say otherwise.
4. **Research/shopping data sources**: do you have API access already (SerpAPI, Tavily, a shopping API, a flights API), or should the plan assume mocked/sample data for a first pass and real APIs as a stretch?
5. **Launcher replacement**: is "swipe to home screen and this is what you see" (Level 2, §7) a must-have for the demo, or is "open the app" (Level 1) fine?
6. **Timeline**: how much time do you have before the demo needs to be ready? This changes how aggressively I'd scope stretch items (custom AGSL orb shader, native STT/TTS, HOME launcher, real telephony).
