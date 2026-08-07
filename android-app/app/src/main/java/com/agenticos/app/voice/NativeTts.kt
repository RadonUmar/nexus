package com.agenticos.app.voice

import android.content.Context
import android.speech.tts.TextToSpeech
import java.util.Locale

/**
 * Wraps Android's on-device TextToSpeech — free, no network round-trip for audio
 * synthesis, keeps the reply-to-speech leg local and low-latency.
 */
class NativeTts(context: Context) {
    private var ready = false
    private val tts = TextToSpeech(context) { status ->
        ready = status == TextToSpeech.SUCCESS
    }

    init {
        tts.language = Locale.US
    }

    fun speak(text: String) {
        if (!ready || text.isBlank()) return
        tts.speak(text, TextToSpeech.QUEUE_FLUSH, null, "nexus-reply")
    }

    fun stop() {
        tts.stop()
    }

    fun shutdown() {
        tts.stop()
        tts.shutdown()
    }
}
