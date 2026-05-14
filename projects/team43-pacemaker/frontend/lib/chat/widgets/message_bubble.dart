import 'package:flutter/material.dart';
import 'package:lucide_icons/lucide_icons.dart';

import '../../api/calendar_api.dart';
import '../../cards/calendar_reload_notifier.dart';
import '../../design/tokens/colors.dart';
import '../../design/tokens/radius.dart';
import '../../design/tokens/spacing.dart';
import '../../design/tokens/typography.dart';
import '../chat_message.dart';
import '../proposal_notifier.dart';
import 'proposal_card.dart';

class MessageBubble extends StatefulWidget {
  const MessageBubble({
    super.key,
    required this.message,
    this.calendarApi,
    this.calendarReload,
    this.proposalNotifier,
  });

  final ChatMessage message;
  // Forwarded to ProposalCard so the "캘린더에 등록" button can call Supabase
  // and bump the calendar card. All nullable for unit tests.
  final CalendarApi? calendarApi;
  final CalendarReloadNotifier? calendarReload;
  final ProposalNotifier? proposalNotifier;

  @override
  State<MessageBubble> createState() => _MessageBubbleState();
}

class _MessageBubbleState extends State<MessageBubble>
    with SingleTickerProviderStateMixin {
  late final AnimationController _entrance;

  @override
  void initState() {
    super.initState();
    _entrance = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 240),
    )..forward();
  }

  @override
  void dispose() {
    _entrance.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final message = widget.message;
    final isUser = message.role == ChatRole.user;
    final alignment = isUser ? Alignment.centerRight : Alignment.centerLeft;
    final bubbleColor = isUser
        ? AppColors.accentSecondary.withValues(alpha: 0.22)
        : AppColors.bgElevated2;
    final borderColor =
        isUser ? AppColors.accentSecondaryGlow : AppColors.borderSubtle;

    final fade = CurvedAnimation(parent: _entrance, curve: Curves.easeOut);
    final slide = Tween<Offset>(
      begin: const Offset(0, 0.18),
      end: Offset.zero,
    ).animate(CurvedAnimation(parent: _entrance, curve: Curves.easeOutCubic));

    final column = Column(
      crossAxisAlignment:
          isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
      children: [
        if (!isUser && (message.toolCallNote?.isNotEmpty ?? false))
          _ToolCallChip(label: message.toolCallNote!),
        Container(
          margin: const EdgeInsets.symmetric(vertical: AppSpacing.s2 / 2),
          padding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.s4,
            vertical: AppSpacing.s3,
          ),
          decoration: BoxDecoration(
            color: bubbleColor,
            borderRadius: BorderRadius.circular(AppRadius.lg),
            border: Border.all(color: borderColor),
          ),
          child: _BubbleBody(message: message),
        ),
        if (message.proposal != null)
          Padding(
            padding: const EdgeInsets.only(top: AppSpacing.s2),
            child: ProposalCard(
              proposal: message.proposal!,
              calendarApi: widget.calendarApi,
              calendarReload: widget.calendarReload,
              proposalNotifier: widget.proposalNotifier,
            ),
          ),
      ],
    );

    return FadeTransition(
      opacity: fade,
      child: SlideTransition(
        position: slide,
        child: Align(
          alignment: alignment,
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 360),
            child: isUser
                ? column
                : Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const _AssistantAvatar(),
                      const SizedBox(width: AppSpacing.s2),
                      Flexible(child: column),
                    ],
                  ),
          ),
        ),
      ),
    );
  }
}

class _AssistantAvatar extends StatelessWidget {
  const _AssistantAvatar();

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(top: 4),
      width: 22,
      height: 22,
      decoration: BoxDecoration(
        color: AppColors.bgElevated2,
        borderRadius: BorderRadius.circular(AppRadius.full),
        border: Border.all(color: AppColors.borderSubtle),
      ),
      child: Icon(
        LucideIcons.bot,
        size: 12,
        color: AppColors.accentPrimary,
      ),
    );
  }
}

class _BubbleBody extends StatelessWidget {
  const _BubbleBody({required this.message});

  final ChatMessage message;

  @override
  Widget build(BuildContext context) {
    if (message.errorMessage != null) {
      return Row(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(LucideIcons.alertCircle,
              size: 14, color: AppColors.statusDanger),
          const SizedBox(width: AppSpacing.s2),
          Flexible(
            child: Text(
              message.errorMessage!,
              style: AppTypography.body.copyWith(color: AppColors.statusDanger),
            ),
          ),
        ],
      );
    }

    if (message.text.isEmpty && message.isStreaming) {
      return const _TypingDots();
    }

    return Text(message.text, style: AppTypography.body);
  }
}

class _ToolCallChip extends StatelessWidget {
  const _ToolCallChip({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: AppSpacing.s1),
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.s3,
        vertical: AppSpacing.s1,
      ),
      decoration: BoxDecoration(
        color: AppColors.bgElevated1,
        borderRadius: BorderRadius.circular(AppRadius.full),
        border: Border.all(color: AppColors.borderSubtle),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(LucideIcons.zap, size: 11, color: AppColors.accentPrimary),
          const SizedBox(width: AppSpacing.s1),
          Text(
            label,
            style: AppTypography.caption.copyWith(
              color: AppColors.accentPrimary,
            ),
          ),
        ],
      ),
    );
  }
}

class _TypingDots extends StatefulWidget {
  const _TypingDots();
  @override
  State<_TypingDots> createState() => _TypingDotsState();
}

class _TypingDotsState extends State<_TypingDots>
    with SingleTickerProviderStateMixin {
  late final AnimationController _ctrl;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    )..repeat();
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _ctrl,
      builder: (context, _) {
        return Row(
          mainAxisSize: MainAxisSize.min,
          children: List.generate(3, (i) {
            final t = ((_ctrl.value + i * 0.2) % 1.0);
            final opacity = 0.3 + 0.7 * (1 - (t * 2 - 1).abs());
            return Padding(
              padding: const EdgeInsets.symmetric(horizontal: 2),
              child: Container(
                width: 6,
                height: 6,
                decoration: BoxDecoration(
                  color: AppColors.textSecondary.withValues(alpha: opacity),
                  shape: BoxShape.circle,
                ),
              ),
            );
          }),
        );
      },
    );
  }
}
