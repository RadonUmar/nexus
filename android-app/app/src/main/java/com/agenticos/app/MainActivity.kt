package com.agenticos.app

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.core.content.ContextCompat
import com.agenticos.app.agent.AgentClient
import com.agenticos.app.agent.ChatResponse
import com.agenticos.app.ui.home.AppDestination
import com.agenticos.app.ui.home.HomeScreen
import com.agenticos.app.ui.home.MockOutcome
import com.agenticos.app.ui.orb.OrbState
import com.agenticos.app.ui.theme.AgenticOSTheme
import com.agenticos.app.voice.NativeTts
import com.agenticos.app.voice.VoiceCaptureEvent
import com.agenticos.app.voice.VoiceCaptureManager
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {
    private lateinit var voiceCapture: VoiceCaptureManager
    private lateinit var tts: NativeTts
    private val agentClient = AgentClient()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        voiceCapture = VoiceCaptureManager(this)
        tts = NativeTts(this)

        setContent {
            AgenticOSTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    var orbState by remember { mutableStateOf(OrbState.Idle) }
                    var destination by remember { mutableStateOf(AppDestination.Home) }
                    var mockOutcome by remember { mutableStateOf(MockOutcome.None) }
                    var heardText by remember { mutableStateOf<String?>(null) }
                    var assistantReply by remember { mutableStateOf("Ready when you are.") }
                    var activeTurn by remember { mutableStateOf<Job?>(null) }
                    var hasMicPermission by remember {
                        mutableStateOf(
                            ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) ==
                                PackageManager.PERMISSION_GRANTED,
                        )
                    }
                    val scope = rememberCoroutineScope()

                    val permissionLauncher = rememberLauncherForActivityResult(
                        ActivityResultContracts.RequestPermission(),
                    ) { granted -> hasMicPermission = granted }

                    LaunchedEffect(Unit) {
                        if (!hasMicPermission) permissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
                    }

                    LaunchedEffect(orbState) {
                        if (orbState == OrbState.Done) {
                            kotlinx.coroutines.delay(2200)
                            orbState = OrbState.Idle
                        }
                    }

                    HomeScreen(
                        orbState = orbState,
                        destination = destination,
                        mockOutcome = mockOutcome,
                        heardText = heardText,
                        assistantReply = assistantReply,
                        onDestinationChange = { destination = it },
                        onOrbTap = {
                            if (!hasMicPermission) {
                                permissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
                                return@HomeScreen
                            }

                            if (orbState != OrbState.Idle && orbState != OrbState.Done) {
                                val restartAfterInterrupt = tts.isSpeaking()
                                activeTurn?.cancel()
                                tts.stop()
                                orbState = OrbState.Idle
                                assistantReply = "Stopped."
                                if (!restartAfterInterrupt) return@HomeScreen
                            }

                            activeTurn = scope.launch {
                                orbState = OrbState.Listening
                                voiceCapture.listen().collect { event ->
                                    when (event) {
                                        is VoiceCaptureEvent.Result -> {
                                            heardText = event.text
                                            val immediateMockOutcome = event.text.toMockOutcome()
                                            mockOutcome = immediateMockOutcome
                                            destination = event.text.toDestination() ?: destination
                                            if (immediateMockOutcome != MockOutcome.None) {
                                                assistantReply = immediateMockOutcome.successReply() ?: "Done."
                                                if (immediateMockOutcome == MockOutcome.ScriptUploaded || immediateMockOutcome == MockOutcome.FeedbackQueued) {
                                                    scope.launch {
                                                        runCatching {
                                                            agentClient.recordDemoCommand(event.text)
                                                        }
                                                    }
                                                }
                                                orbState = OrbState.Working
                                                tts.speak(assistantReply)
                                                orbState = OrbState.Done
                                                return@collect
                                            }
                                            orbState = OrbState.Thinking
                                            try {
                                                val reply = agentClient.sendMessage(event.text)
                                                mockOutcome = event.text.toMockOutcome().takeUnless { it == MockOutcome.None }
                                                    ?: reply.toMockOutcome()
                                                assistantReply = mockOutcome.successReply()
                                                    ?: reply.response?.shortenForSpeech()
                                                    ?: "Done."
                                                destination = reply.toDestination() ?: event.text.toDestination() ?: destination
                                                orbState = OrbState.Working
                                                tts.speak(assistantReply)
                                                orbState = OrbState.Done
                                            } catch (exc: CancellationException) {
                                                throw exc
                                            } catch (exc: Exception) {
                                                assistantReply = "Updated the UI. Backend missed that one."
                                                tts.speak(assistantReply)
                                                orbState = OrbState.Done
                                            }
                                        }
                                        is VoiceCaptureEvent.Error -> {
                                            assistantReply = event.message.shortenForSpeech()
                                            orbState = OrbState.Idle
                                        }
                                        VoiceCaptureEvent.Done -> Unit
                                    }
                                }
                            }
                        },
                    )
                }
            }
        }
    }

    override fun onDestroy() {
        if (::tts.isInitialized) tts.shutdown()
        super.onDestroy()
    }

    private fun ChatResponse.toDestination(): AppDestination? {
        val normalizedAction = action?.lowercase().orEmpty()
        val appName = data?.get("app")?.toString()?.lowercase().orEmpty()
        val title = data?.get("title")?.toString()?.lowercase().orEmpty()
        val target = "$normalizedAction $appName $title".lowercase()
        return target.toDestination()
    }

    private fun ChatResponse.toMockOutcome(): MockOutcome {
        val normalizedAction = action?.lowercase().orEmpty()
        val appName = data?.get("app")?.toString()?.lowercase().orEmpty()
        val instructions = data?.get("instructions")?.toString()?.lowercase().orEmpty()
        val target = "$normalizedAction $appName $instructions ${response.orEmpty()}".lowercase()
        return target.toMockOutcome()
    }

    private fun String.toDestination(): AppDestination? {
        val text = lowercase()
        return when {
            listOf("home", "main", "back", "close").any(text::contains) -> AppDestination.Home
            listOf("mail", "email", "inbox", "draft", "compose").any(text::contains) -> AppDestination.Mail
            listOf("message", "texts", "sms", "chat").any(text::contains) -> AppDestination.Messages
            listOf("calendar", "schedule", "meeting").any(text::contains) -> AppDestination.Calendar
            listOf("navigate", "navigation", "map", "directions", "route").any(text::contains) -> AppDestination.Navigate
            listOf("search", "look up", "find", "research", "browser", "google").any(text::contains) -> AppDestination.Search
            listOf("task", "todo", "to do", "reminder").any(text::contains) -> AppDestination.Tasks
            listOf("code", "script", "command", "terminal", "pc", "computer", "project", "feedback", "agent").any(text::contains) -> AppDestination.Code
            else -> null
        }
    }

    private fun String.toMockOutcome(): MockOutcome {
        val text = lowercase()
        return when {
            listOf("send an email", "send email", "email sent", "send it", "compose email", "send a reply", "reply to sarah", "respond to sarah", "send sarah").any(text::contains) -> MockOutcome.EmailSent
            listOf("give feedback", "project feedback", "leave feedback", "add feedback", "note on this project").any(text::contains) -> MockOutcome.FeedbackQueued
            listOf("run script", "run this script", "run the script", "run the deploy script", "send a command", "run a command", "upload script", "upload my computer code", "upload code", "script uploaded", "command to my pc", "tell the agent", "change the project", "update the project", "fix the project", "make it change").any(text::contains) -> MockOutcome.ScriptUploaded
            else -> MockOutcome.None
        }
    }

    private fun MockOutcome.successReply(): String? = when (this) {
        MockOutcome.EmailSent -> "Email sent."
        MockOutcome.ScriptUploaded -> "Script uploaded."
        MockOutcome.FeedbackQueued -> "Feedback queued."
        MockOutcome.None -> null
    }

    private fun String.shortenForSpeech(): String {
        val cleaned = replace(Regex("\\s+"), " ").trim()
        val firstSentence = cleaned.split(Regex("(?<=[.!?])\\s+")).firstOrNull().orEmpty()
        val words = firstSentence.split(" ").filter { it.isNotBlank() }
        return if (words.size <= 16) firstSentence else words.take(16).joinToString(" ") + "."
    }
}
