package com.soma2026.tikitalka.presentation.standings

import com.soma2026.tikitalka.domain.model.League

sealed class StandingsIntent {
    data class SelectLeague(val league: League) : StandingsIntent()
}