import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'chat_message.dart';

/// Broadcasts the latest [ScheduleProposal] received from the agent to any
/// listener outside the chat panel (radar card, calendar card, ...).
///
/// Kept separate from `ChatController` so the controller stays focused on the
/// transcript and multiple widgets can listen without coupling to chat state.
class ProposalNotifier extends ChangeNotifier {
  ScheduleProposal? _latest;

  // IDs of calendar_events rows we created via the "캘린더에 등록" button.
  // Persisted to localStorage so a refined turn — even after a page reload —
  // can wipe the previous registration without touching seed data or
  // user-authored events. Issue #31.
  static const _storageKey = 'proposal.registeredEventIds.v1';
  final List<int> _registeredEventIds = [];
  bool _restored = false;

  ScheduleProposal? get latest => _latest;

  List<int> get registeredEventIds => List.unmodifiable(_registeredEventIds);

  void update(ScheduleProposal proposal) {
    _latest = proposal;
    notifyListeners();
  }

  /// Hydrate the in-memory id set from localStorage. Idempotent — safe to call
  /// from app startup. Until this completes the getter returns an empty list,
  /// so callers that race startup will simply skip the prior-delete step.
  Future<void> restore() async {
    if (_restored) return;
    final prefs = await SharedPreferences.getInstance();
    final stored = prefs.getStringList(_storageKey) ?? const [];
    _registeredEventIds
      ..clear()
      ..addAll(stored.map(int.tryParse).whereType<int>());
    _restored = true;
  }

  /// Replace the tracked id set after a successful registration cycle.
  /// Caller is responsible for having deleted the previous ids (if any) in
  /// Supabase before calling this.
  Future<void> recordRegisteredIds(List<int> ids) async {
    _registeredEventIds
      ..clear()
      ..addAll(ids);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setStringList(
      _storageKey,
      ids.map((e) => e.toString()).toList(growable: false),
    );
  }
}
