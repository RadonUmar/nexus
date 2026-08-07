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
import androidx.compose.ui.draw.BlurredEdgeTreatment
import androidx.compose.ui.draw.blur
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.BlendMode
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.CompositingStrategy
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.unit.dp
import com.agenticos.app.ui.theme.AgenticBlue
import com.agenticos.app.ui.theme.AgenticCyan
import com.agenticos.app.ui.theme.AgenticGreen
import com.agenticos.app.ui.theme.AgenticViolet
import kotlin.math.cos
import kotlin.math.sin

/**
 * Siri-style orb: a few softly blurred color blobs drifting and breathing inside
 * a circular mask, blended additively so they melt into each other like a lava lamp,
 * topped with a faint glassy sheen. No hard edges, rings, or particles — the blur
 * uses BlurredEdgeTreatment.Unbounded so the glow fades to true transparency instead
 * of cutting off at a visible square, which is what made the previous version look
 * like a mismatched box against the background.
 *
 * Swap for a Lottie composition later without touching call sites (see README).
 */
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
        targetValue = if (state == OrbState.Done) AgenticGreen else AgenticBlue,
        animationSpec = tween(450),
        label = "orb-primary",
    )
    val secondary = if (state == OrbState.Done) AgenticGreen else AgenticViolet
    val tertiary = if (state == OrbState.Done) AgenticGreen else AgenticCyan

    val size = 132.dp

    Box(modifier = modifier.size(size)) {
        // Blob layer — blurred, unbounded edge treatment so it fades to nothing
        // rather than clipping to a visible rectangle.
        Canvas(
            modifier = Modifier
                .size(size)
                .graphicsLayer { compositingStrategy = CompositingStrategy.Offscreen }
                .blur(radius = 16.dp, edgeTreatment = BlurredEdgeTreatment.Unbounded),
        ) {
            val r = this.size.minDimension / 2f * breathe

            fun blobCenter(angleDeg: Float, orbitRadius: Float): Offset {
                val rad = Math.toRadians(angleDeg.toDouble())
                return center + Offset((cos(rad) * orbitRadius).toFloat(), (sin(rad) * orbitRadius).toFloat())
            }

            // Circular mask so blobs never spill into a square silhouette.
            drawCircle(color = Color.Black, radius = r, center = center, blendMode = BlendMode.Clear)

            drawCircle(
                brush = Brush.radialGradient(
                    colors = listOf(primary.copy(alpha = 0.95f), Color.Transparent),
                    center = blobCenter(drift, r * 0.32f),
                    radius = r * 0.95f,
                ),
                radius = r * 0.95f,
                center = blobCenter(drift, r * 0.32f),
                blendMode = BlendMode.Plus,
            )
            drawCircle(
                brush = Brush.radialGradient(
                    colors = listOf(secondary.copy(alpha = 0.8f), Color.Transparent),
                    center = blobCenter(drift * 1.4f + 140f, r * 0.34f),
                    radius = r * 0.85f,
                ),
                radius = r * 0.85f,
                center = blobCenter(drift * 1.4f + 140f, r * 0.34f),
                blendMode = BlendMode.Plus,
            )
            drawCircle(
                brush = Brush.radialGradient(
                    colors = listOf(tertiary.copy(alpha = 0.7f), Color.Transparent),
                    center = blobCenter(-drift * 0.8f + 260f, r * 0.3f),
                    radius = r * 0.75f,
                ),
                radius = r * 0.75f,
                center = blobCenter(-drift * 0.8f + 260f, r * 0.3f),
                blendMode = BlendMode.Plus,
            )
        }

        // Sheen layer — soft glassy highlight + a whisper-thin rim, unblurred and sharp.
        Canvas(modifier = Modifier.size(size)) {
            val r = this.size.minDimension / 2f * breathe
            val highlightOffset = Offset(r * 0.28f, r * 0.34f)

            drawCircle(
                brush = Brush.radialGradient(
                    colors = listOf(Color.White.copy(alpha = 0.32f), Color.Transparent),
                    center = center - highlightOffset,
                    radius = r * 0.5f,
                ),
                radius = r * 0.5f,
                center = center - highlightOffset,
            )
            drawCircle(
                color = Color.White.copy(alpha = 0.14f),
                radius = r,
                center = center,
                style = Stroke(width = 1.dp.toPx()),
            )
        }
    }
}
