package com.soma2026.tikitalka.data.remote.dto

import com.soma2026.tikitalka.domain.model.League
import com.soma2026.tikitalka.domain.model.LeagueStandings
import com.soma2026.tikitalka.domain.model.TeamStanding
import kotlinx.serialization.Serializable

@Serializable
data class StandingsResponseDto(
    val season: SeasonDto,
    val standings: List<StandingGroupDto>,
)

@Serializable
data class SeasonDto(
    val startDate: String,
    val currentMatchday: Int? = null,
)

@Serializable
data class StandingGroupDto(
    val type: String,
    val table: List<TableEntryDto>,
)

@Serializable
data class TableEntryDto(
    val position: Int,
    val team: TeamDto,
    val playedGames: Int,
    val won: Int,
    val draw: Int,
    val lost: Int,
    val points: Int,
    val goalDifference: Int,
)

@Serializable
data class TeamDto(
    val name: String,
    val tla: String,
    val crest: String = "",
)

fun StandingsResponseDto.toDomain(league: League): LeagueStandings {
    val table = standings.firstOrNull { it.type == "TOTAL" }?.table ?: emptyList()
    val startYear = season.startDate.take(4)
    val endYear = (startYear.toIntOrNull()?.plus(1))?.toString()?.takeLast(2) ?: "?"
    return LeagueStandings(
        league = league,
        season = "$startYear/$endYear 시즌",
        currentMatchday = season.currentMatchday ?: 0,
        table = table.map { it.toDomain() },
    )
}

private fun TableEntryDto.toDomain() = TeamStanding(
    position = position,
    teamName = team.name.toKoreanTeamName(),
    tla = team.tla,
    crestUrl = team.crest,
    playedGames = playedGames,
    won = won,
    drawn = draw,
    lost = lost,
    points = points,
    goalDifference = goalDifference,
)