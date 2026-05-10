import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:lucide_icons/lucide_icons.dart';

import '../design/tokens/colors.dart';
import '../design/tokens/fatigue_palette.dart';
import '../design/tokens/spacing.dart';
import '../design/tokens/typography.dart';
import '../models/muscle_fatigue_state.dart';
import 'card_panel.dart';

/// Agent `_MUSCLES`(`agent/nodes.py:15`) 순서. 레이더 회전 라벨이 SSE
/// proposal 출력에 따라 흔들리지 않도록 클라이언트도 같은 순서로 고정한다.
const List<String> _muscleOrder = [
  '가슴',
  '등',
  '하체',
  '어깨',
  '코어',
  '이두',
  '삼두',
];

class FatigueRadarCard extends StatelessWidget {
  const FatigueRadarCard({super.key, required this.state});

  final MuscleFatigueState state;

  @override
  Widget build(BuildContext context) {
    final entries = _orderedEntries(state.fatigue);
    final avg = entries.isEmpty
        ? 0
        : (entries.map((e) => e.value).reduce((a, b) => a + b) / entries.length)
            .round();
    final lineColor = fatigueColor(avg);

    return CardPanel(
      title: '부위별 피로도',
      icon: LucideIcons.sparkles,
      trailing: Text(
        '0–5 스케일',
        style: AppTypography.caption.copyWith(color: AppColors.textTertiary),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: AppSpacing.s3),
        child: SizedBox(
          height: 280,
          child: RadarChart(
            RadarChartData(
              radarShape: RadarShape.polygon,
              tickCount: 5,
              tickBorderData: const BorderSide(
                color: AppColors.borderSubtle,
                width: 1,
              ),
              gridBorderData: const BorderSide(
                color: AppColors.borderSubtle,
                width: 1,
              ),
              radarBorderData:
                  const BorderSide(color: AppColors.borderSubtle, width: 1),
              borderData: FlBorderData(show: false),
              titleTextStyle: AppTypography.caption,
              getTitle: (index, angle) {
                final entry = entries[index];
                return RadarChartTitle(
                  text: entry.key,
                  angle: 0,
                );
              },
              ticksTextStyle: const TextStyle(
                color: Colors.transparent,
                fontSize: 10,
              ),
              radarBackgroundColor: Colors.transparent,
              dataSets: [
                RadarDataSet(
                  fillColor: lineColor.withValues(alpha: 0.2),
                  borderColor: lineColor,
                  borderWidth: 2,
                  entryRadius: 4,
                  dataEntries: [
                    for (final e in entries)
                      RadarEntry(value: e.value.toDouble()),
                  ],
                ),
              ],
              radarTouchData: RadarTouchData(enabled: false),
            ),
          ),
        ),
      ),
    );
  }
}

/// `_muscleOrder` 우선, 누락 키는 0으로 채우고, 모르는 키는 끝에 append.
List<MapEntry<String, int>> _orderedEntries(Map<String, int> fatigue) {
  final result = <MapEntry<String, int>>[];
  final seen = <String>{};
  for (final key in _muscleOrder) {
    result.add(MapEntry(key, fatigue[key] ?? 0));
    seen.add(key);
  }
  for (final entry in fatigue.entries) {
    if (!seen.contains(entry.key)) {
      result.add(entry);
    }
  }
  return result;
}
