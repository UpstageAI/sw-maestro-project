import 'package:flutter/material.dart';
import 'package:lucide_icons/lucide_icons.dart';

import '../api/calendar_api.dart';
import '../cards/calendar_reload_notifier.dart';
import '../design/tokens/colors.dart';
import '../design/tokens/radius.dart';
import '../design/tokens/shadows.dart';
import '../design/tokens/spacing.dart';
import '../design/tokens/typography.dart';
import 'chat_controller.dart';
import 'chat_message.dart';
import 'proposal_notifier.dart';
import 'widgets/chat_input.dart';
import 'widgets/message_bubble.dart';

/// Right-rail AI coach chat panel. Replaces A's `_ChatPlaceholderPanel`.
/// Slice B owns this widget and everything it imports under `lib/chat/`.
class ChatPanel extends StatefulWidget {
  const ChatPanel({
    super.key,
    this.proposalNotifier,
    this.calendarApi,
    this.calendarReload,
  });

  /// Optional fan-out: when an agent proposal arrives, forward it to this
  /// notifier so dashboard cards (radar, calendar) can react. Owner is
  /// responsible for disposing.
  final ProposalNotifier? proposalNotifier;
  // ProposalCard's "캘린더에 등록" button needs the Supabase wrapper to insert
  // events and a reload notifier to ask the calendar card to refetch. Both
  // optional so unit tests can render the panel headless.
  final CalendarApi? calendarApi;
  final CalendarReloadNotifier? calendarReload;

  @override
  State<ChatPanel> createState() => _ChatPanelState();
}

class _ChatPanelState extends State<ChatPanel> {
  late final ChatController _controller;
  final _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    _controller = ChatController(proposalNotifier: widget.proposalNotifier);
    _controller.addListener(_onChange);
  }

  @override
  void dispose() {
    _controller.removeListener(_onChange);
    _controller.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void _onChange() {
    if (!mounted) return;
    setState(() {});
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_scrollController.hasClients) return;
      _scrollController.animateTo(
        _scrollController.position.maxScrollExtent,
        duration: const Duration(milliseconds: 180),
        curve: Curves.easeOut,
      );
    });
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.s5),
      decoration: BoxDecoration(
        color: AppColors.bgElevated1,
        borderRadius: BorderRadius.circular(AppRadius.xl),
        border: Border.all(color: AppColors.borderSubtle),
        boxShadow: AppShadows.card,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _ChatHeader(
            onReset: _controller.resetConversation,
            canReset:
                !_controller.isStreaming && _controller.messages.isNotEmpty,
          ),
          const SizedBox(height: AppSpacing.s4),
          Expanded(
            child: _controller.messages.isEmpty
                ? const _EmptyState()
                : _MessageList(
                    messages: _controller.messages,
                    scrollController: _scrollController,
                    calendarApi: widget.calendarApi,
                    calendarReload: widget.calendarReload,
                    proposalNotifier: widget.proposalNotifier,
                  ),
          ),
          const SizedBox(height: AppSpacing.s3),
          ChatInput(
            enabled: !_controller.isStreaming,
            onSubmit: _controller.send,
          ),
        ],
      ),
    );
  }
}

class _ChatHeader extends StatelessWidget {
  const _ChatHeader({required this.onReset, required this.canReset});

  final VoidCallback onReset;
  final bool canReset;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          padding: const EdgeInsets.all(AppSpacing.s2),
          decoration: BoxDecoration(
            color: AppColors.bgElevated2,
            borderRadius: BorderRadius.circular(AppRadius.full),
          ),
          child: Icon(
            LucideIcons.bot,
            size: 18,
            color: AppColors.accentPrimary,
          ),
        ),
        const SizedBox(width: AppSpacing.s3),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('AI 코치', style: AppTypography.h3),
              Text(
                '캘린더·컨디션·운동기록을 종합한 추천',
                style: AppTypography.caption,
              ),
            ],
          ),
        ),
        _ResetButton(onPressed: canReset ? onReset : null),
      ],
    );
  }
}

class _ResetButton extends StatelessWidget {
  const _ResetButton({required this.onPressed});

  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    final enabled = onPressed != null;
    final color = enabled
        ? AppColors.textTertiary
        : AppColors.textTertiary.withValues(alpha: 0.4);

    return Tooltip(
      message: '새 대화 시작',
      child: InkWell(
        onTap: onPressed,
        borderRadius: BorderRadius.circular(AppRadius.full),
        child: Container(
          padding: const EdgeInsets.all(AppSpacing.s2),
          decoration: BoxDecoration(
            color: AppColors.bgElevated2,
            borderRadius: BorderRadius.circular(AppRadius.full),
          ),
          child: Icon(LucideIcons.refreshCw, size: 16, color: color),
        ),
      ),
    );
  }
}

class _MessageList extends StatelessWidget {
  const _MessageList({
    required this.messages,
    required this.scrollController,
    this.calendarApi,
    this.calendarReload,
    this.proposalNotifier,
  });

  final List<ChatMessage> messages;
  final ScrollController scrollController;
  final CalendarApi? calendarApi;
  final CalendarReloadNotifier? calendarReload;
  final ProposalNotifier? proposalNotifier;

  @override
  Widget build(BuildContext context) {
    return ListView.separated(
      controller: scrollController,
      padding: const EdgeInsets.symmetric(vertical: AppSpacing.s2),
      itemCount: messages.length,
      separatorBuilder: (_, __) => const SizedBox(height: AppSpacing.s2),
      // ValueKey ties each MessageBubble to its message id so ListView reuse
      // doesn't (a) replay the entrance fade-in on streaming text deltas or
      // (b) wipe ProposalCard's "등록 완료" state mid-rebuild.
      itemBuilder: (_, i) => MessageBubble(
        key: ValueKey(messages[i].id),
        message: messages[i],
        calendarApi: calendarApi,
        calendarReload: calendarReload,
        proposalNotifier: proposalNotifier,
      ),
    );
  }
}

class _EmptyState extends StatefulWidget {
  const _EmptyState();

  @override
  State<_EmptyState> createState() => _EmptyStateState();
}

class _EmptyStateState extends State<_EmptyState>
    with SingleTickerProviderStateMixin {
  late final AnimationController _pulse;

  @override
  void initState() {
    super.initState();
    _pulse = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2200),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _pulse.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          AnimatedBuilder(
            animation: _pulse,
            builder: (context, child) {
              final t = Curves.easeInOut.transform(_pulse.value);
              return Opacity(
                opacity: 0.55 + 0.45 * t,
                child: Transform.scale(scale: 0.96 + 0.08 * t, child: child),
              );
            },
            child: Icon(
              LucideIcons.sparkles,
              size: 32,
              color: AppColors.accentPrimaryGlow,
            ),
          ),
          const SizedBox(height: AppSpacing.s3),
          Text(
            '"이번 주 운동 추천해줘"',
            style: AppTypography.body.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(height: AppSpacing.s1),
          Text(
            '메시지를 입력하면 코치가 응답합니다',
            style: AppTypography.caption.copyWith(
              color: AppColors.textTertiary,
            ),
          ),
        ],
      ),
    );
  }
}
