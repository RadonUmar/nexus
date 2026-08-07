package com.agenticos.app.ui.home

import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInHorizontally
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutHorizontally
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.outlined.CalendarMonth
import androidx.compose.material.icons.outlined.CheckCircleOutline
import androidx.compose.material.icons.outlined.Code
import androidx.compose.material.icons.outlined.MailOutline
import androidx.compose.material.icons.outlined.Message
import androidx.compose.material.icons.outlined.Navigation
import androidx.compose.material.icons.outlined.Search
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.agenticos.app.ui.orb.Orb
import com.agenticos.app.ui.orb.OrbState
import com.agenticos.app.ui.theme.AgenticBlack
import com.agenticos.app.ui.theme.AgenticBlue
import com.agenticos.app.ui.theme.AgenticCyan
import com.agenticos.app.ui.theme.AgenticGreen
import com.agenticos.app.ui.theme.AgenticStroke
import com.agenticos.app.ui.theme.AgenticSurface
import com.agenticos.app.ui.theme.AgenticTextPrimary
import com.agenticos.app.ui.theme.AgenticTextSecondary
import com.agenticos.app.ui.theme.AgenticTextTertiary
import com.agenticos.app.ui.theme.AgenticViolet
import com.agenticos.app.ui.theme.AgenticVoid

enum class AppDestination(val label: String, val icon: ImageVector) {
    Home("Home", Icons.Outlined.Search),
    Messages("Messages", Icons.Outlined.Message),
    Calendar("Calendar", Icons.Outlined.CalendarMonth),
    Navigate("Navigate", Icons.Outlined.Navigation),
    Search("Search", Icons.Outlined.Search),
    Tasks("Tasks", Icons.Outlined.CheckCircleOutline),
    Mail("Mail", Icons.Outlined.MailOutline),
    Code("Code", Icons.Outlined.Code),
}

enum class MockOutcome {
    None,
    EmailSent,
    ScriptUploaded,
    FeedbackQueued,
}

private data class CoreFunction(val destination: AppDestination)

private val CORE_FUNCTIONS = listOf(
    CoreFunction(AppDestination.Messages),
    CoreFunction(AppDestination.Calendar),
    CoreFunction(AppDestination.Navigate),
    CoreFunction(AppDestination.Search),
    CoreFunction(AppDestination.Tasks),
    CoreFunction(AppDestination.Mail),
    CoreFunction(AppDestination.Code),
)

@Composable
fun HomeScreen(
    orbState: OrbState,
    destination: AppDestination = AppDestination.Home,
    mockOutcome: MockOutcome = MockOutcome.None,
    heardText: String? = null,
    assistantReply: String = "Ready when you are.",
    onDestinationChange: (AppDestination) -> Unit = {},
    onOrbTap: () -> Unit = {},
) {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(
                Brush.verticalGradient(
                    colors = listOf(AgenticVoid, AgenticBlack, AgenticBlack),
                ),
            ),
    ) {
        AnimatedContent(
            targetState = destination,
            transitionSpec = {
                fadeIn(tween(220)) + slideInHorizontally(tween(260)) { it / 8 } togetherWith
                    fadeOut(tween(160)) + slideOutHorizontally(tween(220)) { -it / 10 }
            },
            label = "destination",
        ) { currentDestination ->
            if (currentDestination == AppDestination.Home) {
                HomeContent(
                    orbState = orbState,
                    heardText = heardText,
                    assistantReply = assistantReply,
                    onDestinationChange = onDestinationChange,
                )
            } else {
                MockSection(
                        destination = currentDestination,
                        mockOutcome = mockOutcome,
                        heardText = heardText,
                    assistantReply = assistantReply,
                    onClose = { onDestinationChange(AppDestination.Home) },
                )
            }
        }

        OrbDock(orbState = orbState, onOrbTap = onOrbTap)
    }
}

