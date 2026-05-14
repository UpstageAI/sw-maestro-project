import 'dart:math' as math;

import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:lucide_icons/lucide_icons.dart';

import '../api/health_api.dart';
import '../design/tokens/colors.dart';
import '../design/tokens/spacing.dart';
import '../design/tokens/typography.dart';
import '../models/health_snapshot.dart';
import 'card_panel.dart';
import 'card_states.dart';

class HealthCard extends StatefulWidget {
  const HealthCard({super.key, required this.api});

  final HealthApi api;

  @override
  State<HealthCard> createState() => _HealthCardState();
}

class _HealthCardState extends State<HealthCard> {
  late Future<HealthSnapshot?> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<HealthSnapshot?> _load() => widget.api.getLatest();

  void _retry() => setState(() => _future = _load());

  @override
  Widget build(BuildContext context) {
    return CardPanel(
      title: '컨디션 점수',
      icon: LucideIcons.heartPulse,
      child: FutureBuilder<HealthSnapshot?>(
        future: _future,
        builder: (context, snapshot) {
          return switch (snapshot.connectionState) {
            ConnectionState.waiting => const CardLoadingDonut(),
            _ when snapshot.hasError => CardErrorState(
                message: '컨디션을 불러오지 못했습니다',
                detail: snapshot.error.toString(),
                onRetry: _retry,
              ),
            _ when snapshot.data == null => const CardEmptyState(
                icon: LucideIcons.heartPulse,
                message: '측정 데이터 없음',
                hint: 'health_snapshots 시드를 INSERT 하면 표시됩니다',
              ),
            _ => _DonutWithMeta(snapshot: snapshot.data!),
          };
        },
      ),
    );
  }
}

/// 임시 산식: sleep_hours 와 activity_minutes 를 0~100 점수로 합성.
/// 5/8 통합 시 C agent 의 daily_conditions.score 로 대체 예정.
int _composeScore(HealthSnapshot s) {
  final sleepPart = math.min(70.0, (s.sleepHours / 8.0) * 70.0);
  final activityPart = math.min(30.0, (s.activityMinutes / 60.0) * 30.0);
  return (sleepPart + activityPart).clamp(0, 100).round();
}

class _DonutWithMeta extends StatelessWidget {
  const _DonutWithMeta({required this.snapshot});

  final HealthSnapshot snapshot;

  @override
  Widget build(BuildContext context) {
    final score = _composeScore(snapshot);
    return Column(
      children: [
        _Donut(score: score),
        const SizedBox(height: AppSpacing.s4),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceEvenly,
          children: [
            _Meta(
              icon: LucideIcons.moon,
              label: '수면',
              value: '${snapshot.sleepHours.toStringAsFixed(1)}시간',
            ),
            _Meta(
              icon: LucideIcons.footprints,
              label: '활동',
              value: '${snapshot.activityMinutes}분',
            ),
            if (snapshot.restingHr != null)
              _Meta(
                icon: LucideIcons.activity,
                label: '안정 HR',
                value: '${snapshot.restingHr}',
              ),
          ],
        ),
      ],
    );
  }
}

class _Donut extends StatelessWidget {
  const _Donut({required this.score});

  final int score;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 144,
      height: 144,
      child: Stack(
        alignment: Alignment.center,
        children: [
          PieChart(
            PieChartData(
              startDegreeOffset: -90,
              sectionsSpace: 0,
              centerSpaceRadius: 54,
              sections: [
                PieChartSectionData(
                  value: score.toDouble(),
                  color: AppColors.accentPrimary,
                  radius: 12,
                  showTitle: false,
                ),
                PieChartSectionData(
                  value: (100 - score).toDouble(),
                  color: AppColors.bgElevated2,
                  radius: 12,
                  showTitle: false,
                ),
              ],
            ),
          ),
          Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                '$score',
                style: AppTypography.dataXl.copyWith(fontSize: 36, height: 1),
              ),
              const SizedBox(height: 2),
              Text(
                '/ 100',
                style: AppTypography.caption
                    .copyWith(color: AppColors.textTertiary),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _Meta extends StatelessWidget {
  const _Meta({required this.icon, required this.label, required this.value});

  final IconData icon;
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 14, color: AppColors.textTertiary),
        const SizedBox(height: 4),
        Text(
          value,
          style: AppTypography.dataMd.copyWith(fontSize: 14),
        ),
        Text(
          label,
          style: AppTypography.caption.copyWith(color: AppColors.textTertiary),
        ),
      ],
    );
  }
}
