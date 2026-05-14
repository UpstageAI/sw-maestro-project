package com.soma2026.tikitalka.data.remote.api

import com.soma2026.tikitalka.data.remote.dto.StandingsResponseDto
import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.get

class StandingApi(private val client: HttpClient) {
    suspend fun getStandings(leagueCode: String): StandingsResponseDto =
        client.get("competitions/$leagueCode/standings").body()
}