@Composable
private fun HomeContent(
    orbState: OrbState,
    heardText: String?,
    assistantReply: String,
    onDestinationChange: (AppDestination) -> Unit,
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .statusBarsPadding()
            .padding(horizontal = 28.dp),
    ) {
        AnimatedVisibility(
            visible = true,
            enter = fadeIn(tween(500)) + slideInVertically(tween(500)) { -20 },
        ) {
            GreetingHeader(orbState = orbState)
        }

        Spacer(modifier = Modifier.height(28.dp))

        CORE_FUNCTIONS.forEachIndexed { index, function ->
            AnimatedVisibility(
                visible = true,
                enter = fadeIn(tween(400, delayMillis = index * 60)) +
                    slideInVertically(tween(400, delayMillis = index * 60)) { 24 },
            ) {
                FunctionRow(
                    destination = function.destination,
                    selected = false,
                    onClick = { onDestinationChange(function.destination) },
                )
            }
        }

        Spacer(modifier = Modifier.height(12.dp))

        Text(
            text = heardText ?: assistantReply,
            color = AgenticTextTertiary,
            fontSize = 12.sp,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
            modifier = Modifier.fillMaxWidth(),
        )
    }
}

@Composable
private fun GreetingHeader(orbState: OrbState) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column {
            Text(
                text = "nexus",
                color = AgenticTextPrimary,
                fontSize = 26.sp,
                fontWeight = FontWeight.Light,
            )
            Text(
                text = "Tell me what you need",
                color = AgenticTextTertiary,
                fontSize = 13.sp,
            )
        }
        StatusDot(orbState = orbState)
    }
}

@Composable
private fun StatusDot(orbState: OrbState) {
    val color = if (orbState == OrbState.Done) AgenticBlue else AgenticTextTertiary
    Box(
        modifier = Modifier
            .size(8.dp)
            .clip(CircleShape)
            .background(color)
            .alpha(if (orbState == OrbState.Idle) 0.4f else 1f),
    )
}

@Composable
private fun FunctionRow(destination: AppDestination, selected: Boolean, onClick: () -> Unit) {
    val interactionSource = remember { MutableInteractionSource() }
    val isPressed by interactionSource.collectIsPressedAsState()

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(18.dp))
            .background(if (isPressed || selected) AgenticSurface else Color.Transparent)
            .clickable(interactionSource = interactionSource, indication = null, onClick = onClick)
            .padding(vertical = 16.dp, horizontal = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Box(
            modifier = Modifier
                .size(38.dp)
                .clip(RoundedCornerShape(12.dp))
                .background(AgenticSurface),
            contentAlignment = Alignment.Center,
        ) {
            Icon(
                imageVector = destination.icon,
                contentDescription = destination.label,
                tint = if (selected) AgenticBlue else AgenticTextSecondary,
                modifier = Modifier.size(18.dp),
            )
        }

        Spacer(modifier = Modifier.width(16.dp))

        Text(
            text = destination.label,
            color = AgenticTextPrimary,
            fontSize = 21.sp,
            fontWeight = FontWeight.Light,
            modifier = Modifier.weight(1f),
        )
    }

    Box(
        modifier = Modifier
            .fillMaxWidth()
            .height(1.dp)
            .background(AgenticStroke.copy(alpha = 0.5f)),
    )
}

@Composable
private fun VoiceStatusCard(heardText: String?, assistantReply: String) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(18.dp))
            .background(AgenticSurface.copy(alpha = 0.78f))
            .padding(16.dp),
    ) {
        Text(
            text = heardText?.let { "\"$it\"" } ?: "Say \"open messages\", \"show calendar\", or \"search Qualcomm\"",
            color = AgenticTextPrimary,
            fontSize = 14.sp,
            maxLines = 2,
            overflow = TextOverflow.Ellipsis,
        )
        Spacer(modifier = Modifier.height(6.dp))
        Text(
            text = assistantReply,
            color = AgenticTextSecondary,
            fontSize = 12.sp,
            maxLines = 2,
            overflow = TextOverflow.Ellipsis,
        )
    }
}

