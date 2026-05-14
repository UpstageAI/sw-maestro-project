import 'dart:async';

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:lucide_icons/lucide_icons.dart';

import '../api/calendar_api.dart';
import '../design/tokens/colors.dart';
import '../design/tokens/radius.dart';
import '../design/tokens/spacing.dart';
import '../design/tokens/typography.dart';
import '../models/calendar_event.dart';
import 'calendar_reload_notifier.dart';
import 'card_panel.dart';
import 'card_states.dart';

class CalendarCard extends StatefulWidget {
  const CalendarCard({
    super.key,
    required this.api,
    required this.weekStart,
    this.reloadNotifier,
  });

  final CalendarApi api;
  final DateTime weekStart;
  // Optional pub/sub: bumped by Slice B after inserting events from a
  // proposal so this card refetches without a full page reload.
  final CalendarReloadNotifier? reloadNotifier;

  @override
  State<CalendarCard> createState() => _CalendarCardState();
}

class _CalendarCardState extends State<CalendarCard> {
  // Last successful fetch — kept around so a refetch (proposal 등록 후 bump
  // 또는 재시도)에서 카드가 빈 skeleton 으로 깜빡이지 않고 직전 데이터를
  // 그대로 보여주다가 새 데이터가 도착하면 부드럽게 교체된다.
  List<CalendarEvent>? _lastEvents;
  Object? _lastError;

  @override
  void initState() {
    super.initState();
    unawaited(_trackedLoad());
    widget.reloadNotifier?.addListener(_onExternalReload);
  }

  @override
  void didUpdateWidget(covariant CalendarCard oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.reloadNotifier != widget.reloadNotifier) {
      oldWidget.reloadNotifier?.removeListener(_onExternalReload);
      widget.reloadNotifier?.addListener(_onExternalReload);
    }
    if (oldWidget.weekStart != widget.weekStart ||
        oldWidget.api != widget.api) {
      // Different week — drop cached events so the loading skeleton shows
      // (the cache no longer represents the requested range).
      _lastEvents = null;
      _lastError = null;
      unawaited(_trackedLoad());
    }
  }

  @override
  void dispose() {
    widget.reloadNotifier?.removeListener(_onExternalReload);
    super.dispose();
  }

  Future<List<CalendarEvent>> _trackedLoad() async {
    final end = widget.weekStart.add(const Duration(days: 7));
    try {
      final events = await widget.api.getCalendar(widget.weekStart, end);
      if (mounted) {
        setState(() {
          _lastEvents = events;
          _lastError = null;
        });
      }
      return events;
    } catch (e) {
      if (mounted) {
        setState(() {
          _lastError = e;
        });
      }
      rethrow;
    }
  }

  void _onExternalReload() {
    if (!mounted) return;
    unawaited(_trackedLoad());
  }

  void _retry() {
    _lastError = null;
    unawaited(_trackedLoad());
    setState(() {}); // clear the error UI immediately
  }

  @override
  Widget build(BuildContext context) {
    final weekLabel = _weekRangeLabel(widget.weekStart);

    return CardPanel(
      title: '이번 주 일정',
      icon: LucideIcons.calendar,
      trailing: Text(
        weekLabel,
        style: AppTypography.caption.copyWith(color: AppColors.textTertiary),
      ),
      child: _buildBody(),
    );
  }

  Widget _buildBody() {
    // Cached data wins over the in-flight future so background refetches
    // don't drop the card back to a skeleton.
    if (_lastEvents != null) {
      if (_lastEvents!.isEmpty) {
        return const CardEmptyState(
          icon: LucideIcons.calendarOff,
          message: '이번 주 등록된 일정이 없습니다',
          hint: 'calendar_events 시드를 INSERT 하면 표시됩니다',
        );
      }
      return _EventList(events: _lastEvents!);
    }
    if (_lastError != null) {
      return CardErrorState(
        message: '일정을 불러오지 못했습니다',
        detail: _lastError.toString(),
        onRetry: _retry,
      );
    }
    return const CardLoadingRows(iconSize: 44);
  }
}

String _weekRangeLabel(DateTime weekStart) {
  final end = weekStart.add(const Duration(days: 6));
  final f = DateFormat('M/d');
  return '${f.format(weekStart)} – ${f.format(end)}';
}

class _EventList extends StatelessWidget {
  const _EventList({required this.events});

  final List<CalendarEvent> events;

  @override
  Widget build(BuildContext context) {
    final today = DateTime.now();
    final dayLabel = DateFormat('E', 'ko_KR');
    final timeLabel = DateFormat('HH:mm');

    // Mon→Sun (ascending chronological). Defensive client-side sort so the
    // UI does not depend on whichever order the backend echoes back.
    final sorted = [...events]..sort((a, b) => a.startAt.compareTo(b.startAt));

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        for (var i = 0; i < sorted.length; i++) ...[
          if (i != 0) const Divider(height: 1, color: AppColors.divider),
          _EventRow(
            event: sorted[i],
            isToday: _isSameDate(sorted[i].startAt, today),
            dayLabel: dayLabel.format(sorted[i].startAt),
            timeLabel: timeLabel.format(sorted[i].startAt),
          ),
        ],
      ],
    );
  }

  static bool _isSameDate(DateTime a, DateTime b) =>
      a.year == b.year && a.month == b.month && a.day == b.day;
}

class _EventRow extends StatelessWidget {
  const _EventRow({
    required this.event,
    required this.isToday,
    required this.dayLabel,
    required this.timeLabel,
  });

  final CalendarEvent event;
  final bool isToday;
  final String dayLabel;
  final String timeLabel;

  @override
  Widget build(BuildContext context) {
    final accentColor =
        event.isBusy ? AppColors.statusDanger : AppColors.statusSuccess;

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: AppSpacing.s3),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Container(
            width: 44,
            padding: const EdgeInsets.symmetric(vertical: AppSpacing.s1),
            decoration: BoxDecoration(
              color: isToday
                  ? AppColors.accentPrimary.withValues(alpha: 0.12)
                  : AppColors.bgElevated2,
              borderRadius: BorderRadius.circular(AppRadius.md),
              border: Border.all(
                color: isToday
                    ? AppColors.accentPrimary.withValues(alpha: 0.4)
                    : Colors.transparent,
              ),
            ),
            child: Column(
              children: [
                Text(
                  dayLabel,
                  style: AppTypography.overline.copyWith(
                    color: isToday
                        ? AppColors.accentPrimary
                        : AppColors.textSecondary,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  timeLabel,
                  style: AppTypography.dataMd.copyWith(
                    fontSize: 13,
                    color: isToday
                        ? AppColors.accentPrimary
                        : AppColors.textPrimary,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: AppSpacing.s4),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  event.title,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: AppTypography.body.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 2),
                Row(
                  children: [
                    Container(
                      width: 6,
                      height: 6,
                      decoration: BoxDecoration(
                        color: accentColor,
                        shape: BoxShape.circle,
                      ),
                    ),
                    const SizedBox(width: AppSpacing.s2),
                    Text(
                      event.isBusy ? '바쁨' : '운동 가능',
                      style: AppTypography.caption.copyWith(color: accentColor),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
