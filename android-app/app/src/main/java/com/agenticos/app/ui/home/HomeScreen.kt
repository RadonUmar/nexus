package com.agenticos.app.ui.home

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.slideInVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.CalendarMonth
import androidx.compose.material.icons.outlined.CheckCircleOutline
import androidx.compose.material.icons.outlined.MailOutline
import androidx.compose.material.icons.outlined.Message
import androidx.compose.material.icons.outlined.Navigation
import androidx.compose.material.icons.outlined.Search
import androidx.compose.material3.Icon
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
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.agenticos.app.ui.orb.Orb
import com.agenticos.app.ui.orb.OrbState
import com.agenticos.app.ui.theme.AgenticBlack
import com.agenticos.app.ui.theme.AgenticBlue
import com.agenticos.app.ui.theme.AgenticStroke
import com.agenticos.app.ui.theme.AgenticSurface
import com.agenticos.app.ui.theme.AgenticTextPrimary
import com.agenticos.app.ui.theme.AgenticTextSecondary
import com.agenticos.app.ui.theme.AgenticTextTertiary
import com.agenticos.app.ui.theme.AgenticVoid

private data class CoreFunction(val label: String, val icon: ImageVector)

private val CORE_FUNCTIONS = listOf(
    CoreFunction("Messages", Icons.Outlined.Message),
    CoreFunction("Calendar", Icons.Outlined.CalendarMonth),
    CoreFunction("Navigate", Icons.Outlined.Navigation),
    CoreFunction("Search", Icons.Outlined.Search),
    CoreFunction("Tasks", Icons.Outlined.CheckCircleOutline),
    CoreFunction("Mail", Icons.Outlined.MailOutline),
)

@Composable
fun HomeScreen(orbState: OrbState) {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(
                Brush.verticalGradient(
                    colors = listOf(AgenticVoid, AgenticBlack, AgenticBlack),
                ),
            ),
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
                    FunctionRow(function = function)
                }
            }
        }

        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(bottom = 48.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Bottom,
        ) {
            Orb(state = orbState)
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
                text = "Agentic OS",
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
private fun FunctionRow(function: CoreFunction) {
    val interactionSource = remember { MutableInteractionSource() }
    val isPressed by interactionSource.collectIsPressedAsState()

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(18.dp))
            .background(if (isPressed) AgenticSurface else Color.Transparent)
            .clickable(interactionSource = interactionSource, indication = null) {}
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
                imageVector = function.icon,
                contentDescription = function.label,
                tint = AgenticTextSecondary,
                modifier = Modifier.size(18.dp),
            )
        }

        Spacer(modifier = Modifier.width(16.dp))

        Text(
            text = function.label,
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

private fun OrbState.label(): String = when (this) {
    OrbState.Idle -> "LISTENING FOR YOU"
    OrbState.Listening -> "LISTENING"
    OrbState.Thinking -> "THINKING"
    OrbState.Working -> "WORKING"
    OrbState.Done -> "DONE"
}
