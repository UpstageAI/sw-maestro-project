package com.soma2026.tikitalka.domain.usecase

import com.soma2026.tikitalka.domain.model.League
import com.soma2026.tikitalka.domain.model.LeagueStandings
import com.soma2026.tikitalka.domain.repository.StandingRepository

class GetStandingsUseCase(private val repository: StandingRepository) {
    suspend operator fun invoke(league: League): Result<LeagueStandings> =
        repository.getStandings(league)
}