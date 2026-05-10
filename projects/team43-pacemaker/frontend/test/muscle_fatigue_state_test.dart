import 'package:flutter_test/flutter_test.dart';
import 'package:exercise_planning/models/muscle_fatigue_state.dart';

void main() {
  group('MuscleFatigueState.demo', () {
    test('contains the 7 muscles agreed with agent/nodes.py _MUSCLES', () {
      final state = MuscleFatigueState.demo();

      expect(
        state.fatigue.keys.toSet(),
        {'가슴', '등', '하체', '어깨', '코어', '이두', '삼두'},
      );
    });

    test('every value is within 0..5', () {
      final state = MuscleFatigueState.demo();

      for (final v in state.fatigue.values) {
        expect(v, inInclusiveRange(0, 5));
      }
    });
  });

  group('MuscleFatigueState.demoTimeline', () {
    test('returns 7 entries with strictly increasing dates at midnight', () {
      final timeline =
          MuscleFatigueState.demoTimeline(from: DateTime(2026, 5, 8, 14, 30));

      expect(timeline, hasLength(7));
      // Dates normalized to midnight + monotonically increasing 1 day.
      for (var i = 0; i < timeline.length; i++) {
        expect(timeline[i].date, DateTime(2026, 5, 8 + i));
      }
    });

    test('every value stays clamped within 0..5 across all days', () {
      final timeline = MuscleFatigueState.demoTimeline();

      for (final state in timeline) {
        for (final v in state.fatigue.values) {
          expect(v, inInclusiveRange(0, 5),
              reason:
                  'fatigue out of range on ${state.date}: ${state.fatigue}');
        }
      }
    });

    test('keeps the same 7 muscle keys on every day', () {
      final timeline = MuscleFatigueState.demoTimeline();
      const expected = {'가슴', '등', '하체', '어깨', '코어', '이두', '삼두'};

      for (final state in timeline) {
        expect(state.fatigue.keys.toSet(), expected);
      }
    });

    test('rest day (no stimulus) reduces every muscle by 1', () {
      final timeline =
          MuscleFatigueState.demoTimeline(from: DateTime(2026, 5, 8));
      // day 3 (index 3) is a rest day per the stimulus pattern.
      final day2 = timeline[2];
      final day3 = timeline[3];

      for (final muscle in day2.fatigue.keys) {
        final before = day2.fatigue[muscle]!;
        final after = day3.fatigue[muscle]!;
        // Either decreased by 1, or already at 0 (clamped).
        if (before == 0) {
          expect(after, 0);
        } else {
          expect(after, before - 1);
        }
      }
    });

    test('first entry matches demo() distribution', () {
      final timeline =
          MuscleFatigueState.demoTimeline(from: DateTime(2026, 5, 8));
      final demo = MuscleFatigueState.demo();

      expect(timeline.first.fatigue, demo.fatigue);
    });

    test('returned list is unmodifiable', () {
      final timeline = MuscleFatigueState.demoTimeline();

      expect(
        () => timeline.add(MuscleFatigueState.demo()),
        throwsUnsupportedError,
      );
      expect(
        () => timeline.first.fatigue['가슴'] = 99,
        throwsUnsupportedError,
      );
    });
  });
}