@Composable
private fun MockSection(
    destination: AppDestination,
    mockOutcome: MockOutcome,
    heardText: String?,
    assistantReply: String,
    onClose: () -> Unit,
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .statusBarsPadding()
            .padding(horizontal = 20.dp),
    ) {
        SectionHeader(destination = destination, onClose = onClose)
        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(top = 8.dp, bottom = 220.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            item { VoiceStatusCard(heardText = heardText, assistantReply = assistantReply) }
            when (destination) {
                AppDestination.Mail -> item { MailMockContent(mockOutcome = mockOutcome) }
                AppDestination.Messages -> item { MessagesMockContent() }
                AppDestination.Code -> item { CodeMockContent(mockOutcome = mockOutcome) }
                else -> {
                    sectionItems(destination).forEach { mockItem ->
                        item { MockCard(item = mockItem) }
                    }
                }
            }
        }
    }
}

@Composable
private fun SectionHeader(destination: AppDestination, onClose: () -> Unit) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(vertical = 12.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(
                modifier = Modifier
                    .size(38.dp)
                    .clip(RoundedCornerShape(12.dp))
                    .background(AgenticSurface),
                contentAlignment = Alignment.Center,
            ) {
                Icon(destination.icon, contentDescription = destination.label, tint = AgenticBlue, modifier = Modifier.size(18.dp))
            }
            Spacer(modifier = Modifier.width(12.dp))
            Text(destination.label.lowercase(), color = AgenticTextPrimary, fontSize = 22.sp, fontWeight = FontWeight.Light)
        }
        IconButton(onClick = onClose) {
            Icon(imageVector = Icons.Filled.Close, contentDescription = "Close", tint = AgenticTextSecondary)
        }
    }
}

@Composable
private fun MockCard(item: MockUiItem) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(20.dp))
            .background(AgenticSurface)
            .padding(18.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(
                modifier = Modifier
                    .size(40.dp)
                    .clip(CircleShape)
                    .background(item.color.copy(alpha = 0.16f)),
                contentAlignment = Alignment.Center,
            ) {
                Text(item.initial, color = item.color, fontSize = 15.sp, fontWeight = FontWeight.Medium)
            }
            Spacer(modifier = Modifier.width(12.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(item.title, color = AgenticTextPrimary, fontSize = 15.sp, fontWeight = FontWeight.Medium)
                Text(item.subtitle, color = AgenticTextSecondary, fontSize = 13.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
            }
            if (item.meta.isNotBlank()) {
                Text(item.meta, color = AgenticTextTertiary, fontSize = 12.sp)
            }
        }
        Spacer(modifier = Modifier.height(10.dp))
        Box(modifier = Modifier.fillMaxWidth().height(1.dp).background(AgenticStroke.copy(alpha = 0.5f)))
        Spacer(modifier = Modifier.height(10.dp))
        Text(item.body, color = AgenticTextSecondary, fontSize = 14.sp, lineHeight = 20.sp)
    }
}

@Composable
private fun MailMockContent(mockOutcome: MockOutcome) {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        if (mockOutcome == MockOutcome.EmailSent) {
            SuccessCard(
                title = "email sent",
                body = "To Sarah Chen. Subject: Phone demo update.",
                color = AgenticGreen,
            )
        }
        SectionMetricRow(
            items = listOf(
                Metric(if (mockOutcome == MockOutcome.EmailSent) "sent" else "12", if (mockOutcome == MockOutcome.EmailSent) "status" else "inbox"),
                Metric("3", "priority"),
                Metric(if (mockOutcome == MockOutcome.EmailSent) "0" else "1", "draft"),
            ),
        )
        MailRow(
            sender = "Sarah Chen",
            subject = "Re: Q3 roadmap sync",
            preview = "Thursday works. I can bring the design lead and final tradeoff notes.",
            time = "9:41",
            tag = "needs reply",
            color = AgenticBlue,
        )
        MailRow(
            sender = "Qualcomm Demo Team",
            subject = "Phone build checklist",
            preview = "Latest APK is installed. Voice navigation and backend tunnel are ready.",
            time = "9:12",
            tag = "demo",
            color = AgenticViolet,
        )
        MailDraftCard(sent = mockOutcome == MockOutcome.EmailSent)
        CommandRow(commands = listOf("summarize inbox", "draft reply", "archive low priority"))
    }
}

