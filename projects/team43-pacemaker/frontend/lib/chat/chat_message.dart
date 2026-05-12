import 'package:flutter/foundation.dart';

import '../models/muscle_fatigue_state.dart';

enum ChatRole { user, assistant }

/// Single recommended workout slot inside a [ScheduleProposal].
///
/// Mirrors `schemas.models.WorkoutSlot`. Kept FE-local for now; if A's radar
/// chart needs it too, we can promote to `lib/models/` later.
@immutable
class WorkoutSlot {
  const WorkoutSlot({
    required this.start,
    required this.end,
    required this.type,
    required this.targetMuscles,
    required this.intensity,
    required this.rationale,
  });

  final DateTime start;
  final DateTime end;
  final String type;
  final List<String> targetMuscles;
  final int intensity;
  final String rationale;

  factory WorkoutSlot.fromJson(Map<String, dynamic> json) {
    return WorkoutSlot(
      start: DateTime.parse(json['start'] as String),
      end: DateTime.parse(json['end'] as String),
      type: json['type'] as String,
      targetMuscles: (json['target_muscles'] as List).cast<String>(),
      intensity: json['intensity'] as int,
      rationale: json['rationale'] as String? ?? '',
    );
  }
}

@immutable
class ScheduleProposal {
  const ScheduleProposal({
    required this.slots,
    required this.fatigueTimeline,
  });

  final List<WorkoutSlot> slots;
  final List<MuscleFatigueState> fatigueTimeline;

  factory ScheduleProposal.fromJson(Map<String, dynamic> json) {
    final rawSlots = (json['slots'] as List?) ?? const [];
    final rawTimeline = (json['fatigue_timeline'] as List?) ?? const [];
    return ScheduleProposal(
      slots: rawSlots
          .cast<Map<String, dynamic>>()
          .map(WorkoutSlot.fromJson)
          .toList(growable: false),
      fatigueTimeline: rawTimeline
          .cast<Map<String, dynamic>>()
          .map(MuscleFatigueState.fromJson)
          .toList(growable: false),
    );
  }
}

/// One message in the chat transcript.
///
/// Assistant messages accumulate `text` deltas as they stream in. A single
/// turn can also surface a [toolCallNote] (latest tool name) and a
/// [proposal] once the agent emits one.
class ChatMessage {
  ChatMessage({
    required this.id,
    required this.role,
    this.text = '',
    this.isStreaming = false,
    this.toolCallNote,
    this.proposal,
    this.errorMessage,
  });

  final String id;
  final ChatRole role;
  String text;
  bool isStreaming;
  String? toolCallNote;
  ScheduleProposal? proposal;
  String? errorMessage;
}
