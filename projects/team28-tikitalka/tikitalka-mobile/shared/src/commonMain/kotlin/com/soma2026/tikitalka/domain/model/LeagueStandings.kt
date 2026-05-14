package com.soma2026.tikitalka.domain.model

data class LeagueStandings(
    val league: League,
    val season: String,
    val currentMatchday: Int,
    val table: List<TeamStanding>,
)