@Composable
private fun MessagesMockContent() {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        SectionMetricRow(
            items = listOf(
                Metric("5", "threads"),
                Metric("2", "unread"),
                Metric("now", "reply ready"),
            ),
        )
        MessageThreadCard(
            name = "Maya",
            message = "Can you show the phone demo after the intro?",
            reply = "Yep, the build is live on device. I’ll run it right after intro.",
            time = "now",
            color = AgenticCyan,
        )
        MessageThreadCard(
            name = "Alex",
            message = "Do we have the Qualcomm AI Hub beat in the pitch?",
            reply = "Added a quick on-device AI angle and the Nexus control flow.",
            time = "8m",
            color = AgenticViolet,
        )
        CommandRow(commands = listOf("reply to Maya", "summarize Alex", "mark all read"))
    }
}

@Composable
private fun CodeMockContent(mockOutcome: MockOutcome) {
    val isCodeAction = mockOutcome == MockOutcome.ScriptUploaded || mockOutcome == MockOutcome.FeedbackQueued
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        if (isCodeAction) {
            SuccessCard(
                title = if (mockOutcome == MockOutcome.FeedbackQueued) "feedback queued" else "script uploaded",
                body = if (mockOutcome == MockOutcome.FeedbackQueued) {
                    "Nexus attached your note to /nexus/mobile-demo."
                } else {
                    "Nexus routed deploy_preview.sh into /nexus/mobile-demo."
                },
                color = AgenticCyan,
            )
        }
        SectionMetricRow(
            items = listOf(
                Metric("3", "projects"),
                Metric(if (isCodeAction) "queued" else "ready", "agent"),
                Metric("local", "pc bridge"),
            ),
        )
        ProjectCard(
            path = "/nexus/mobile-demo",
            name = "phone voice shell",
            status = if (mockOutcome == MockOutcome.FeedbackQueued) "feedback queued" else if (mockOutcome == MockOutcome.ScriptUploaded) "command queued" else "active",
            accent = AgenticCyan,
            dirs = listOf("android-app/", "agentic_os/", "static/"),
            scripts = listOf("deploy_preview.sh", "run_backend.sh", "inspect_device.sh"),
        )
        ProjectCard(
            path = "/projects/site-lab",
            name = "web dashboard",
            status = "watching",
            accent = AgenticViolet,
            dirs = listOf("templates/", "static/", "routes/"),
            scripts = listOf("sync_agent_events.sh", "preview_ui.sh"),
        )
        AgentRelayCard(mockOutcome = mockOutcome)
        CommandRow(commands = listOf("run project script", "give feedback", "show dirs"))
    }
}

@Composable
private fun ProjectCard(
    path: String,
    name: String,
    status: String,
    accent: Color,
    dirs: List<String>,
    scripts: List<String>,
) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(22.dp))
            .background(AgenticSurface)
            .padding(16.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(
                modifier = Modifier
                    .size(34.dp)
                    .clip(RoundedCornerShape(11.dp))
                    .background(accent.copy(alpha = 0.16f)),
                contentAlignment = Alignment.Center,
            ) {
                Text("⌁", color = accent, fontSize = 20.sp, fontWeight = FontWeight.Medium)
            }
            Spacer(modifier = Modifier.width(12.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(name, color = AgenticTextPrimary, fontSize = 15.sp, fontWeight = FontWeight.Medium)
                Text(path, color = AgenticTextTertiary, fontSize = 11.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
            }
            CommandPill(text = status, color = accent)
        }
        Spacer(modifier = Modifier.height(14.dp))
        Text("directories", color = AgenticTextTertiary, fontSize = 11.sp)
        Spacer(modifier = Modifier.height(8.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(7.dp), modifier = Modifier.fillMaxWidth()) {
            dirs.forEach { dir ->
                FilePill(text = dir, color = AgenticBlue)
            }
        }
        Spacer(modifier = Modifier.height(12.dp))
        Text("scripts", color = AgenticTextTertiary, fontSize = 11.sp)
        Spacer(modifier = Modifier.height(8.dp))
        scripts.forEach { script ->
            ScriptRow(script = script, accent = accent)
        }
    }
}

@Composable
private fun FilePill(text: String, color: Color) {
    Text(
        text = text,
        color = AgenticTextPrimary,
        fontSize = 11.sp,
        maxLines = 1,
        overflow = TextOverflow.Ellipsis,
        modifier = Modifier
            .clip(RoundedCornerShape(999.dp))
            .background(color.copy(alpha = 0.12f))
            .padding(horizontal = 9.dp, vertical = 6.dp),
    )
}

@Composable
private fun ScriptRow(script: String, accent: Color) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 5.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text("sh", color = accent, fontSize = 11.sp, fontWeight = FontWeight.Medium)
        Spacer(modifier = Modifier.width(10.dp))
        Text(script, color = AgenticTextPrimary, fontSize = 13.sp, modifier = Modifier.weight(1f))
        Text("ready", color = AgenticTextTertiary, fontSize = 11.sp)
    }
}

