package com.agenticos.app.voice

import android.content.Context
import android.speech.tts.TextToSpeech
import android.util.Log
import java.util.Locale

/**
 * Wraps Android's on-device TextToSpeech — free, no network round-trip for audio
 * synthesis, keeps the reply-to-speech leg local and low-latency.
 *
 * The engine binds asynchronously, so anything touching it (setLanguage included)
 * has to wait for onInit. A speak() that lands before then is held in [pending]
 * and flushed once the engine is up — otherwise the first reply after a cold
 * start is silently dropped.
 */
class NativeTts(context: Context) {
    private var ready = false
    private var pending: String? = null
    private lateinit var tts: TextToSpeech

    init {
        tts = TextToSpeech(context) { status ->
            if (status != TextToSpeech.SUCCESS) {
                Log.e(TAG, "TextToSpeech init failed with status $status")
                return@TextToSpeech
            }
            val result = tts.setLanguage(Locale.US)
            if (result == TextToSpeech.LANG_MISSING_DATA || result == TextToSpeech.LANG_NOT_SUPPORTED) {
                Log.w(TAG, "en-US voice data unavailable; using engine default")
            }
            ready = true
            pending?.let { queued ->
                pending = null
                speak(queued)
            }
        }
    }

    fun speak(text: String) {
        if (text.isBlank()) return
        if (!ready) {
            pending = text
            return
        }
        tts.speak(text, TextToSpeech.QUEUE_FLUSH, null, UTTERANCE_ID)
    }

    fun isSpeaking(): Boolean = ready && tts.isSpeaking

    fun stop() {
        pending = null
        tts.stop()
    }

    fun shutdown() {
        pending = null
        tts.stop()
        tts.shutdown()
    }

    private companion object {
        const val TAG = "NativeTts"
        const val UTTERANCE_ID = "nexus-reply"
    }
}
