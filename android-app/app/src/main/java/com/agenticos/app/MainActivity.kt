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
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.core.content.ContextCompat
import com.agenticos.app.agent.AgentClient
import com.agenticos.app.ui.home.HomeScreen
import com.agenticos.app.ui.orb.OrbState
import com.agenticos.app.ui.theme.AgenticOSTheme
import com.agenticos.app.voice.NativeTts
import com.agenticos.app.voice.VoiceCaptureEvent
import com.agenticos.app.voice.VoiceCaptureManager
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

                    DisposableEffect(Unit) {
                        onDispose { tts.shutdown() }
                    }

                    LaunchedEffect(orbState) {
                        if (orbState == OrbState.Done) {
                            kotlinx.coroutines.delay(2200)
                            orbState = OrbState.Idle
                        }
                    }

                    HomeScreen(
                        orbState = orbState,
                        onOrbTap = {
                            if (!hasMicPermission) {
                                permissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
                                return@HomeScreen
                            }
                            if (orbState != OrbState.Idle && orbState != OrbState.Done) return@HomeScreen

                            scope.launch {
                                orbState = OrbState.Listening
                                voiceCapture.listen().collect { event ->
                                    when (event) {
                                        is VoiceCaptureEvent.Result -> {
                                            orbState = OrbState.Thinking
                                            scope.launch {
                                                try {
                                                    val reply = agentClient.sendMessage(event.text)
                                                    orbState = OrbState.Working
                                                    val spoken = reply.response ?: "Done."
                                                    tts.speak(spoken)
                                                    orbState = OrbState.Done
                                                } catch (exc: Exception) {
                                                    tts.speak("Sorry, I couldn't reach the backend.")
                                                    orbState = OrbState.Idle
                                                }
                                            }
                                        }
                                        is VoiceCaptureEvent.Error -> orbState = OrbState.Idle
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
}
