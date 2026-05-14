import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:lucide_icons/lucide_icons.dart';

import '../api/workouts_api.dart';
import '../design/tokens/colors.dart';
import '../design/tokens/spacing.dart';
import '../design/tokens/typography.dart';
import '../models/workout_record.dart';
import 'card_panel.dart';
import 'card_states.dart';

class WorkoutsCard extends StatefulWidget {
  const WorkoutsCard({super.key, required this.api, this.limit = 5});

  final WorkoutsApi api;
  final int limit;

  @override
  State<WorkoutsCard> createState() => _WorkoutsCardState();
}

class _WorkoutsCardState extends State<WorkoutsCard> {
  late Future<List<WorkoutRecord>> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<List<WorkoutRecord>> _load() =>
      widget.api.getRecent(limit: widget.limit);

  void _retry() => setState(() => _future = _load());

  @override
  Widget build(BuildContext context) {
    return CardPanel(
      title: '최근 운동 이력',
      icon: LucideIcons.clock,
      child: FutureBuilder<List<WorkoutRecord>>(
        future: _future,
        builder: (context, snapshot) {
          return switch (snapshot.connectionState) {
            ConnectionState.waiting => const CardLoadingRows(iconSize: 40),
            _ when snapshot.hasError => CardErrorState(
                message: '운동 이력을 불러오지 못했습니다',
                detail: snapshot.error.toString(),
                onRetry: _retry,
              ),
            _ when (snapshot.data ?? const []).isEmpty => const CardEmptyState(
                icon: LucideIcons.dumbbell,
                message: '최근 운동 이력 없음',
                hint: 'workout_records 시드를 INSERT 하면 표시됩니다',
              ),
            _ => _RecordList(records: snapshot.data!),
          };
        },
      ),
    );
  }
}

class _RecordList extends StatelessWidget {
  const _RecordList({required this.records});

  final List<WorkoutRecord> records;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        for (var i = 0; i < records.length; i++) ...[
          if (i != 0) const Divider(height: 1, color: AppColors.divider),
          _RecordRow(record: records[i]),
        ],
      ],
    );
  }
}

class _CategoryStyle {
  const _CategoryStyle(this.color, this.icon);
  final Color color;
  final IconData icon;
}

_CategoryStyle _styleFor(String type) {
  final t = type.toLowerCase();
  if (t.contains('러닝') || t.contains('run') || t.contains('유산소')) {
    return const _CategoryStyle(AppColors.catCardio, LucideIcons.footprints);
  }
  if (t.contains('스쿼트') || t.contains('하체') || t.contains('squat')) {
    return const _CategoryStyle(AppColors.catLower, LucideIcons.dumbbell);
  }
  if (t.contains('코어') || t.contains('플랭크') || t.contains('core')) {
    return const _CategoryStyle(AppColors.catCore, LucideIcons.sparkles);
  }
  if (t.contains('휴식') || t.contains('rest')) {
    return const _CategoryStyle(AppColors.catRest, LucideIcons.moon);
  }
  return const _CategoryStyle(AppColors.catUpper, LucideIcons.dumbbell);
}

class _RecordRow extends StatelessWidget {
  const _RecordRow({required this.record});

  final WorkoutRecord record;

  @override
  Widget build(BuildContext context) {
    final style = _styleFor(record.type);
    final dateLabel = DateFormat('M/d').format(record.date);

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: AppSpacing.s3),
      child: Row(
        children: [
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: style.color.withValues(alpha: 0.18),
              shape: BoxShape.circle,
              border: Border.all(color: style.color.withValues(alpha: 0.4)),
            ),
            child: Icon(style.icon, size: 18, color: style.color),
          ),
          const SizedBox(width: AppSpacing.s3),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  record.type,
                  style: AppTypography.body.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  record.muscles.isEmpty
                      ? '강도 ${record.intensity}/5'
                      : '${record.muscles.join(', ')} · 강도 ${record.intensity}/5',
                  style: AppTypography.caption.copyWith(
                    color: AppColors.textTertiary,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
          const SizedBox(width: AppSpacing.s2),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                dateLabel,
                style: AppTypography.caption.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
              Text(
                "${record.durationMin}'",
                style: AppTypography.dataMd.copyWith(fontSize: 14),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
