package com.soma2026.tikitalka.navigation

sealed class Screen(val route: String) {
    data object Dashboard : Screen("dashboard")
    data object Chat : Screen("chat")
    data object Standings : Screen("standings")
}
