package com.soma2026.tikitalka.ui.standings

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.material3.Icon
import androidx.compose.foundation.layout.Spacer
import coil3.compose.SubcomposeAsyncImage
import org.jetbrains.compose.resources.painterResource
import tikitalka.composeapp.generated.resources.Res
import tikitalka.composeapp.generated.resources.ico_league_bl1
import tikitalka.composeapp.generated.resources.ico_league_fl1
import tikitalka.composeapp.generated.resources.ico_league_pd
import tikitalka.composeapp.generated.resources.ico_league_pl
import tikitalka.composeapp.generated.resources.ico_league_sa
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Snackbar
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.soma2026.tikitalka.domain.model.League
import com.soma2026.tikitalka.domain.model.LeagueStandings
import com.soma2026.tikitalka.domain.model.TeamStanding
import com.soma2026.tikitalka.presentation.standings.StandingsEffect
import com.soma2026.tikitalka.presentation.standings.StandingsIntent
import com.soma2026.tikitalka.presentation.standings.StandingsState
import com.soma2026.tikitalka.presentation.standings.StandingsViewModel
import org.koin.compose.viewmodel.koinViewModel

@Composable
fun StandingsScreen(viewModel: StandingsViewModel = koinViewModel()) {
    val state by viewModel.state.collectAsState()
    val snackbarHostState = remember { SnackbarHostState() }

    LaunchedEffect(Unit) {
        viewModel.effect.collect { effect ->
            when (effect) {
                is StandingsEffect.ShowError -> snackbarHostState.showSnackbar(effect.message)
            }
        }
    }

    StandingsContent(
        state = state,
        snackbarHostState = snackbarHostState,
        onSelectLeague = { viewModel.handleIntent(StandingsIntent.SelectLeague(it)) },
    )
}

@Composable
internal fun StandingsContent(
    state: StandingsState,
    snackbarHostState: SnackbarHostState = remember { SnackbarHostState() },
    onSelectLeague: (League) -> Unit = {},
) {
    Scaffold(
        snackbarHost = { SnackbarHost(snackbarHostState) { Snackbar(it) } },
        containerColor = MaterialTheme.colorScheme.background,
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding),
        ) {
            // 헤더
            Column(modifier = Modifier.padding(horizontal = 20.dp, vertical = 16.dp)) {
                val standings = state.currentStandings
                Text(
                    text = if (standings != null) "${standings.season} · ${standings.currentMatchday}R 기준" else "",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                Spacer(modifier = Modifier.height(2.dp))
                Text(
                    text = "리그 순위",
                    style = MaterialTheme.typography.headlineMedium,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onSurface,
                )
            }

            // 리그 탭
            Row(
                modifier = Modifier
                    .horizontalScroll(rememberScrollState())
                    .padding(horizontal = 16.dp),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                League.entries.forEach { league ->
                    LeagueChip(
                        label = league.displayName,
                        league = league,
                        selected = league == state.selectedLeague,
                        onClick = { onSelectLeague(league) },
                    )
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            // 순위 테이블
            Surface(
                modifier = Modifier
                    .weight(1f)
                    .padding(horizontal = 16.dp),
                shape = RoundedCornerShape(12.dp),
                color = MaterialTheme.colorScheme.surface,
            ) {
                when {
                    state.isLoading -> {
                        Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                            CircularProgressIndicator()
                        }
                    }
                    state.errorMessage != null && state.currentStandings == null -> {
                        Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                            Text(
                                text = "순위를 불러오지 못했습니다",
                                style = MaterialTheme.typography.bodyMedium,
                                color = MaterialTheme.colorScheme.error,
                            )
                        }
                    }
                    state.currentStandings != null -> {
                        StandingsTable(standings = state.currentStandings!!)
                    }
                }
            }

            // 범례
            StandingsLegend(
                leagueCode = state.selectedLeague.code,
                modifier = Modifier.padding(horizontal = 20.dp, vertical = 12.dp),
            )
        }
    }
}

