import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:lucide_icons/lucide_icons.dart';

import '../../api/calendar_api.dart';
import '../../cards/calendar_reload_notifier.dart';
import '../../design/tokens/colors.dart';
import '../../design/tokens/radius.dart';
import '../../design/tokens/spacing.dart';
import '../../design/tokens/typography.dart';
import '../../models/calendar_event.dart';
import '../chat_message.dart';
import '../proposal_notifier.dart';

/// Renders a [ScheduleProposal] as a stack of slot cards inside the chat
/// transcript. The "캘린더에 등록" button (F7) inserts every slot into
/// `calendar_events` and bumps [CalendarReloadNotifier] so the calendar card
/// refetches.
class ProposalCard extends StatefulWidget {
  const ProposalCard({
    super.key,
    required this.proposal,
    this.calendarApi,
    this.calendarReload,
    this.proposalNotifier,
  });

  final ScheduleProposal proposal;
  // Optional so widget tests / preview surfaces can render without wiring up
  // Supabase. When null the register button is hidden.
  final CalendarApi? calendarApi;
  final CalendarReloadNotifier? calendarReload;
  // Tracks ids of rows we created so a refined re-registration replaces
  // (not stacks) the previous one.
  final ProposalNotifier? proposalNotifier;

  @override
  State<ProposalCard> createState() => _ProposalCardState();
}

enum _RegisterState { idle, registering, done, failed }

class _ProposalCardState extends State<ProposalCard> {
  _RegisterState _state = _RegisterState.idle;
  String? _errorMessage;

  Future<void> _onRegister() async {
    final api = widget.calendarApi;
    if (api == null ||
        _state == _RegisterState.registering ||
        _state == _RegisterState.done) {
      return;
    }
    setState(() {
      _state = _RegisterState.registering;
      _errorMessage = null;
    });

    try {
      // Replace semantics — drop any rows we registered earlier in this
      // session so refining ("화요일은 바쁠 것 같아") doesn't stack a second
      // copy. Only ids we created ourselves are touched (tracked in
      // ProposalNotifier) — seed data + user-authored events stay put.
      final priorIds = widget.proposalNotifier?.registeredEventIds ?? const [];
      if (priorIds.isNotEmpty) {
        await api.deleteEventsByIds(priorIds);
      }

      final newIds = <int>[];
      for (final slot in widget.proposal.slots) {
        // 휴식 슬롯은 targetMuscles가 비어 있어 "휴식 ()" 처럼 빈 괄호가
        // 붙는다. 비어 있으면 type만, 있으면 "type (부위)" 로 포맷.
        final muscles = slot.targetMuscles.join(', ');
        final title =
            muscles.isEmpty ? slot.type : '${slot.type} ($muscles)';
        final inserted = await api.createEvent(CalendarEvent(
          startAt: slot.start,
          endAt: slot.end,
          title: title,
        ));
        if (inserted.id != null) newIds.add(inserted.id!);
      }
      await widget.proposalNotifier?.recordRegisteredIds(newIds);
      widget.calendarReload?.bump();
      if (!mounted) return;
      setState(() => _state = _RegisterState.done);
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _state = _RegisterState.failed;
        _errorMessage = e.toString();
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final proposal = widget.proposal;
    if (proposal.slots.isEmpty) return const SizedBox.shrink();

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpacing.s4),
      decoration: BoxDecoration(
        gradient: AppColors.recommendGradient,
        borderRadius: BorderRadius.circular(AppRadius.lg),
        border: Border.all(color: AppColors.borderSubtle),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Icon(LucideIcons.sparkles,
                  size: 14, color: AppColors.accentPrimary),
              const SizedBox(width: AppSpacing.s2),
              Text(
                '추천 운동 슬롯',
                style: AppTypography.caption.copyWith(
                  color: AppColors.accentPrimary,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.s3),
          for (var i = 0; i < proposal.slots.length; i++) ...[
            if (i != 0) const SizedBox(height: AppSpacing.s2),
            _SlotRow(slot: proposal.slots[i]),
          ],
          if (widget.calendarApi != null) ...[
            const SizedBox(height: AppSpacing.s3),
            _RegisterButton(
              state: _state,
              slotCount: proposal.slots.length,
              errorMessage: _errorMessage,
              onTap: _onRegister,
            ),
          ],
        ],
      ),
    );
  }
}

