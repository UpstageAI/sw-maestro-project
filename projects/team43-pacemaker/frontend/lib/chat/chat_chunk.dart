import 'package:flutter/foundation.dart';

/// SSE stream chunk emitted by `POST /agent/chat`.
///
/// Wire contract is locked in `schemas/CLAUDE.md`. Each chunk has a `type` and
/// a free-form `payload` map whose shape depends on type.
enum ChatChunkType {
  text,
  toolCall,
  proposal,
  done,
  error,
  unknown;

  static ChatChunkType fromWire(String raw) {
    return switch (raw) {
      'text' => ChatChunkType.text,
      'tool_call' => ChatChunkType.toolCall,
      'proposal' => ChatChunkType.proposal,
      'done' => ChatChunkType.done,
      'error' => ChatChunkType.error,
      _ => ChatChunkType.unknown,
    };
  }
}

@immutable
class ChatChunk {
  const ChatChunk({required this.type, required this.payload});

  final ChatChunkType type;
  final Map<String, dynamic> payload;

  factory ChatChunk.fromJson(Map<String, dynamic> json) {
    return ChatChunk(
      type: ChatChunkType.fromWire(json['type'] as String? ?? ''),
      payload: (json['payload'] as Map?)?.cast<String, dynamic>() ?? const {},
    );
  }
}