@Composable
private fun AgentRelayCard(mockOutcome: MockOutcome) {
    val active = mockOutcome == MockOutcome.ScriptUploaded || mockOutcome == MockOutcome.FeedbackQueued
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(20.dp))
            .background(Color(0xFF090A10))
            .padding(16.dp),
    ) {
        Text("agent relay", color = AgenticCyan, fontSize = 13.sp, fontWeight = FontWeight.Medium)
        Spacer(modifier = Modifier.height(10.dp))
        Text("phone → backend dashboard → PC project", color = AgenticTextPrimary, fontSize = 12.sp)
        Spacer(modifier = Modifier.height(6.dp))
        Text(
            if (mockOutcome == MockOutcome.FeedbackQueued) {
                "feedback note mirrored to the desktop relay"
            } else if (active) {
                "deploy_preview.sh queued with voice context"
            } else {
                "waiting for project command or feedback"
            },
            color = if (active) AgenticCyan else AgenticTextSecondary,
            fontSize = 12.sp,
            lineHeight = 18.sp,
        )
    }
}

@Composable
private fun SuccessCard(title: String, body: String, color: Color) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(22.dp))
            .background(
                Brush.horizontalGradient(
                    colors = listOf(color.copy(alpha = 0.24f), AgenticSurface),
                ),
            )
            .padding(18.dp),
    ) {
        Text(title, color = color, fontSize = 18.sp, fontWeight = FontWeight.Medium)
        Spacer(modifier = Modifier.height(6.dp))
        Text(body, color = AgenticTextPrimary, fontSize = 13.sp, lineHeight = 19.sp)
    }
}

@Composable
private fun SectionMetricRow(items: List<Metric>) {
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
        items.forEach { item ->
            Column(
                modifier = Modifier
                    .weight(1f)
                    .clip(RoundedCornerShape(18.dp))
                    .background(AgenticSurface)
                    .padding(vertical = 14.dp, horizontal = 12.dp),
            ) {
                Text(item.value, color = AgenticTextPrimary, fontSize = 18.sp, fontWeight = FontWeight.Medium)
                Spacer(modifier = Modifier.height(3.dp))
                Text(item.label, color = AgenticTextTertiary, fontSize = 11.sp)
            }
        }
    }
}

@Composable
private fun MailRow(
    sender: String,
    subject: String,
    preview: String,
    time: String,
    tag: String,
    color: Color,
) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(20.dp))
            .background(AgenticSurface)
            .padding(16.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(
                modifier = Modifier
                    .size(38.dp)
                    .clip(CircleShape)
                    .background(color.copy(alpha = 0.18f)),
                contentAlignment = Alignment.Center,
            ) {
                Text(sender.take(1), color = color, fontSize = 15.sp, fontWeight = FontWeight.Medium)
            }
            Spacer(modifier = Modifier.width(12.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(sender, color = AgenticTextPrimary, fontSize = 15.sp, fontWeight = FontWeight.Medium)
                Text(subject, color = AgenticTextPrimary, fontSize = 13.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
            }
            Text(time, color = AgenticTextTertiary, fontSize = 12.sp)
        }
        Spacer(modifier = Modifier.height(10.dp))
        Text(preview, color = AgenticTextSecondary, fontSize = 13.sp, lineHeight = 19.sp)
        Spacer(modifier = Modifier.height(12.dp))
        CommandPill(text = tag, color = color)
    }
}

