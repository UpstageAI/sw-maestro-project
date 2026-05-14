import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:lucide_icons/lucide_icons.dart';

import '../../design/tokens/colors.dart';
import '../../design/tokens/radius.dart';
import '../../design/tokens/spacing.dart';
import '../../design/tokens/typography.dart';

class ChatInput extends StatefulWidget {
  const ChatInput({
    super.key,
    required this.onSubmit,
    required this.enabled,
  });

  final ValueChanged<String> onSubmit;
  final bool enabled;

  @override
  State<ChatInput> createState() => _ChatInputState();
}

class _ChatInputState extends State<ChatInput> {
  final _controller = TextEditingController();
  final _focusNode = FocusNode();

  @override
  void dispose() {
    _controller.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  void _handleSubmit() {
    final text = _controller.text.trim();
    if (text.isEmpty || !widget.enabled) return;
    widget.onSubmit(text);
    _controller.clear();
    _focusNode.requestFocus();
  }

  @override
  Widget build(BuildContext context) {
    final canSend = widget.enabled && _controller.text.trim().isNotEmpty;

    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.s4,
        vertical: AppSpacing.s2,
      ),
      decoration: BoxDecoration(
        color: AppColors.bgElevated2,
        borderRadius: BorderRadius.circular(AppRadius.full),
        border: Border.all(color: AppColors.borderSubtle),
      ),
      child: Row(
        children: [
          Icon(
            LucideIcons.plusCircle,
            size: 18,
            color: AppColors.textTertiary,
          ),
          const SizedBox(width: AppSpacing.s3),
          Expanded(
            child: Shortcuts(
              shortcuts: const {
                SingleActivator(LogicalKeyboardKey.enter): _SubmitIntent(),
              },
              child: Actions(
                actions: {
                  _SubmitIntent: CallbackAction<_SubmitIntent>(
                    onInvoke: (_) {
                      _handleSubmit();
                      return null;
                    },
                  ),
                },
                child: TextField(
                  controller: _controller,
                  focusNode: _focusNode,
                  enabled: widget.enabled,
                  style: AppTypography.body,
                  cursorColor: AppColors.accentPrimary,
                  decoration: InputDecoration(
                    isCollapsed: true,
                    border: InputBorder.none,
                    hintText: widget.enabled
                        ? '"이번 주 운동 추천해줘"'
                        : '응답 생성 중…',
                    hintStyle: AppTypography.body.copyWith(
                      color: AppColors.textTertiary,
                    ),
                  ),
                  onChanged: (_) => setState(() {}),
                  onSubmitted: (_) => _handleSubmit(),
                ),
              ),
            ),
          ),
          const SizedBox(width: AppSpacing.s2),
          _SendButton(enabled: canSend, onTap: _handleSubmit),
        ],
      ),
    );
  }
}

class _SubmitIntent extends Intent {
  const _SubmitIntent();
}

class _SendButton extends StatelessWidget {
  const _SendButton({required this.enabled, required this.onTap});

  final bool enabled;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final color = enabled
        ? AppColors.accentSecondary
        : AppColors.accentSecondary.withValues(alpha: 0.4);

    return InkWell(
      onTap: enabled ? onTap : null,
      borderRadius: BorderRadius.circular(AppRadius.md),
      child: Container(
        width: 36,
        height: 36,
        decoration: BoxDecoration(
          color: color,
          borderRadius: BorderRadius.circular(AppRadius.md),
        ),
        child: Icon(
          LucideIcons.send,
          size: 16,
          color: AppColors.textPrimary,
        ),
      ),
    );
  }
}
