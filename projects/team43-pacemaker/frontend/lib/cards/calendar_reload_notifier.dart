import 'package:flutter/foundation.dart';

/// Pub/sub channel that asks [CalendarCard] to refetch from Supabase.
///
/// Slice B's chat ProposalCard calls [bump] after inserting events into
/// `calendar_events`; the card's listener triggers a `getCalendar` reload so
/// the new rows show up without a full page refresh.
class CalendarReloadNotifier extends ChangeNotifier {
  void bump() => notifyListeners();
}
