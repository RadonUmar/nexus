package com.agenticos.app.ui.orb

import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.size
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.unit.dp
import com.agenticos.app.ui.theme.AgenticBlue
import com.agenticos.app.ui.theme.AgenticCyan
import com.agenticos.app.ui.theme.AgenticGreen
import com.agenticos.app.ui.theme.AgenticViolet
import kotlin.math.cos
import kotlin.math.sin

@Composable
fun Orb(state: OrbState, modifier: Modifier = Modifier) {
    val transition = rememberInfiniteTransition(label = "orb")

    val speedMs = when (state) {
        OrbState.Idle -> 5200
        OrbState.Listening -> 2600
        OrbState.Thinking -> 1300
        OrbState.Working -> 1600
        OrbState.Done -> 3600
    }
    val pulseMs = when (state) {
        OrbState.Idle -> 2600
        OrbState.Listening -> 1400
        OrbState.Thinking -> 800
        OrbState.Working -> 950
        OrbState.Done -> 1800
    }

    val drift by transition.animateFloat(
        initialValue = 0f,
        targetValue = 360f,
        animationSpec = infiniteRepeatable(animation = tween(durationMillis = speedMs, easing = LinearEasing)),
        label = "orb-drift",
    )
    val breathe by transition.animateFloat(
        initialValue = 0.9f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = pulseMs, easing = LinearEasing),
            repeatMode = RepeatMode.Reverse,
        ),
        label = "orb-breathe",
    )

    val primary by animateColorAsState(
        targetValue = when (state) {
            OrbState.Done -> AgenticGreen
            OrbState.Thinking -> AgenticViolet
            OrbState.Working -> AgenticCyan
            else -> AgenticBlue
        },
        animationSpec = tween(450),
        label = "orb-primary",
    )
    val secondary = if (state == OrbState.Done) AgenticGreen else AgenticViolet
    val tertiary = if (state == OrbState.Done) AgenticGreen else AgenticCyan

    val size = 132.dp

    Box(modifier = modifier.size(size)) {
        Canvas(modifier = Modifier.size(size)) {
            val r = this.size.minDimension / 2f * breathe

            fun blobCenter(angleDeg: Float, orbitRadius: Float): Offset {
                val rad = Math.toRadians(angleDeg.toDouble())
                return center + Offset((cos(rad) * orbitRadius).toFloat(), (sin(rad) * orbitRadius).toFloat())
            }

            drawCircle(
                brush = Brush.radialGradient(
                    colors = listOf(
                        primary.copy(alpha = 0.22f),
                        Color.Transparent,
                    ),
                    center = center,
                    radius = r * 1.22f,
                ),
                radius = r * 1.22f,
                center = center,
            )
            drawCircle(
                brush = Brush.radialGradient(
                    colors = listOf(Color(0xFF03030E), Color(0xFF090622), Color(0xFF160B36)),
                    center = center,
                    radius = r * 0.98f,
                ),
                radius = r * 0.98f,
                center = center,
            )
            drawCircle(
                brush = Brush.radialGradient(
                    colors = listOf(primary.copy(alpha = 0.9f), primary.copy(alpha = 0.22f), Color.Transparent),
                    center = blobCenter(drift, r * 0.32f),
                    radius = r * 0.74f,
                ),
                radius = r * 0.74f,
                center = blobCenter(drift, r * 0.32f),
            )
            drawCircle(
                brush = Brush.radialGradient(
                    colors = listOf(secondary.copy(alpha = 0.78f), secondary.copy(alpha = 0.2f), Color.Transparent),
                    center = blobCenter(drift * 1.4f + 140f, r * 0.34f),
                    radius = r * 0.66f,
                ),
                radius = r * 0.66f,
                center = blobCenter(drift * 1.4f + 140f, r * 0.34f),
            )
            drawCircle(
                brush = Brush.radialGradient(
                    colors = listOf(tertiary.copy(alpha = 0.72f), tertiary.copy(alpha = 0.18f), Color.Transparent),
                    center = blobCenter(-drift * 0.8f + 260f, r * 0.3f),
                    radius = r * 0.6f,
                ),
                radius = r * 0.6f,
                center = blobCenter(-drift * 0.8f + 260f, r * 0.3f),
            )
            drawCircle(
                brush = Brush.radialGradient(
                    colors = listOf(Color.White.copy(alpha = 0.32f), Color.Transparent),
                    center = blobCenter(drift * 1.8f + 40f, r * 0.48f),
                    radius = r * 0.24f,
                ),
                radius = r * 0.24f,
                center = blobCenter(drift * 1.8f + 40f, r * 0.48f),
            )
            drawCircle(
                brush = Brush.radialGradient(
                    colors = listOf(Color.Transparent, Color(0xFF02030A).copy(alpha = 0.46f)),
                    center = center,
                    radius = r,
                ),
                radius = r,
                center = center,
            )
            val highlightOffset = Offset(r * 0.28f, r * 0.34f)
            drawCircle(
                brush = Brush.radialGradient(
                    colors = listOf(Color.White.copy(alpha = 0.28f), Color.Transparent),
                    center = center - highlightOffset,
                    radius = r * 0.42f,
                ),
                radius = r * 0.42f,
                center = center - highlightOffset,
            )
            val stars = listOf(
                Offset(center.x - r * 0.28f, center.y - r * 0.1f),
                Offset(center.x + r * 0.22f, center.y - r * 0.34f),
                Offset(center.x + r * 0.32f, center.y + r * 0.18f),
            )
            stars.forEachIndexed { index, star ->
                drawCircle(
                    color = Color.White.copy(alpha = 0.72f - index * 0.16f),
                    radius = (1.2f + index * 0.35f).dp.toPx(),
                    center = star,
                )
            }
            drawCircle(
                color = Color.White.copy(alpha = 0.18f),
                radius = r,
                center = center,
                style = Stroke(width = 1.dp.toPx()),
            )
            drawCircle(
                color = primary.copy(alpha = 0.22f),
                radius = r * 0.86f,
                center = center,
                style = Stroke(width = 2.dp.toPx()),
            )
            drawCircle(
                color = Color.White.copy(alpha = 0.08f),
                radius = r * 0.58f,
                center = center,
                style = Stroke(width = 1.dp.toPx()),
            )
        }
    }
}
