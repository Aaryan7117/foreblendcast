package com.foreblendcast.app.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp

val Forest = Color(0xFF0E3825)
val Leaf = Color(0xFF174A35)
val LeafPale = Color(0xFFE6F2EB)
val Mist = Color(0xFFF4F6F3)
val Ink = Color(0xFF1B1F1D)
val InkMuted = Color(0xFF536273)
val Rain = Color(0xFF1D4ED8)

val TierRed = Color(0xFFDC2626)
val TierOrange = Color(0xFFEA580C)
val TierYellow = Color(0xFFF59E0B)
val TierGreen = Color(0xFF16A34A)

private val LightScheme = lightColorScheme(
    primary = Forest,
    onPrimary = Color.White,
    primaryContainer = LeafPale,
    onPrimaryContainer = Forest,
    secondary = Leaf,
    onSecondary = Color.White,
    secondaryContainer = Color(0xFFDCE9E1),
    onSecondaryContainer = Forest,
    tertiary = Rain,
    background = Mist,
    onBackground = Ink,
    surface = Color.White,
    onSurface = Ink,
    surfaceVariant = Color(0xFFEDF1EE),
    onSurfaceVariant = InkMuted,
    outline = Color(0xFFCBD5D0),
    error = TierRed,
)

private val DarkScheme = darkColorScheme(
    primary = Color(0xFF8FD3AE),
    onPrimary = Forest,
    primaryContainer = Leaf,
    onPrimaryContainer = Color(0xFFDFF3E7),
    secondary = Color(0xFFA7D7BE),
    background = Color(0xFF0F1512),
    onBackground = Color(0xFFE6ECE8),
    surface = Color(0xFF161D19),
    onSurface = Color(0xFFE6ECE8),
    surfaceVariant = Color(0xFF222B26),
    onSurfaceVariant = Color(0xFFB4C0B9),
    outline = Color(0xFF3B463F),
    error = Color(0xFFFF8A80),
)

val AppTypography = Typography(
    headlineSmall = TextStyle(fontWeight = FontWeight.Bold, fontSize = 22.sp, lineHeight = 28.sp),
    titleLarge = TextStyle(fontWeight = FontWeight.Bold, fontSize = 20.sp, lineHeight = 26.sp),
    titleMedium = TextStyle(fontWeight = FontWeight.SemiBold, fontSize = 16.sp, lineHeight = 22.sp),
    titleSmall = TextStyle(fontWeight = FontWeight.SemiBold, fontSize = 14.sp, lineHeight = 20.sp),
    bodyLarge = TextStyle(fontSize = 16.sp, lineHeight = 24.sp),
    bodyMedium = TextStyle(fontSize = 14.sp, lineHeight = 20.sp),
    bodySmall = TextStyle(fontSize = 12.sp, lineHeight = 16.sp),
    labelLarge = TextStyle(fontWeight = FontWeight.SemiBold, fontSize = 14.sp),
    labelMedium = TextStyle(fontWeight = FontWeight.SemiBold, fontSize = 12.sp, letterSpacing = 0.3.sp),
    labelSmall = TextStyle(fontWeight = FontWeight.SemiBold, fontSize = 10.5.sp, letterSpacing = 0.5.sp),
)

@Composable
fun ForeBlendCastTheme(darkTheme: Boolean = isSystemInDarkTheme(), content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = if (darkTheme) DarkScheme else LightScheme,
        typography = AppTypography,
        content = content,
    )
}
