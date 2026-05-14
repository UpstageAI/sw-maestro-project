import 'package:flutter/material.dart';

import 'colors.dart';

class AppShadows {
  const AppShadows._();

  static const List<BoxShadow> card = [
    BoxShadow(
      color: Color(0x08FFFFFF),
      offset: Offset(0, 1),
      blurRadius: 0,
      spreadRadius: 0,
    ),
    BoxShadow(
      color: Color(0x40000000),
      offset: Offset(0, 8),
      blurRadius: 24,
    ),
  ];

  static const List<BoxShadow> glowCyan = [
    BoxShadow(
      color: Color(0x404FC3F7),
      blurRadius: 0,
      spreadRadius: 1,
    ),
    BoxShadow(
      color: Color(0x334FC3F7),
      blurRadius: 24,
      spreadRadius: 0,
    ),
  ];

  static const List<BoxShadow> glowViolet = [
    BoxShadow(
      color: Color(0x407B61FF),
      blurRadius: 0,
      spreadRadius: 1,
    ),
    BoxShadow(
      color: Color(0x337B61FF),
      blurRadius: 24,
      spreadRadius: 0,
    ),
  ];

  static const List<BoxShadow> focusRing = [
    BoxShadow(
      color: AppColors.accentPrimaryGlow,
      blurRadius: 0,
      spreadRadius: 3,
    ),
  ];
}
