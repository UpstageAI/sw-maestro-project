package com.soma.ai13be.common.exception;

import org.springframework.http.HttpStatus;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.server.ResponseStatusException;

import com.soma.ai13be.common.dto.ErrorResponse;

/**
 * 도메인 예외를 HTTP 응답으로 변환하는 전역 예외 처리기입니다.
 * 컨트롤러는 비즈니스 예외를 직접 처리하지 않고 이 클래스에 위임합니다.
 */
@RestControllerAdvice
public class GlobalExceptionHandler {

	@ExceptionHandler(CustomException.class)
	public ResponseEntity<ErrorResponse> handleCustomException(CustomException exception) {
		ErrorCode errorCode = exception.getErrorCode();
		return ResponseEntity.status(errorCode.getStatus())
			.body(new ErrorResponse(errorCode.name(), exception.getMessage()));
	}

	@ExceptionHandler(IllegalArgumentException.class)
	public ResponseEntity<ErrorResponse> handleIllegalArgument(IllegalArgumentException exception) {
		return ResponseEntity.status(HttpStatus.BAD_REQUEST)
			.body(new ErrorResponse(ErrorCode.INVALID_REQUEST.name(), exception.getMessage()));
	}

	@ExceptionHandler(ResponseStatusException.class)
	public ResponseEntity<ErrorResponse> handleResponseStatus(ResponseStatusException exception) {
		ErrorCode errorCode = resolveErrorCode(exception.getStatusCode());
		return ResponseEntity.status(exception.getStatusCode())
			.body(new ErrorResponse(errorCode.name(), exception.getReason()));
	}

	private ErrorCode resolveErrorCode(HttpStatusCode statusCode) {
		if (statusCode.is4xxClientError()) {
			return ErrorCode.INVALID_REQUEST;
		}
		return ErrorCode.INTERNAL_SERVER_ERROR;
	}
}
