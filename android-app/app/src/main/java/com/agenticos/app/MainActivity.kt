package com.agenticos.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import com.agenticos.app.ui.home.HomeScreen
import com.agenticos.app.ui.orb.OrbState
import com.agenticos.app.ui.theme.AgenticOSTheme
import kotlinx.coroutines.delay

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        setContent {
            AgenticOSTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    var orbState by remember { mutableStateOf(OrbState.Idle) }

                    // Demo-only: cycles orb states so the visual design can be
                    // previewed without a live backend. Remove once VoiceSocketClient
                    // / AgentClient drive orbState from real call state
                    // (Option A, per SAMSUNG_AGENTIC_OS_PLAN.md §4).
                    LaunchedEffect(Unit) {
                        val cycle = listOf(
                            OrbState.Idle to 3500L,
                            OrbState.Listening to 2200L,
                            OrbState.Thinking to 1800L,
                            OrbState.Working to 2200L,
                            OrbState.Done to 2200L,
                        )
                        while (true) {
                            for ((state, holdMs) in cycle) {
                                orbState = state
                                delay(holdMs)
                            }
                        }
                    }

                    HomeScreen(orbState = orbState)
                }
            }
        }
    }
}
