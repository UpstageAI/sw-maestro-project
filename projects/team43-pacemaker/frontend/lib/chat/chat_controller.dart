import 'dart:async';
import 'dart:math';

import 'package:flutter/foundation.dart';

import 'chat_chunk.dart';
import 'chat_client.dart';
import 'chat_message.dart';
import 'proposal_notifier.dart';

/// Drives the chat panel: holds the transcript, accumulates streaming deltas,
/// and persists `thread_id` across turns so multi-turn refinement (5/7) works
/// without further plumbing.
class ChatController extends ChangeNotifier {
  ChatController({ChatClient? client, ProposalNotifier? proposalNotifier})
      : _client = client ?? ChatClient(),
        _proposalNotifier = proposalNotifier,
        _threadId = _newThreadId();

  final ChatClient _client;
  final ProposalNotifier? _proposalNotifier;
  final List<ChatMessage> _messages = [];
  // Seeded per-controller so each browser session/tab gets its own LangGraph
  // checkpoint bucket. Without this, the agent falls back to "default-thread"
  // (agent/graph.py:112) and a fresh tab's first message refines whatever
  // proposal the previous user happened to leave behind.
  String _threadId;
  StreamSubscription<ChatChunk>? _activeStream;
  ChatMessage? _activeAssistant;
  int _seq = 0;
  static final _rng = Random();

  List<ChatMessage> get messages => List.unmodifiable(_messages);
  bool get isStreaming => _activeStream != null;

  Future<void> send(String text) async {
    final trimmed = text.trim();
    if (trimmed.isEmpty || isStreaming) return;

    _messages.add(ChatMessage(
      id: _nextId('u'),
      role: ChatRole.user,
      text: trimmed,
    ));
    final assistant = ChatMessage(
      id: _nextId('a'),
      role: ChatRole.assistant,
      isStreaming: true,
    );
    _messages.add(assistant);
    _activeAssistant = assistant;
    notifyListeners();

    try {
      final stream = _client.stream(message: trimmed, threadId: _threadId);
      _activeStream = stream.listen(
        _handleChunk,
        onError: (Object err) => _completeWithError(err.toString()),
        onDone: _finalizeStream,
        cancelOnError: true,
      );
    } catch (err) {
      _completeWithError(err.toString());
    }
  }

  void _handleChunk(ChatChunk chunk) {
    final assistant = _activeAssistant;
    if (assistant == null) return;

    switch (chunk.type) {
      case ChatChunkType.text:
        final delta = chunk.payload['delta'] as String? ?? '';
        if (delta.isNotEmpty) {
          assistant.text += delta;
          notifyListeners();
        }
      case ChatChunkType.toolCall:
        final name = chunk.payload['name'] as String? ?? '';
        assistant.toolCallNote = _toolLabel(name);
        notifyListeners();
      case ChatChunkType.proposal:
        final proposal = ScheduleProposal.fromJson(chunk.payload);
        assistant.proposal = proposal;
        _proposalNotifier?.update(proposal);
        notifyListeners();
      case ChatChunkType.done:
        // Server echoes back the thread_id we sent (or its fallback). Trust it
        // so any server-side rewrite stays in sync with the FE.
        final tid = chunk.payload['thread_id'] as String?;
        if (tid != null && tid.isNotEmpty) {
          _threadId = tid;
        }
      case ChatChunkType.error:
        assistant.errorMessage =
            chunk.payload['message'] as String? ?? '알 수 없는 오류';
        notifyListeners();
      case ChatChunkType.unknown:
        break;
    }
  }

  void _finalizeStream() {
    _activeAssistant?.isStreaming = false;
    _activeAssistant = null;
    _activeStream = null;
    notifyListeners();
  }

  void _completeWithError(String message) {
    final assistant = _activeAssistant;
    if (assistant != null) {
      assistant.errorMessage = message;
      assistant.isStreaming = false;
    }
    _activeAssistant = null;
    _activeStream?.cancel();
    _activeStream = null;
    notifyListeners();
  }

  /// Start a fresh conversation: clear transcript and rotate `thread_id` so
  /// the next message lands in a new LangGraph checkpoint bucket (no refine
  /// off the previous proposal).
  void resetConversation() {
    if (isStreaming) return;
    _messages.clear();
    _threadId = _newThreadId();
    notifyListeners();
  }

  String _nextId(String prefix) {
    _seq += 1;
    return '$prefix$_seq';
  }

  static String _newThreadId() {
    final micros = DateTime.now().microsecondsSinceEpoch;
    // 1 << 32 overflows to 0 on Flutter Web (JS) → Random.nextInt throws
    // RangeError. Two 30-bit picks give us 60 bits of entropy and stay safe
    // on every platform.
    final rand = (_rng.nextInt(1 << 30).toRadixString(16)) +
        _rng.nextInt(1 << 30).toRadixString(16);
    return 'fe-$micros-$rand';
  }

  static String _toolLabel(String toolName) {
    return switch (toolName) {
      'get_calendar' => '캘린더 확인 중…',
      'get_health' => '컨디션 확인 중…',
      'get_workouts' => '최근 운동 확인 중…',
      '' => '',
      _ => '$toolName 실행 중…',
    };
  }

  @override
  void dispose() {
    _activeStream?.cancel();
    _client.dispose();
    super.dispose();
  }
}
