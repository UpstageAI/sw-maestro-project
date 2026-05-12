import 'package:flutter/material.dart';

import 'colors.dart';

/// 0~5 정수 피로도 → 색상 매핑.
/// 0 = 회복(초록), 5 = 과부하(빨강). DESIGN.md 토큰만 재사용한다.
Color fatigueColor(int level) {
  final clamped = level.clamp(0, 5);
  return switch (clamped) {
    0 => AppColors.statusSuccess,
    1 => Color.lerp(
        AppColors.statusSuccess,
        AppColors.statusWarning,
        0.25,
      )!,
    2 => Color.lerp(
        AppColors.statusSuccess,
        AppColors.statusWarning,
        0.6,
      )!,
    3 => AppColors.statusWarning,
    4 => Color.lerp(
        AppColors.statusWarning,
        AppColors.statusDanger,
        0.6,
      )!,
    5 => AppColors.statusDanger,
    _ => AppColors.statusSuccess,
  };
}
