package com.agenticos.app.ui.orb

/**
 * Mirrors the state machine the backend voice/chat pipeline drives:
 * idle -> listening -> thinking -> working -> done -> idle.
 */
enum class OrbState {
    Idle,
    Listening,
    Thinking,
    Working,
    Done,
}
