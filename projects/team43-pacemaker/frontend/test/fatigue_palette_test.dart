import 'package:exercise_planning/design/tokens/colors.dart';
import 'package:exercise_planning/design/tokens/fatigue_palette.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('fatigueColor', () {
    test('0 maps to statusSuccess (green)', () {
      expect(fatigueColor(0), AppColors.statusSuccess);
    });

    test('3 maps to statusWarning (yellow)', () {
      expect(fatigueColor(3), AppColors.statusWarning);
    });

    test('5 maps to statusDanger (red)', () {
      expect(fatigueColor(5), AppColors.statusDanger);
    });

    test('clamps below 0 to the level-0 color', () {
      expect(fatigueColor(-1), fatigueColor(0));
    });

    test('clamps above 5 to the level-5 color', () {
      expect(fatigueColor(99), fatigueColor(5));
    });
  });
}