@Composable
private fun MailDraftCard(sent: Boolean) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(20.dp))
            .background(AgenticBlue.copy(alpha = 0.14f))
            .padding(16.dp),
    ) {
        Text(if (sent) "sent copy" else "draft preview", color = AgenticBlue, fontSize = 12.sp, fontWeight = FontWeight.Medium)
        Spacer(modifier = Modifier.height(8.dp))
        Text("Sounds good. I’ll bring the phone build and keep the walkthrough under two minutes.", color = AgenticTextPrimary, fontSize = 14.sp, lineHeight = 20.sp)
        Spacer(modifier = Modifier.height(10.dp))
        Text(if (sent) "Delivered just now." else "Say \"send it\" or \"make it shorter\".", color = AgenticTextSecondary, fontSize = 12.sp)
    }
}

@Composable
private fun TerminalCard(title: String, lines: List<String>) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(20.dp))
            .background(Color(0xFF090A10))
            .padding(16.dp),
    ) {
        Text(title, color = AgenticCyan, fontSize = 13.sp, fontWeight = FontWeight.Medium)
        Spacer(modifier = Modifier.height(10.dp))
        lines.forEach { line ->
            Text(line, color = AgenticTextPrimary, fontSize = 12.sp, lineHeight = 18.sp)
        }
    }
}

@Composable
private fun MessageThreadCard(name: String, message: String, reply: String, time: String, color: Color) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(20.dp))
            .background(AgenticSurface)
            .padding(16.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(
                modifier = Modifier
                    .size(38.dp)
                    .clip(CircleShape)
                    .background(color.copy(alpha = 0.18f)),
                contentAlignment = Alignment.Center,
            ) {
                Text(name.take(1), color = color, fontSize = 15.sp, fontWeight = FontWeight.Medium)
            }
            Spacer(modifier = Modifier.width(12.dp))
            Text(name, color = AgenticTextPrimary, fontSize = 15.sp, fontWeight = FontWeight.Medium, modifier = Modifier.weight(1f))
            Text(time, color = AgenticTextTertiary, fontSize = 12.sp)
        }
        Spacer(modifier = Modifier.height(12.dp))
        Bubble(text = message, alignEnd = false, color = AgenticSurface)
        Spacer(modifier = Modifier.height(8.dp))
        Bubble(text = reply, alignEnd = true, color = color.copy(alpha = 0.18f))
    }
}

@Composable
private fun Bubble(text: String, alignEnd: Boolean, color: Color) {
    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = if (alignEnd) Arrangement.End else Arrangement.Start) {
        Text(
            text = text,
            color = AgenticTextPrimary,
            fontSize = 13.sp,
            lineHeight = 18.sp,
            modifier = Modifier
                .fillMaxWidth(0.82f)
                .clip(RoundedCornerShape(17.dp))
                .background(if (alignEnd) color else AgenticBlack.copy(alpha = 0.55f))
                .padding(12.dp),
        )
    }
}

@Composable
private fun CommandRow(commands: List<String>) {
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
        commands.take(3).forEachIndexed { index, command ->
            CommandPill(
                text = command,
                color = listOf(AgenticBlue, AgenticCyan, AgenticViolet)[index],
                modifier = Modifier.weight(1f),
            )
        }
    }
}

