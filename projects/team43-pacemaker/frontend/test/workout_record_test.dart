import 'package:exercise_planning/models/workout_record.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('WorkoutRecord.fromJson', () {
    test('maps snake_case columns and Postgres text[] muscles', () {
      final record = WorkoutRecord.fromJson(const {
        'date': '2026-05-04',
        'type': '헬스',
        'duration_min': 55,
        'muscles': ['어깨', '삼두'],
        'intensity': 3,
      });

      expect(record.date, DateTime(2026, 5, 4));
      expect(record.type, '헬스');
      expect(record.durationMin, 55);
      expect(record.muscles, ['어깨', '삼두']);
      expect(record.intensity, 3);
    });

    test('accepts empty muscles list', () {
      final record = WorkoutRecord.fromJson(const {
        'date': '2026-05-03',
        'type': '러닝',
        'duration_min': 30,
        'muscles': <String>[],
        'intensity': 2,
      });

      expect(record.muscles, isEmpty);
    });

    test('two records with identical fields are equal', () {
      final a = WorkoutRecord.fromJson(const {
        'date': '2026-05-04',
        'type': '헬스',
        'duration_min': 55,
        'muscles': ['어깨', '삼두'],
        'intensity': 3,
      });
      final b = WorkoutRecord.fromJson(const {
        'date': '2026-05-04',
        'type': '헬스',
        'duration_min': 55,
        'muscles': ['어깨', '삼두'],
        'intensity': 3,
      });

      expect(a, equals(b));
      expect(a.hashCode, b.hashCode);
    });
  });
}