class _RegisterButton extends StatelessWidget {
  const _RegisterButton({
    required this.state,
    required this.slotCount,
    required this.errorMessage,
    required this.onTap,
  });

  final _RegisterState state;
  final int slotCount;
  final String? errorMessage;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final (label, icon, fg, bg) = switch (state) {
      _RegisterState.idle => (
          '캘린더에 $slotCount건 등록',
          LucideIcons.calendarPlus,
          AppColors.textOnAccent,
          AppColors.accentPrimary,
        ),
      _RegisterState.registering => (
          '등록 중…',
          LucideIcons.loader,
          AppColors.textOnAccent,
          AppColors.accentPrimary.withValues(alpha: 0.7),
        ),
      _RegisterState.done => (
          '등록 완료',
          LucideIcons.checkCircle2,
          AppColors.statusSuccess,
          AppColors.statusSuccessBg,
        ),
      _RegisterState.failed => (
          '다시 등록',
          LucideIcons.alertTriangle,
          AppColors.statusDanger,
          AppColors.statusDangerBg,
        ),
    };

    final isInteractive =
        state == _RegisterState.idle || state == _RegisterState.failed;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        InkWell(
          onTap: isInteractive ? onTap : null,
          borderRadius: BorderRadius.circular(AppRadius.md),
          child: Container(
            padding: const EdgeInsets.symmetric(
              horizontal: AppSpacing.s4,
              vertical: AppSpacing.s2,
            ),
            decoration: BoxDecoration(
              color: bg,
              borderRadius: BorderRadius.circular(AppRadius.md),
              border: Border.all(color: fg.withValues(alpha: 0.25)),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(icon, size: 14, color: fg),
                const SizedBox(width: AppSpacing.s2),
                Text(
                  label,
                  style: AppTypography.caption.copyWith(
                    color: fg,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
        ),
        if (state == _RegisterState.failed && errorMessage != null) ...[
          const SizedBox(height: AppSpacing.s1),
          Text(
            errorMessage!,
            style:
                AppTypography.caption.copyWith(color: AppColors.statusDanger),
          ),
        ],
      ],
    );
  }
}

class _SlotRow extends StatelessWidget {
  const _SlotRow({required this.slot});

  final WorkoutSlot slot;

  @override
  Widget build(BuildContext context) {
    final dayLabel = DateFormat('M/d (E)', 'ko_KR').format(slot.start);
    final timeLabel =
        '${DateFormat('HH:mm').format(slot.start)}–${DateFormat('HH:mm').format(slot.end)}';

    return Container(
      padding: const EdgeInsets.all(AppSpacing.s3),
      decoration: BoxDecoration(
        color: AppColors.bgElevated1,
        borderRadius: BorderRadius.circular(AppRadius.md),
        border: Border.all(color: AppColors.borderSubtle),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  '$dayLabel · $timeLabel',
                  style: AppTypography.caption.copyWith(
                    color: AppColors.textSecondary,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
              _IntensityChip(intensity: slot.intensity),
            ],
          ),
          const SizedBox(height: AppSpacing.s1),
          Text(
            slot.targetMuscles.isEmpty
                ? slot.type
                : '${slot.type} · ${slot.targetMuscles.join(', ')}',
            style: AppTypography.body.copyWith(fontWeight: FontWeight.w600),
          ),
          if (slot.rationale.isNotEmpty) ...[
            const SizedBox(height: 2),
            Text(
              slot.rationale,
              style: AppTypography.caption,
            ),
          ],
        ],
      ),
    );
  }
}

class _IntensityChip extends StatelessWidget {
  const _IntensityChip({required this.intensity});

  final int intensity;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.s2,
        vertical: 2,
      ),
      decoration: BoxDecoration(
        color: AppColors.bgElevated2,
        borderRadius: BorderRadius.circular(AppRadius.full),
      ),
      child: Text(
        '강도 $intensity/5',
        style: AppTypography.overline.copyWith(
          color: AppColors.textSecondary,
        ),
      ),
    );
  }
}
