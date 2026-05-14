import 'package:exercise_planning/models/health_snapshot.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('HealthSnapshot.fromJson', () {
    test('maps snake_case columns to camelCase fields', () {
      final snapshot = HealthSnapshot.fromJson(const {
        'date': '2026-05-05',
        'sleep_hours': 7.8,
        'activity_minutes': 45,
        'resting_hr': 59,
      });

      expect(snapshot.date, DateTime(2026, 5, 5));
      expect(snapshot.sleepHours, 7.8);
      expect(snapshot.activityMinutes, 45);
      expect(snapshot.restingHr, 59);
    });

    test('treats missing resting_hr as null', () {
      final snapshot = HealthSnapshot.fromJson(const {
        'date': '2026-05-05',
        'sleep_hours': 6.0,
        'activity_minutes': 30,
      });

      expect(snapshot.restingHr, isNull);
    });

    test('two snapshots with identical fields are equal', () {
      final a = HealthSnapshot.fromJson(const {
        'date': '2026-05-05',
        'sleep_hours': 7.8,
        'activity_minutes': 45,
        'resting_hr': 59,
      });
      final b = HealthSnapshot.fromJson(const {
        'date': '2026-05-05',
        'sleep_hours': 7.8,
        'activity_minutes': 45,
        'resting_hr': 59,
      });

      expect(a, equals(b));
      expect(a.hashCode, b.hashCode);
    });
  });
}
