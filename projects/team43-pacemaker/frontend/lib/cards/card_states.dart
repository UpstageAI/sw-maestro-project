import 'package:flutter/material.dart';
import 'package:lucide_icons/lucide_icons.dart';

import '../design/tokens/colors.dart';
import '../design/tokens/radius.dart';
import '../design/tokens/spacing.dart';
import '../design/tokens/typography.dart';

/// 행 형식 카드(calendar, workouts) 공용 로딩 스켈레톤.
class CardLoadingRows extends StatelessWidget {
  const CardLoadingRows({super.key, this.rows = 3, this.iconSize = 44});

  final int rows;
  final double iconSize;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        for (var i = 0; i < rows; i++)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: AppSpacing.s3),
            child: Row(
              children: [
                Container(
                  width: iconSize,
                  height: iconSize * 0.82,
                  decoration: BoxDecoration(
                    color: AppColors.bgElevated2,
                    borderRadius: BorderRadius.circular(AppRadius.md),
                  ),
                ),
                const SizedBox(width: AppSpacing.s4),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Container(
                        height: 12,
                        width: double.infinity,
                        color: AppColors.bgElevated2,
                      ),
                      const SizedBox(height: 6),
                      Container(
                        height: 10,
                        width: 80,
                        color: AppColors.bgElevated2,
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
      ],
    );
  }
}

/// 도넛 카드(health) 공용 로딩 자리표시자.
class CardLoadingDonut extends StatelessWidget {
  const CardLoadingDonut({super.key, this.size = 144});

  final double size;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: AppSpacing.s4),
      child: Container(
        width: size,
        height: size,
        decoration: const BoxDecoration(
          color: AppColors.bgElevated2,
          shape: BoxShape.circle,
        ),
      ),
    );
  }
}

/// 카드 공용 에러 상태. 재시도 콜백이 있으면 버튼 노출.
class CardErrorState extends StatelessWidget {
  const CardErrorState({
    super.key,
    required this.message,
    required this.detail,
    this.onRetry,
  });

  final String message;
  final String detail;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.s3),
      decoration: BoxDecoration(
        color: AppColors.statusDangerBg,
        borderRadius: BorderRadius.circular(AppRadius.md),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(
                LucideIcons.alertCircle,
                size: 16,
                color: AppColors.statusDanger,
              ),
              const SizedBox(width: AppSpacing.s2),
              Expanded(
                child: SelectableText(
                  message,
                  style: AppTypography.body.copyWith(
                    color: AppColors.statusDanger,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.s2),
          SelectableText(
            detail,
            maxLines: 4,
            style:
                AppTypography.caption.copyWith(color: AppColors.textTertiary),
          ),
          if (onRetry != null) ...[
            const SizedBox(height: AppSpacing.s2),
            Align(
              alignment: Alignment.centerRight,
              child: TextButton.icon(
                onPressed: onRetry,
                icon: const Icon(LucideIcons.refreshCw, size: 14),
                label: const Text('다시 시도'),
                style: TextButton.styleFrom(
                  foregroundColor: AppColors.statusDanger,
                  padding: const EdgeInsets.symmetric(
                    horizontal: AppSpacing.s3,
                    vertical: AppSpacing.s1,
                  ),
                  textStyle: AppTypography.caption.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                  minimumSize: const Size(0, 28),
                  tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

/// 카드 공용 빈 상태.
class CardEmptyState extends StatelessWidget {
  const CardEmptyState({
    super.key,
    required this.icon,
    required this.message,
    this.hint,
  });

  final IconData icon;
  final String message;
  final String? hint;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: AppSpacing.s4),
      child: Column(
        children: [
          Icon(icon, size: 22, color: AppColors.textTertiary),
          const SizedBox(height: AppSpacing.s2),
          Text(
            message,
            textAlign: TextAlign.center,
            style: AppTypography.body.copyWith(color: AppColors.textSecondary),
          ),
          if (hint != null) ...[
            const SizedBox(height: 2),
            Text(
              hint!,
              textAlign: TextAlign.center,
              style:
                  AppTypography.caption.copyWith(color: AppColors.textTertiary),
            ),
          ],
        ],
      ),
    );
  }
}
