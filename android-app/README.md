# Agentic OS — Android App

Native Kotlin + Jetpack Compose client for the Samsung Galaxy S25 demo.
Full plan: [`../SAMSUNG_AGENTIC_OS_PLAN.md`](../SAMSUNG_AGENTIC_OS_PLAN.md).

## What's here (scaffold status)

- Gradle project skeleton (`settings.gradle.kts`, `build.gradle.kts`, `app/build.gradle.kts`)
- `MainActivity` — single-Activity Compose host, edge-to-edge, dark theme
- `HomeScreen` — vertical list of core functions (Messages, Calendar, Navigate, Search, Tasks, Mail) + orb
- `Orb` — placeholder pulsing radial-gradient Canvas orb with `OrbState` (Idle/Listening/Thinking/Working/Done). Swap for Lottie once per-state animation files exist (see plan §3).
- `AgentClient` — OkHttp/Moshi REST client wired to the backend's `/api/chat` endpoint (matches `agentic_os/chat.py`'s `{response, action, data}` shape)

Not yet built: voice pipeline wiring (`VoiceSocketClient`), card composables (`EmailDraftCard`, `ResearchTableCard`, `ProductComparisonCard`), `MediaProjection` screen-context capture, native STT/TTS. These come next per the plan's phasing (§10).

## First-time setup

1. **Finish the Android Studio setup wizard** (installed via winget) — on first launch it downloads the Android SDK, platform-tools (adb), and a default emulator image. Accept the SDK license when prompted. This step is required before anything below will build.
2. **Open this folder** (`android-app/`) directly in Android Studio via *File → Open*. Do **not** open the repo root — the Android project root is `android-app/`.
3. Android Studio will offer to generate the Gradle wrapper jar (`gradle-wrapper.jar`, `gradlew`, `gradlew.bat`) automatically on first sync since only `gradle-wrapper.properties` is checked in here — let it do so, or run `gradle wrapper` yourself if you have a system Gradle install.
4. Let Gradle sync finish (first sync downloads dependencies — can take a few minutes).

## Running on the physical S25 (recommended over emulator)

1. On the S25: Settings → About phone → tap **Build number** 7 times → enables Developer Options.
2. Settings → Developer options → enable **USB debugging** (or **Wireless debugging** to skip the cable).
3. Connect via USB (accept the RSA fingerprint prompt on the phone), or pair wireless debugging from Android Studio's Device Manager.
4. In Android Studio, select the S25 in the device dropdown and hit Run ▶.

## Pointing the app at your backend

`app/build.gradle.kts` sets `BACKEND_BASE_URL` via `buildConfigField`. It currently defaults to `http://10.0.2.2:8000` (the special alias the Android **emulator** uses to reach `localhost` on your dev machine) — this will **not** work from the physical S25.

When testing on the physical device:
- Run the FastAPI backend (`uvicorn main:app --host 0.0.0.0 --port 8000` from the repo root) on your dev machine.
- Find your dev machine's LAN IP (`ipconfig` → IPv4 address), make sure the S25 is on the same Wi-Fi.
- Change `BACKEND_BASE_URL` in `app/build.gradle.kts` to `http://<your-lan-ip>:8000`.
- `usesCleartextTraffic="true"` is already set in the manifest for plain-HTTP dev traffic — tighten this before any real deployment.

For demo day, prefer deploying the backend somewhere reachable over HTTPS (consistent with the existing Railway dependency for email) so the demo isn't tied to a laptop + shared Wi-Fi.

## Emulator (optional)

Not required since you're targeting a physical S25, but if you want one for fast layout iteration: Android Studio's Device Manager → Create Device → pick a Pixel profile → choose an **ARM64** system image (matches this dev machine's architecture and the S25's Snapdragon, so it runs without x86 translation overhead).
