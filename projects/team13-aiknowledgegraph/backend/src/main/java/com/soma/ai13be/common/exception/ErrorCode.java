package com.soma.ai13be.common.exception;

import org.springframework.http.HttpStatus;

import lombok.Getter;
import lombok.RequiredArgsConstructor;

@Getter
@RequiredArgsConstructor
public enum ErrorCode {

	INVALID_REQUEST(HttpStatus.BAD_REQUEST, "Invalid request"),
	DUPLICATE_PERSONA(HttpStatus.CONFLICT, "Persona already exists"),
	PERSONA_PROMPT_GENERATION_FAILED(HttpStatus.BAD_GATEWAY, "Failed to generate persona prompt"),
	PERSONA_NOT_FOUND(HttpStatus.NOT_FOUND, "Persona not found"),
	BUILT_IN_PERSONA_DELETION(HttpStatus.CONFLICT, "Built-in persona cannot be deleted"),
	KNOWLEDGE_NODE_NOT_FOUND(HttpStatus.NOT_FOUND, "Knowledge node not found"),
	KNOWLEDGE_EXTRACTION_FAILED(HttpStatus.BAD_GATEWAY, "Failed to extract knowledge"),
	CHAT_SESSION_NOT_FOUND(HttpStatus.NOT_FOUND, "Chat session not found"),
	DISCUSSION_NOT_FOUND(HttpStatus.NOT_FOUND, "Discussion not found"),
	SOLAR_RESPONSE_EMPTY(HttpStatus.BAD_GATEWAY, "Solar API returned empty response"),
	INTERNAL_SERVER_ERROR(HttpStatus.INTERNAL_SERVER_ERROR, "Internal server error");

	private final HttpStatus status;
	private final String message;
}
