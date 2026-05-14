import 'dart:async';
import 'dart:convert';

import 'package:exercise_planning/chat/chat_chunk.dart';
import 'package:exercise_planning/chat/chat_client.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  group('ChatClient connect retry', () {
    test('retries through transient 503s and yields parsed chunks', () async {
      var attempts = 0;
      final client = MockClient.streaming((req, body) async {
        attempts += 1;
        if (attempts < 3) {
          return http.StreamedResponse(
            Stream.value(utf8.encode('upstream down')),
            503,
          );
        }
        return http.StreamedResponse(
          Stream.value(utf8.encode(
            'data: {"type":"text","payload":{"delta":"hi"}}\n\n'
            'data: {"type":"done","payload":{"thread_id":"t-1"}}\n\n',
          )),
          200,
          headers: {'content-type': 'text/event-stream'},
        );
      });

      final chat = ChatClient(
        httpClient: client,
        baseUrl: 'http://test.invalid',
        initialBackoff: const Duration(milliseconds: 1),
      );

      final chunks = await chat
          .stream(message: 'ping', threadId: 'seed')
          .toList();

      expect(attempts, 3);
      expect(chunks.map((c) => c.type), [
        ChatChunkType.text,
        ChatChunkType.done,
      ]);
    });

    test('does not retry on 4xx — surfaces the error immediately', () async {
      var attempts = 0;
      final client = MockClient.streaming((req, body) async {
        attempts += 1;
        return http.StreamedResponse(
          Stream.value(utf8.encode('bad payload')),
          400,
        );
      });

      final chat = ChatClient(
        httpClient: client,
        baseUrl: 'http://test.invalid',
        initialBackoff: const Duration(milliseconds: 1),
      );

      expect(
        () => chat.stream(message: 'x').first,
        throwsA(isA<ChatTransportException>()),
      );
      // Let the future resolve before asserting attempts.
      await pumpEventQueue();
      expect(attempts, 1);
    });

    test('gives up after maxConnectRetries and throws', () async {
      var attempts = 0;
      final client = MockClient.streaming((req, body) async {
        attempts += 1;
        throw const _FakeSocketException('connection refused');
      });

      final chat = ChatClient(
        httpClient: client,
        baseUrl: 'http://test.invalid',
        maxConnectRetries: 2,
        initialBackoff: const Duration(milliseconds: 1),
      );

      await expectLater(
        chat.stream(message: 'x').toList(),
        throwsA(isA<Exception>()),
      );
      // 1 initial + 2 retries.
      expect(attempts, 3);
    });
  });
}

/// Lightweight stand-in so the retry loop's `catch (e)` branch sees a
/// non-ChatTransportException network failure.
class _FakeSocketException implements Exception {
  const _FakeSocketException(this.message);
  final String message;
  @override
  String toString() => 'SocketException: $message';
}
