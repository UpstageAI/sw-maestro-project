import 'package:exercise_planning/models/calendar_event.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('CalendarEvent.fromJson', () {
    test('maps snake_case columns to camelCase fields', () {
      final event = CalendarEvent.fromJson(const {
        'start_at': '2026-05-05T09:00:00',
        'end_at': '2026-05-05T10:00:00',
        'title': '스탠드업',
        'is_busy': true,
      });

      expect(event.startAt, DateTime(2026, 5, 5, 9));
      expect(event.endAt, DateTime(2026, 5, 5, 10));
      expect(event.title, '스탠드업');
      expect(event.isBusy, isTrue);
    });

    test('defaults is_busy to true when column is missing', () {
      final event = CalendarEvent.fromJson(const {
        'start_at': '2026-05-05T12:00:00',
        'end_at': '2026-05-05T12:30:00',
        'title': '점심',
      });

      expect(event.isBusy, isTrue);
    });

    test('respects explicit is_busy=false (free slot)', () {
      final event = CalendarEvent.fromJson(const {
        'start_at': '2026-05-05T18:00:00',
        'end_at': '2026-05-05T19:00:00',
        'title': '퇴근 후',
        'is_busy': false,
      });

      expect(event.isBusy, isFalse);
    });

    test('two events with identical fields are equal', () {
      final a = CalendarEvent.fromJson(const {
        'start_at': '2026-05-05T09:00:00',
        'end_at': '2026-05-05T10:00:00',
        'title': '스탠드업',
        'is_busy': true,
      });
      final b = CalendarEvent.fromJson(const {
        'start_at': '2026-05-05T09:00:00',
        'end_at': '2026-05-05T10:00:00',
        'title': '스탠드업',
        'is_busy': true,
      });

      expect(a, equals(b));
      expect(a.hashCode, b.hashCode);
    });
  });
}
