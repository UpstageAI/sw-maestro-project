package com.soma2026.tikitalka.data.repository

import com.soma2026.tikitalka.data.remote.api.StandingApi
import com.soma2026.tikitalka.data.remote.dto.toDomain
import com.soma2026.tikitalka.domain.model.League
import com.soma2026.tikitalka.domain.model.LeagueStandings
import com.soma2026.tikitalka.domain.repository.StandingRepository

class StandingRepositoryImpl(private val api: StandingApi) : StandingRepository {
    override suspend fun getStandings(league: League): Result<LeagueStandings> =
        runCatching { api.getStandings(league.code).toDomain(league) }
}