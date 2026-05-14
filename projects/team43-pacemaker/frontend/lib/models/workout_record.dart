import 'package:flutter/foundation.dart';

@immutable
class WorkoutRecord {
  const WorkoutRecord({
    this.id,
    required this.date,
    required this.type,
    required this.durationMin,
    required this.muscles,
    required this.intensity,
  });

  final int? id;
  final DateTime date;
  final String type;
  final int durationMin;
  final List<String> muscles;
  final int intensity;

  factory WorkoutRecord.fromJson(Map<String, dynamic> row) {
    return WorkoutRecord(
      id: (row['id'] as num?)?.toInt(),
      date: DateTime.parse(row['date'] as String),
      type: row['type'] as String,
      durationMin: (row['duration_min'] as num).toInt(),
      muscles: (row['muscles'] as List).cast<String>(),
      intensity: (row['intensity'] as num).toInt(),
    );
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is WorkoutRecord &&
          runtimeType == other.runtimeType &&
          id == other.id &&
          date == other.date &&
          type == other.type &&
          durationMin == other.durationMin &&
          listEquals(muscles, other.muscles) &&
          intensity == other.intensity;

  @override
  int get hashCode => Object.hash(
        id,
        date,
        type,
        durationMin,
        Object.hashAll(muscles),
        intensity,
      );
}
