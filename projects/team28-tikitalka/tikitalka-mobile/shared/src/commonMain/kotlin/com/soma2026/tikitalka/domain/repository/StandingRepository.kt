package com.soma2026.tikitalka.domain.repository

import com.soma2026.tikitalka.domain.model.League
import com.soma2026.tikitalka.domain.model.LeagueStandings

interface StandingRepository {
    suspend fun getStandings(league: League): Result<LeagueStandings>
}