@Composable
private fun LeagueChip(label: String, league: League, selected: Boolean, onClick: () -> Unit) {
    val iconRes = when (league) {
        League.PREMIER_LEAGUE -> Res.drawable.ico_league_pl
        League.LA_LIGA -> Res.drawable.ico_league_pd
        League.BUNDESLIGA -> Res.drawable.ico_league_bl1
        League.SERIE_A -> Res.drawable.ico_league_sa
        League.LIGUE_1 -> Res.drawable.ico_league_fl1
    }
    Row(
        modifier = Modifier
            .clip(RoundedCornerShape(20.dp))
            .background(
                if (selected) MaterialTheme.colorScheme.onSurface
                else MaterialTheme.colorScheme.surfaceVariant,
            )
            .clickable(
                indication = null,
                interactionSource = remember { MutableInteractionSource() },
                onClick = onClick,
            )
            .padding(horizontal = 12.dp, vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        Icon(
            painter = painterResource(iconRes),
            contentDescription = null,
            modifier = Modifier.size(16.dp),
            tint = Color.Unspecified,
        )
        Text(
            text = label,
            style = MaterialTheme.typography.labelMedium,
            color = if (selected) MaterialTheme.colorScheme.surface else MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

@Composable
private fun StandingsTable(standings: LeagueStandings) {
    Column {
        // 헤더 행
        TableHeaderRow()
        HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)

        LazyColumn {
            items(standings.table, key = { it.position }) { team ->
                TeamRow(team = team, leagueCode = standings.league.code)
                HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)
            }
        }
    }
}

@Composable
private fun TableHeaderRow() {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Spacer(modifier = Modifier.width(3.dp)) // 인디케이터 공간
        Spacer(modifier = Modifier.width(8.dp))
        Text(
            text = "#",
            modifier = Modifier.width(24.dp),
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            textAlign = TextAlign.Center,
        )
        Spacer(modifier = Modifier.width(8.dp))
        Spacer(modifier = Modifier.width(28.dp)) // 로고 자리
        Spacer(modifier = Modifier.width(8.dp))
        Text(
            text = "팀",
            modifier = Modifier.weight(1f),
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        listOf("P", "W", "D", "L", "GD", "PTS").forEach { header ->
            Text(
                text = header,
                modifier = Modifier.width(if (header == "PTS" || header == "GD") 40.dp else 28.dp),
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                textAlign = TextAlign.Center,
                fontWeight = if (header == "PTS") FontWeight.Bold else FontWeight.Normal,
            )
        }
    }
}

@Composable
private fun TeamRow(team: TeamStanding, leagueCode: String) {
    val zoneColor = positionZoneColor(team.position, leagueCode)

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        // 포지션 인디케이터 바
        Box(
            modifier = Modifier
                .width(3.dp)
                .height(28.dp)
                .background(
                    color = zoneColor,
                    shape = RoundedCornerShape(topEnd = 2.dp, bottomEnd = 2.dp),
                ),
        )
        Spacer(modifier = Modifier.width(8.dp))

        // 순위
        Text(
            text = "${team.position}",
            modifier = Modifier.width(24.dp),
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            textAlign = TextAlign.Center,
        )
        Spacer(modifier = Modifier.width(8.dp))

        // 팀 로고
        SubcomposeAsyncImage(
            model = team.crestUrl,
            contentDescription = team.teamName,
            modifier = Modifier.size(28.dp),
            error = {
                Box(
                    modifier = Modifier
                        .size(28.dp)
                        .clip(RoundedCornerShape(6.dp))
                        .background(MaterialTheme.colorScheme.surfaceVariant),
                    contentAlignment = Alignment.Center,
                ) {
                    Text(
                        text = team.tla,
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        fontWeight = FontWeight.Medium,
                    )
                }
            },
        )
        Spacer(modifier = Modifier.width(8.dp))

        // 팀 이름
        Text(
            text = team.teamName,
            modifier = Modifier
                .weight(1f)
                .padding(end = 4.dp),
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurface,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )

        // P, W, D, L
        listOf(team.playedGames, team.won, team.drawn, team.lost).forEach { value ->
            Text(
                text = "$value",
                modifier = Modifier.width(28.dp),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                textAlign = TextAlign.Center,
            )
        }

        // GD (양수=초록, 음수=빨강)
        val gdText = if (team.goalDifference > 0) "+${team.goalDifference}" else "${team.goalDifference}"
        val gdColor = when {
            team.goalDifference > 0 -> MaterialTheme.colorScheme.tertiary
            team.goalDifference < 0 -> MaterialTheme.colorScheme.error
            else -> MaterialTheme.colorScheme.onSurfaceVariant
        }
        Text(
            text = gdText,
            modifier = Modifier.width(40.dp),
            style = MaterialTheme.typography.bodySmall,
            color = gdColor,
            textAlign = TextAlign.Center,
        )

        // PTS (볼드)
        Text(
            text = "${team.points}",
            modifier = Modifier.width(40.dp),
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurface,
            fontWeight = FontWeight.Bold,
            textAlign = TextAlign.Center,
        )
    }
}

private enum class PositionZone { UCL, EL, ECL, MID, PLAYOFF, RELEGATION }

private fun positionZone(position: Int, leagueCode: String): PositionZone = when (leagueCode) {
    "PL" -> when (position) {
        in 1..4 -> PositionZone.UCL
        5 -> PositionZone.EL
        6 -> PositionZone.ECL
        in 18..20 -> PositionZone.RELEGATION
        else -> PositionZone.MID
    }
    "PD" -> when (position) {
        in 1..4 -> PositionZone.UCL
        5, 6 -> PositionZone.EL
        in 18..20 -> PositionZone.RELEGATION
        else -> PositionZone.MID
    }
    "BL1" -> when (position) {
        in 1..4 -> PositionZone.UCL
        5, 6 -> PositionZone.EL
        16 -> PositionZone.PLAYOFF
        in 17..18 -> PositionZone.RELEGATION
        else -> PositionZone.MID
    }
    "SA" -> when (position) {
        in 1..4 -> PositionZone.UCL
        5, 6 -> PositionZone.EL
        in 18..20 -> PositionZone.RELEGATION
        else -> PositionZone.MID
    }
    "FL1" -> when (position) {
        in 1..3 -> PositionZone.UCL
        4, 5 -> PositionZone.EL
        16 -> PositionZone.PLAYOFF
        in 17..18 -> PositionZone.RELEGATION
        else -> PositionZone.MID
    }
    else -> PositionZone.MID
}

@Composable
private fun positionZoneColor(position: Int, leagueCode: String): Color =
    zoneColor(positionZone(position, leagueCode))

@Composable
private fun zoneColor(zone: PositionZone): Color = when (zone) {
    PositionZone.UCL -> MaterialTheme.colorScheme.primary
    PositionZone.EL -> MaterialTheme.colorScheme.tertiary
    PositionZone.ECL -> Color(0xFF22C55E).copy(alpha = 0.6f)
    PositionZone.PLAYOFF -> MaterialTheme.colorScheme.error.copy(alpha = 0.6f)
    PositionZone.RELEGATION -> MaterialTheme.colorScheme.error
    PositionZone.MID -> Color.Transparent
}

private fun leagueZones(leagueCode: String): List<PositionZone> = when (leagueCode) {
    "PL" -> listOf(PositionZone.UCL, PositionZone.EL, PositionZone.ECL, PositionZone.RELEGATION)
    "BL1", "FL1" -> listOf(PositionZone.UCL, PositionZone.EL, PositionZone.PLAYOFF, PositionZone.RELEGATION)
    else -> listOf(PositionZone.UCL, PositionZone.EL, PositionZone.RELEGATION)
}

private fun PositionZone.label(): String = when (this) {
    PositionZone.UCL -> "챔피언스리그"
    PositionZone.EL -> "유로파리그"
    PositionZone.ECL -> "컨퍼런스리그"
    PositionZone.PLAYOFF -> "강등 플레이오프"
    PositionZone.RELEGATION -> "강등"
    PositionZone.MID -> ""
}

@Composable
private fun StandingsLegend(leagueCode: String, modifier: Modifier = Modifier) {
    Row(
        modifier = modifier.horizontalScroll(rememberScrollState()),
        horizontalArrangement = Arrangement.spacedBy(16.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        leagueZones(leagueCode).forEach { zone ->
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                Box(
                    modifier = Modifier
                        .width(3.dp)
                        .height(14.dp)
                        .background(
                            color = zoneColor(zone),
                            shape = RoundedCornerShape(2.dp),
                        ),
                )
                Text(
                    text = zone.label(),
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }
}