@Composable
private fun CommandPill(text: String, color: Color, modifier: Modifier = Modifier) {
    Box(
        modifier = modifier
            .clip(RoundedCornerShape(999.dp))
            .background(color.copy(alpha = 0.16f))
            .padding(horizontal = 11.dp, vertical = 8.dp),
        contentAlignment = Alignment.Center,
    ) {
        Text(text, color = color, fontSize = 11.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
    }
}

@Composable
private fun OrbDock(orbState: OrbState, onOrbTap: () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(bottom = 48.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Bottom,
    ) {
        Orb(
            state = orbState,
            modifier = Modifier.clickable(
                interactionSource = remember { MutableInteractionSource() },
                indication = null,
                onClick = onOrbTap,
            ),
        )
        Spacer(modifier = Modifier.height(10.dp))
        Text(
            text = orbState.label(),
            color = AgenticTextSecondary,
            fontSize = 12.sp,
            fontWeight = FontWeight.Medium,
            letterSpacing = 1.4.sp,
        )
    }
}

private data class MockUiItem(
    val initial: String,
    val title: String,
    val subtitle: String,
    val body: String,
    val meta: String = "",
    val color: Color = AgenticBlue,
)

private data class Metric(val value: String, val label: String)

private fun sectionItems(destination: AppDestination): List<MockUiItem> = when (destination) {
    AppDestination.Home -> emptyList()
    AppDestination.Messages -> listOf(
        MockUiItem("M", "Maya", "Demo check-in", "Voice command: \"reply that the phone build is live\" drafts a response here, then waits for confirmation.", "now", AgenticCyan),
        MockUiItem("A", "Alex", "Qualcomm booth plan", "Voice command: \"summarize this thread\" turns the conversation into three bullets and a next step.", "8m", AgenticViolet),
    )
    AppDestination.Calendar -> listOf(
        MockUiItem("11", "Investor demo", "Today, 11:30 AM", "Voice command: \"move this to after lunch\" previews a reschedule card with attendees and conflicts.", "45m", AgenticGreen),
        MockUiItem("2", "Hardware sync", "Today, 2:00 PM", "Voice command: \"add the AI phone demo\" updates the agenda and marks it as the first topic.", "", AgenticBlue),
    )
    AppDestination.Navigate -> listOf(
        MockUiItem("S", "Snapdragon HQ", "Mock route: 18 min", "Voice command: \"navigate to the hackathon venue\" swaps this card into a route preview with ETA and parking notes.", "18m", AgenticCyan),
        MockUiItem("C", "Coffee nearby", "3 places found", "Voice command: \"find coffee on the way\" pins a stop and recalculates the demo arrival time.", "", AgenticGreen),
    )
    AppDestination.Search -> listOf(
        MockUiItem("Q", "Qualcomm AI Hub", "Research preview", "Voice command: \"search Qualcomm on-device AI\" builds a quick brief with links, highlights, and a takeaway.", "brief", AgenticBlue),
        MockUiItem("N", "NEXUS pitch notes", "Local result", "Voice command: \"turn this into talking points\" creates a concise demo script from the result.", "", AgenticViolet),
    )
    AppDestination.Tasks -> listOf(
        MockUiItem("1", "Run phone demo", "In progress", "Voice command: \"mark this done\" checks it off and moves the next task into focus.", "active", AgenticGreen),
        MockUiItem("2", "Polish voice UI", "Next", "Voice command: \"add galactic orb polish\" creates a subtask with the exact visual direction.", "", AgenticCyan),
    )
    AppDestination.Mail -> listOf(
        MockUiItem("S", "Sarah Chen", "Re: Q3 roadmap sync", "Sounds good. Let's lock in Thursday at 2pm. Voice command: \"draft a reply confirming\" opens an editable reply card.", "9:41", AgenticBlue),
        MockUiItem("D", "Demo Team", "Phone build checklist", "Latest build is ready for install. Voice command: \"summarize action items\" highlights the blockers and owners.", "9:12", AgenticViolet),
    )
    AppDestination.Code -> emptyList()
}

private fun OrbState.label(): String = when (this) {
    OrbState.Idle -> "LISTENING FOR YOU"
    OrbState.Listening -> "LISTENING"
    OrbState.Thinking -> "THINKING"
    OrbState.Working -> "WORKING"
    OrbState.Done -> "DONE"
}
