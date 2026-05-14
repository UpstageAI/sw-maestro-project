package com.soma2026.tikitalka.presentation.standings

sealed class StandingsEffect {
    data class ShowError(val message: String) : StandingsEffect()
}