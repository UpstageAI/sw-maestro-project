import 'package:flutter/material.dart';

class AppColors {
  const AppColors._();

  // Background
  static const Color bgBase = Color(0xFF0A0F1E);
  static const Color bgElevated1 = Color(0xFF101730);
  static const Color bgElevated2 = Color(0xFF162041);
  static const Color bgOverlay = Color(0xCC0A0F1E);

  // Brand / Accent
  static const Color accentPrimary = Color(0xFF4FC3F7);
  static const Color accentPrimaryGlow = Color(0x664FC3F7);
  static const Color accentSecondary = Color(0xFF7B61FF);
  static const Color accentSecondaryGlow = Color(0x667B61FF);

  // Text
  static const Color textPrimary = Color(0xFFFFFFFF);
  static const Color textSecondary = Color(0xFFB8C2D9);
  static const Color textTertiary = Color(0xFF6B7794);
  static const Color textOnAccent = Color(0xFF0A0F1E);

  // Border / Divider
  static const Color borderSubtle = Color(0xFF1F2A4A);
  static const Color borderEmphasis = Color(0xFF4FC3F7);
  static const Color divider = Color(0xFF1A2240);

  // Semantic
  static const Color statusSuccess = Color(0xFF4ADE80);
  static const Color statusSuccessBg = Color(0x1F4ADE80);
  static const Color statusWarning = Color(0xFFFBBF24);
  static const Color statusWarningBg = Color(0x1FFBBF24);
  static const Color statusDanger = Color(0xFFF87171);
  static const Color statusDangerBg = Color(0x1FF87171);
  static const Color statusInfo = Color(0xFF4FC3F7);

  // Category
  static const Color catUpper = Color(0xFF4FC3F7);
  static const Color catLower = Color(0xFFA78BFA);
  static const Color catCore = Color(0xFFF472B6);
  static const Color catCardio = Color(0xFF4ADE80);
  static const Color catRest = Color(0xFF6B7794);

  // Gradients
  static const RadialGradient pageGradient = RadialGradient(
    center: Alignment.topCenter,
    radius: 1.2,
    colors: [Color(0xFF131B36), Color(0xFF0A0F1E)],
    stops: [0.0, 0.7],
  );

  static const LinearGradient todayCardGradient = LinearGradient(
    begin: Alignment.topCenter,
    end: Alignment.bottomCenter,
    colors: [Color(0x1A4FC3F7), Color(0x084FC3F7)],
  );

  static const LinearGradient recommendGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFF162041), Color(0xFF1F2A4A)],
  );
}
