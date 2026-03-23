package com.agentbus.mobile.ui.theme

import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable

private val DarkColors = darkColorScheme(
    primary = Cyan400,
    secondary = Amber300,
    tertiary = Mint400,
    background = Indigo900,
    surface = Indigo700,
    onPrimary = Indigo900,
    onSecondary = Indigo900,
    onTertiary = Indigo900,
)

private val LightColors = lightColorScheme(
    primary = Indigo700,
    secondary = Amber300,
    tertiary = Rose300,
)

@Composable
fun AgentBusTheme(
    useDarkTheme: Boolean = true,
    content: @Composable () -> Unit,
) {
    MaterialTheme(
        colorScheme = if (useDarkTheme) DarkColors else LightColors,
        typography = AgentBusTypography,
        content = content,
    )
}
