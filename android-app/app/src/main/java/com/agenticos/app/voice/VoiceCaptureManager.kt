package com.agenticos.app.voice

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.util.Log
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow

sealed class VoiceCaptureEvent {
    data class Result(val text: String) : VoiceCaptureEvent()
    data class Error(val message: String) : VoiceCaptureEvent()
    object Done : VoiceCaptureEvent()
}

/**
 * Wraps Android's on-device SpeechRecognizer — free, no network round-trip,
 * lower latency than sending raw audio to a server for Whisper-style STT.
 *
 * Must be collected from the main thread: SpeechRecognizer's create/start/destroy
 * calls all assert they're on the main looper.
 */
class VoiceCaptureManager(private val context: Context) {

    fun isAvailable(): Boolean = SpeechRecognizer.isRecognitionAvailable(context)

    fun listen(): Flow<VoiceCaptureEvent> = callbackFlow {
        if (!SpeechRecognizer.isRecognitionAvailable(context)) {
            trySend(VoiceCaptureEvent.Error("No speech recognition service on this device"))
            trySend(VoiceCaptureEvent.Done)
            close()
            return@callbackFlow
        }

        val recognizer = SpeechRecognizer.createSpeechRecognizer(context)
        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, false)
            putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
            // Some recognizer implementations (Samsung's included) reject requests
            // that don't name the caller.
            putExtra(RecognizerIntent.EXTRA_CALLING_PACKAGE, context.packageName)
        }

        recognizer.setRecognitionListener(object : RecognitionListener {
            override fun onResults(results: Bundle?) {
                val text = results
                    ?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                    ?.firstOrNull()
                    .orEmpty()
                if (text.isNotBlank()) {
                    Log.d(TAG, "Recognized: $text")
                    trySend(VoiceCaptureEvent.Result(text))
                } else {
                    trySend(VoiceCaptureEvent.Error("No speech recognized"))
                }
                trySend(VoiceCaptureEvent.Done)
                close()
            }

            override fun onError(error: Int) {
                val message = describe(error)
                Log.w(TAG, "Speech recognition error $error: $message")
                trySend(VoiceCaptureEvent.Error(message))
                trySend(VoiceCaptureEvent.Done)
                close()
            }

            override fun onReadyForSpeech(params: Bundle?) = Unit
            override fun onBeginningOfSpeech() = Unit
            override fun onRmsChanged(rmsdB: Float) = Unit
            override fun onBufferReceived(buffer: ByteArray?) = Unit
            override fun onEndOfSpeech() = Unit
            override fun onPartialResults(partialResults: Bundle?) = Unit
            override fun onEvent(eventType: Int, params: Bundle?) = Unit
        })

        recognizer.startListening(intent)

        // close() above unblocks this, which is what actually releases the
        // recognizer — without it every orb tap leaked one.
        awaitClose {
            recognizer.stopListening()
            recognizer.destroy()
        }
    }

    private fun describe(error: Int): String = when (error) {
        SpeechRecognizer.ERROR_AUDIO -> "Audio recording error"
        SpeechRecognizer.ERROR_CLIENT -> "Client side error"
        SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS -> "Microphone permission denied"
        SpeechRecognizer.ERROR_NETWORK -> "Network error"
        SpeechRecognizer.ERROR_NETWORK_TIMEOUT -> "Network timeout"
        SpeechRecognizer.ERROR_NO_MATCH -> "Didn't catch that"
        SpeechRecognizer.ERROR_RECOGNIZER_BUSY -> "Recognizer busy"
        SpeechRecognizer.ERROR_SERVER -> "Server error"
        SpeechRecognizer.ERROR_SPEECH_TIMEOUT -> "No speech detected"
        else -> "Speech recognition error $error"
    }

    private companion object {
        const val TAG = "VoiceCapture"
    }
}
