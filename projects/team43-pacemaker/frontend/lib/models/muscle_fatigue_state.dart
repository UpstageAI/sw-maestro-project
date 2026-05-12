import 'package:flutter/foundation.dart';

@immutable
class MuscleFatigueState {
  const MuscleFatigueState({required this.date, required this.fatigue});

  final DateTime date;
  final Map<String, int> fatigue;

  // 데모용 더미. 키 순서·이름은 agent/nodes.py:15 의 `_MUSCLES` 와 일치.
  // 5/8 통합 시 C agent SSE proposal 청크 출력으로 대체.
  factory MuscleFatigueState.demo() => MuscleFatigueState(
        date: DateTime.now(),
        fatigue: const {
          '가슴': 3,
          '등': 2,
          '하체': 1,
          '어깨': 4,
          '코어': 3,
          '이두': 2,
          '삼두': 2,
        },
      );

  // 7일치 timeline 더미 — `ScheduleProposal.fatigueTimeline` 도착 전까지 레이더가
  // "변화하는 데이터"를 보여주는 fallback. 운동일에는 해당 부위 +1~2, 휴식일에는
  // 전체 -1 (clamp 0~5). C agent proposal 도착 시 첫 항목(today) 기준으로 교체.
  static List<MuscleFatigueState> demoTimeline({DateTime? from}) {
    final start = from ?? DateTime.now();
    // 오늘 = demo() 와 동일한 분포로 시작.
    final base = <String, int>{
      '가슴': 3,
      '등': 2,
      '하체': 1,
      '어깨': 4,
      '코어': 3,
      '이두': 2,
      '삼두': 2,
    };
    // 부위 자극 패턴 — 운동일에 해당 부위에 부하 추가.
    const stimulusByDay = <Map<String, int>>[
      {}, // day 0: today (베이스 그대로)
      {'가슴': 2, '삼두': 1}, // day 1: 푸시 데이
      {'등': 2, '이두': 1}, // day 2: 풀 데이
      {}, // day 3: 휴식 → 전체 -1
      {'하체': 2, '코어': 1}, // day 4: 레그
      {'어깨': 1, '코어': 1}, // day 5: 가벼운 어깨
      {}, // day 6: 휴식
    ];
    final timeline = <MuscleFatigueState>[];
    var current = Map<String, int>.from(base);
    for (var i = 0; i < stimulusByDay.length; i++) {
      final stim = stimulusByDay[i];
      if (i == 0) {
        timeline.add(MuscleFatigueState(
          date: _atMidnight(start),
          fatigue: Map<String, int>.unmodifiable(current),
        ));
        continue;
      }
      // 휴식일(자극 없음) → 전체 -1, 운동일 → 자극된 부위만 +.
      final next = <String, int>{};
      if (stim.isEmpty) {
        for (final entry in current.entries) {
          next[entry.key] = (entry.value - 1).clamp(0, 5);
        }
      } else {
        for (final entry in current.entries) {
          final delta = stim[entry.key] ?? 0;
          next[entry.key] = (entry.value + delta).clamp(0, 5);
        }
      }
      timeline.add(MuscleFatigueState(
        date: _atMidnight(start.add(Duration(days: i))),
        fatigue: Map<String, int>.unmodifiable(next),
      ));
      current = next;
    }
    return List<MuscleFatigueState>.unmodifiable(timeline);
  }

  factory MuscleFatigueState.fromJson(Map<String, dynamic> row) {
    final raw = (row['fatigue'] as Map).cast<String, dynamic>();
    return MuscleFatigueState(
      date: DateTime.parse(row['date'] as String),
      fatigue: raw.map((k, v) => MapEntry(k, (v as num).toInt())),
    );
  }

  static DateTime _atMidnight(DateTime dt) =>
      DateTime(dt.year, dt.month, dt.day);

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is MuscleFatigueState &&
          runtimeType == other.runtimeType &&
          date == other.date &&
          mapEquals(fatigue, other.fatigue);

  @override
  int get hashCode =>
      Object.hash(date, Object.hashAllUnordered(fatigue.entries));
}
