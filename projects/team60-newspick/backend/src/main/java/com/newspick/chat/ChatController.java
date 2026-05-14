package com.newspick.chat;

import com.newspick.ai.PythonChatClient;
import com.newspick.common.ApiErrorResponse;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.http.codec.ServerSentEvent;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import reactor.core.publisher.Flux;

@RestController
@RequestMapping("/api")
public class ChatController {

    private static final int MAX_MESSAGE_LENGTH = 500;
    private static final String INVALID_CHAT_MESSAGE = "INVALID_CHAT_MESSAGE";
    private static final String CHAT_STREAM_FAILED_DATA = """
            {"code":"CHAT_STREAM_FAILED","message":"답변 생성에 실패했습니다."}
            """.trim();

    private final PythonChatClient pythonChatClient;

    public ChatController(PythonChatClient pythonChatClient) {
        this.pythonChatClient = pythonChatClient;
    }

    @GetMapping(value = "/chat-stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public Flux<ServerSentEvent<String>> chatStream(@RequestParam(value = "q", required = false) String q) {
        String message = q == null ? "" : q.trim();
        if (message.isEmpty() || message.length() > MAX_MESSAGE_LENGTH) {
            throw new InvalidChatRequestException();
        }

        try {
            return pythonChatClient.chatStream(new ChatRequest(message))
                    .onErrorResume(this::errorEvent);
        } catch (RuntimeException ex) {
            return errorEvent(ex);
        }
    }

    @ExceptionHandler(InvalidChatRequestException.class)
    public ResponseEntity<ApiErrorResponse> handleInvalidChatRequest() {
        return ResponseEntity.badRequest()
                .contentType(MediaType.APPLICATION_JSON)
                .body(new ApiErrorResponse(INVALID_CHAT_MESSAGE, "채팅 메시지를 확인해 주세요."));
    }

    private Flux<ServerSentEvent<String>> errorEvent(Throwable ex) {
        return Flux.just(ServerSentEvent.<String>builder()
                .event("error")
                .data(CHAT_STREAM_FAILED_DATA)
                .build());
    }

    private static class InvalidChatRequestException extends RuntimeException {
    }
}
