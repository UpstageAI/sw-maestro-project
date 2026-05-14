import 'package:flutter/foundation.dart';

@immutable
class HealthSnapshot {
  const HealthSnapshot({
    this.id,
    required this.date,
    required this.sleepHours,
    required this.activityMinutes,
    this.restingHr,
  });

  final int? id;
  final DateTime date;
  final double sleepHours;
  final int activityMinutes;
  final int? restingHr;

  factory HealthSnapshot.fromJson(Map<String, dynamic> row) {
    return HealthSnapshot(
      id: (row['id'] as num?)?.toInt(),
      date: DateTime.parse(row['date'] as String),
      sleepHours: (row['sleep_hours'] as num).toDouble(),
      activityMinutes: (row['activity_minutes'] as num).toInt(),
      restingHr: (row['resting_hr'] as num?)?.toInt(),
    );
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is HealthSnapshot &&
          runtimeType == other.runtimeType &&
          id == other.id &&
          date == other.date &&
          sleepHours == other.sleepHours &&
          activityMinutes == other.activityMinutes &&
          restingHr == other.restingHr;

  @override
  int get hashCode =>
      Object.hash(id, date, sleepHours, activityMinutes, restingHr);
}
