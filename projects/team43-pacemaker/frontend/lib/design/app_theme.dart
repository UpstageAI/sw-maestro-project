import 'package:flutter/material.dart';

import 'tokens/colors.dart';
import 'tokens/typography.dart';

ThemeData buildAppTheme() {
  final base = ThemeData.dark(useMaterial3: true);

  return base.copyWith(
    scaffoldBackgroundColor: AppColors.bgBase,
    colorScheme: const ColorScheme.dark(
      surface: AppColors.bgElevated1,
      primary: AppColors.accentPrimary,
      secondary: AppColors.accentSecondary,
      onPrimary: AppColors.textOnAccent,
      onSecondary: AppColors.textPrimary,
      onSurface: AppColors.textPrimary,
      outline: AppColors.borderSubtle,
      error: AppColors.statusDanger,
    ),
    textTheme: const TextTheme(
      displayLarge: AppTypography.display,
      headlineMedium: AppTypography.h1,
      headlineSmall: AppTypography.h2,
      titleLarge: AppTypography.h3,
      bodyLarge: AppTypography.bodyLg,
      bodyMedium: AppTypography.body,
      bodySmall: AppTypography.caption,
      labelSmall: AppTypography.overline,
    ),
    appBarTheme: const AppBarTheme(
      backgroundColor: Colors.transparent,
      foregroundColor: AppColors.textPrimary,
      elevation: 0,
      scrolledUnderElevation: 0,
      titleTextStyle: AppTypography.h2,
    ),
  );
}
