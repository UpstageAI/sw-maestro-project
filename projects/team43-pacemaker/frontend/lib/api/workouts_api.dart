import 'package:supabase_flutter/supabase_flutter.dart';

import '../models/workout_record.dart';

class WorkoutsApi {
  const WorkoutsApi(this._client);

  final SupabaseClient _client;

  Future<List<WorkoutRecord>> getRecent({int limit = 5}) async {
    final rows = await _client
        .from('workout_records')
        .select()
        .order('date', ascending: false)
        .limit(limit);

    return rows
        .cast<Map<String, dynamic>>()
        .map(WorkoutRecord.fromJson)
        .toList(growable: false);
  }
}
