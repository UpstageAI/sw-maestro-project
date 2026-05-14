import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

import '../env.dart';
import 'chat_chunk.dart';

/// SSE client for `POST /agent/chat`.
///
/// Flutter Web's `EventSource` only supports GET; the agent endpoint is POST,
/// so we drive the stream manually via `http.Client.send` and parse
/// `data: <json>\n\n` frames as they arrive.
class ChatClient {
  ChatClient({
    http.Client? httpClient,
    String? baseUrl,
    int maxConnectRetries = 2,
    Duration initialBackoff = const Duration(milliseconds: 250),
  })  : _http = httpClient ?? http.Client(),
        _baseUrl = baseUrl ?? Env.backendBaseUrl,
        _maxConnectRetries = maxConnectRetries,
        _initialBackoff = initialBackoff;

  final http.Client _http;
  final String _baseUrl;
  // Retries cover the connect-time window only (DNS/refused/5xx before any
  // chunk arrives). Once the SSE body starts, mid-stream drops surface as a
  // truncated transcript — re-sending the same message would risk duplicate
  // tool calls and a second proposal.
  final int _maxConnectRetries;
  final Duration _initialBackoff;

  /// Open a stream and yield [ChatChunk] as the server emits them.
  ///
  /// Throws on transport failure (non-2xx, network). Logical errors from the
  /// agent arrive as `ChatChunkType.error` chunks instead.
  Stream<ChatChunk> stream({
    required String message,
    String? threadId,
  }) async* {
    final uri = Uri.parse('$_baseUrl/agent/chat');
    final body = jsonEncode({
      'message': message,
      if (threadId != null) 'thread_id': threadId,
    });

    final response = await _connectWithRetry(uri, body);

    // sse-starlette emits `data: <json>\n\n`. Comments (`: ping`) and unknown
    // headers are ignored. Frames are delimited by a blank line.
    final lines = response.stream
        .transform(utf8.decoder)
        .transform(const LineSplitter());

    final dataBuffer = StringBuffer();
    await for (final line in lines) {
      if (line.isEmpty) {
        final raw = dataBuffer.toString();
        dataBuffer.clear();
        if (raw.isEmpty) continue;
        final decoded = jsonDecode(raw);
        if (decoded is Map<String, dynamic>) {
          yield ChatChunk.fromJson(decoded);
        }
      } else if (line.startsWith('data:')) {
        final value = line.substring(5);
        dataBuffer.write(value.startsWith(' ') ? value.substring(1) : value);
      }
      // Ignore `event:`, `id:`, `:`-prefixed comments.
    }

    // Flush any trailing frame that wasn't terminated by a blank line.
    final tail = dataBuffer.toString();
    if (tail.isNotEmpty) {
      final decoded = jsonDecode(tail);
      if (decoded is Map<String, dynamic>) {
        yield ChatChunk.fromJson(decoded);
      }
    }
  }

  Future<http.StreamedResponse> _connectWithRetry(Uri uri, String body) async {
    Object? lastError;
    for (var attempt = 0; attempt <= _maxConnectRetries; attempt++) {
      if (attempt > 0) {
        await Future<void>.delayed(_initialBackoff * (1 << (attempt - 1)));
      }
      try {
        final request = http.Request('POST', uri)
          ..headers['Content-Type'] = 'application/json'
          ..headers['Accept'] = 'text/event-stream'
          ..body = body;

        final response = await _http.send(request);
        if (response.statusCode == 200) return response;

        // 4xx are usually our fault (bad payload) — don't burn retries on
        // them. 5xx and 408/429 plausibly recover.
        final code = response.statusCode;
        final retriable = code >= 500 || code == 408 || code == 429;
        final errBody = await response.stream.bytesToString();
        lastError = ChatTransportException('agent/chat $code: $errBody');
        if (!retriable) throw lastError;
      } on ChatTransportException {
        rethrow;
      } catch (e) {
        lastError = e;
      }
    }
    if (lastError is Exception) throw lastError;
    throw ChatTransportException('agent/chat connect failed: $lastError');
  }

  void dispose() => _http.close();
}

class ChatTransportException implements Exception {
  ChatTransportException(this.message);
  final String message;
  @override
  String toString() => 'ChatTransportException: $message';
}
