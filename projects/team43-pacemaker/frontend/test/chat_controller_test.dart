import 'dart:async';

import 'package:exercise_planning/chat/chat_chunk.dart';
import 'package:exercise_planning/chat/chat_client.dart';
import 'package:exercise_planning/chat/chat_controller.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('ChatController multi-turn thread_id', () {
    test('first message carries a non-empty thread_id', () async {
      final fake = _FakeChatClient();
      final ctrl = ChatController(client: fake);

      await ctrl.send('hi');
      await _waitForIdle(ctrl);

      expect(fake.calls, hasLength(1));
      expect(fake.calls.single.threadId, isNotNull);
      expect(fake.calls.single.threadId, isNotEmpty);

      ctrl.dispose();
    });

    test('second message reuses the same thread_id', () async {
      final fake = _FakeChatClient();
      final ctrl = ChatController(client: fake);

      await ctrl.send('first');
      await _waitForIdle(ctrl);
      await ctrl.send('second');
      await _waitForIdle(ctrl);

      expect(fake.calls, hasLength(2));
      expect(fake.calls[1].threadId, equals(fake.calls[0].threadId));

      ctrl.dispose();
    });

    test('resetConversation rotates thread_id and clears transcript', () async {
      final fake = _FakeChatClient();
      final ctrl = ChatController(client: fake);

      await ctrl.send('first');
      await _waitForIdle(ctrl);
      ctrl.resetConversation();
      expect(ctrl.messages, isEmpty);

      await ctrl.send('after reset');
      await _waitForIdle(ctrl);

      expect(fake.calls, hasLength(2));
      expect(fake.calls[1].threadId, isNot(equals(fake.calls[0].threadId)));

      ctrl.dispose();
    });
  });
}

Future<void> _waitForIdle(ChatController ctrl) {
  if (!ctrl.isStreaming) return Future.value();
  final done = Completer<void>();
  void listener() {
    if (!ctrl.isStreaming && !done.isCompleted) {
      ctrl.removeListener(listener);
      done.complete();
    }
  }
  ctrl.addListener(listener);
  return done.future;
}

class _Call {
  _Call({required this.message, required this.threadId});
  final String message;
  final String? threadId;
}

class _FakeChatClient extends ChatClient {
  _FakeChatClient() : super(baseUrl: 'http://test.invalid');

  final List<_Call> calls = [];

  @override
  Stream<ChatChunk> stream({
    required String message,
    String? threadId,
  }) async* {
    calls.add(_Call(message: message, threadId: threadId));
    // Echo the thread_id back so the controller's `done` handler runs.
    yield ChatChunk(
      type: ChatChunkType.done,
      payload: {'thread_id': threadId ?? ''},
    );
  }

  @override
  void dispose() {}
}
