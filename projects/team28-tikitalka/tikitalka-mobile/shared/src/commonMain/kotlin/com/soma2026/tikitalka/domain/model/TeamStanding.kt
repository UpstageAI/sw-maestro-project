package com.soma2026.tikitalka.domain.model

data class TeamStanding(
    val position: Int,
    val teamName: String,
    val tla: String,
    val crestUrl: String,
    val playedGames: Int,
    val won: Int,
    val drawn: Int,
    val lost: Int,
    val points: Int,
    val goalDifference: Int,
)