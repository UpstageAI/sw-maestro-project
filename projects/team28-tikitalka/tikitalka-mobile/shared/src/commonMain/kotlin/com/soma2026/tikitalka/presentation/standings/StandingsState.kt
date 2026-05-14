package com.soma2026.tikitalka.presentation.standings

import com.soma2026.tikitalka.domain.model.League
import com.soma2026.tikitalka.domain.model.LeagueStandings

data class StandingsState(
    val selectedLeague: League = League.PREMIER_LEAGUE,
    val standings: Map<League, LeagueStandings> = emptyMap(),
    val isLoading: Boolean = false,
    val errorMessage: String? = null,
) {
    val currentStandings: LeagueStandings? get() = standings[selectedLeague]
}
