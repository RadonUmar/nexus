package com.agenticos.app.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp

val AgenticBlack = Color(0xFF000000)
val AgenticVoid = Color(0xFF050507)
val AgenticSurface = Color(0xFF131316)
val AgenticSurfaceRaised = Color(0xFF1B1B20)
val AgenticStroke = Color(0xFF26262C)

val AgenticBlue = Color(0xFF3E8CFF)
val AgenticBlueDeep = Color(0xFF2E5BFF)
val AgenticViolet = Color(0xFF8B5CF6)
val AgenticCyan = Color(0xFF5EEAD4)
val AgenticGreen = Color(0xFF34D399)

val AgenticTextPrimary = Color(0xFFF5F5F7)
val AgenticTextSecondary = Color(0xFF8E8E96)
val AgenticTextTertiary = Color(0xFF54545C)

private val AgenticColorScheme = darkColorScheme(
    background = AgenticBlack,
    surface = AgenticSurface,
    primary = AgenticBlue,
    secondary = AgenticGreen,
    tertiary = AgenticViolet,
    onBackground = AgenticTextPrimary,
    onSurface = AgenticTextPrimary,
)

private val AgenticTypography = Typography(
    displayLarge = TextStyle(fontWeight = FontWeight.Light, fontSize = 34.sp, letterSpacing = (-0.5).sp),
    titleMedium = TextStyle(fontWeight = FontWeight.Medium, fontSize = 15.sp, letterSpacing = 0.2.sp),
    bodyMedium = TextStyle(fontWeight = FontWeight.Normal, fontSize = 14.sp),
    labelSmall = TextStyle(fontWeight = FontWeight.Medium, fontSize = 11.sp, letterSpacing = 1.2.sp),
)

@Composable
fun AgenticOSTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = AgenticColorScheme,
        typography = AgenticTypography,
        content = content,
    )
}

