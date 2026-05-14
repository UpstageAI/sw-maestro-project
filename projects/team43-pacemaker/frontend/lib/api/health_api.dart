import 'package:supabase_flutter/supabase_flutter.dart';

import '../models/health_snapshot.dart';

class HealthApi {
  const HealthApi(this._client);

  final SupabaseClient _client;

  Future<List<HealthSnapshot>> getHealth(
    DateTime startDate,
    DateTime endDate,
  ) async {
    final rows = await _client
        .from('health_snapshots')
        .select()
        .gte('date', _ymd(startDate))
        .lte('date', _ymd(endDate))
        .order('date', ascending: false);

    return rows
        .cast<Map<String, dynamic>>()
        .map(HealthSnapshot.fromJson)
        .toList(growable: false);
  }

  Future<HealthSnapshot?> getLatest() async {
    final rows = await _client
        .from('health_snapshots')
        .select()
        .order('date', ascending: false)
        .limit(1);

    if (rows.isEmpty) return null;
    return HealthSnapshot.fromJson(rows.first);
  }
}

String _ymd(DateTime d) => '${d.year.toString().padLeft(4, '0')}-'
    '${d.month.toString().padLeft(2, '0')}-'
    '${d.day.toString().padLeft(2, '0')}';
