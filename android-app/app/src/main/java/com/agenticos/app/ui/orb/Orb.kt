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
import androidx.compose.ui.graphics.PointMode
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.rotate
import androidx.compose.ui.unit.dp
import com.agenticos.app.ui.theme.AgenticBlue
import com.agenticos.app.ui.theme.AgenticGreen
import com.agenticos.app.ui.theme.AgenticViolet
import kotlin.math.cos
import kotlin.math.sin

/**
 * Layered plasma-style orb rendered on a Compose Canvas: a slow outer rotation of
 * violet/cyan swirl arcs, a pulsing blue/violet radial core, and a faint particle ring.
 * State drives pulse speed, rotation speed, and a color blend toward green on Done.
 *
 * Swap for a Lottie composition later without touching call sites (see README).
 */
@Composable
fun Orb(state: OrbState, modifier: Modifier = Modifier) {
    val transition = rememberInfiniteTransition(label = "orb")

    val pulseMs = when (state) {
        OrbState.Idle -> 3400
        OrbState.Listening -> 1100
        OrbState.Thinking -> 700
        OrbState.Working -> 850
        OrbState.Done -> 1600
    }
    val rotateMs = when (state) {
        OrbState.Idle -> 14000
        OrbState.Listening -> 6000
        OrbState.Thinking -> 2600
        OrbState.Working -> 3200
        OrbState.Done -> 9000
    }

    val pulse by transition.animateFloat(
        initialValue = 0.82f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = pulseMs, easing = LinearEasing),
            repeatMode = RepeatMode.Reverse,
        ),
        label = "orb-pulse",
    )
    val rotation by transition.animateFloat(
        initialValue = 0f,
        targetValue = 360f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = rotateMs, easing = LinearEasing),
        ),
        label = "orb-rotation",
    )

    val coreColor by animateColorAsState(
        targetValue = if (state == OrbState.Done) AgenticGreen else AgenticBlue,
        animationSpec = tween(400),
        label = "orb-core-color",
    )
    val accentColor = if (state == OrbState.Done) AgenticGreen else AgenticViolet

    Box(modifier = modifier.size(160.dp)) {
        Canvas(modifier = Modifier.size(160.dp)) {
            val outerRadius = size.minDimension / 2f * pulse

            // Outer glow halo
            drawCircle(
                brush = Brush.radialGradient(
                    colors = listOf(
                        coreColor.copy(alpha = 0.35f),
                        accentColor.copy(alpha = 0.12f),
                        Color.Transparent,
                    ),
                    center = center,
                    radius = outerRadius * 2f,
                ),
                radius = outerRadius * 2f,
                center = center,
            )

            // Rotating swirl arcs (plasma feel)
            rotate(degrees = rotation, pivot = center) {
                for (i in 0 until 3) {
                    val angleOffset = i * 120f
                    val armRadius = outerRadius * (0.55f + i * 0.12f)
                    val points = mutableListOf<Offset>()
                    for (deg in 0..180 step 6) {
                        val rad = Math.toRadians((deg + angleOffset).toDouble())
                        points.add(
                            center + Offset(
                                (cos(rad) * armRadius).toFloat(),
                                (sin(rad) * armRadius * 0.6f).toFloat(),
                            ),
                        )
                    }
                    drawPoints(
                        points = points,
                        pointMode = PointMode.Polygon,
                        color = accentColor.copy(alpha = 0.28f - i * 0.06f),
                        strokeWidth = 2.5f,
                    )
                }
            }

            // Core sphere with layered gradient for depth
            drawCircle(
                brush = Brush.radialGradient(
                    colors = listOf(
                        Color.White.copy(alpha = 0.9f),
                        coreColor.copy(alpha = 0.95f),
                        coreColor.copy(alpha = 0.55f),
                        accentColor.copy(alpha = 0.25f),
                        Color.Transparent,
                    ),
                    center = center - Offset(outerRadius * 0.15f, outerRadius * 0.15f),
                    radius = outerRadius * 1.05f,
                ),
                radius = outerRadius * 0.62f,
                center = center,
            )

            // Thin bright rim
            drawCircle(
                color = coreColor.copy(alpha = 0.5f),
                radius = outerRadius * 0.62f,
                center = center,
                style = Stroke(width = 1.5f),
            )
        }
    }
}
