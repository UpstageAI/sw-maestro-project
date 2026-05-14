package com.newspick.pipeline;

import com.newspick.ai.PythonAiClient;
import com.newspick.category.CategoryCatalog;
import org.springframework.http.MediaType;
import org.springframework.http.codec.ServerSentEvent;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.http.HttpStatus;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

@RestController
@RequestMapping("/api")
public class PipelineController {

    private static final String REFRESH_STREAM_FAILED_DATA = """
            {"code":"REFRESH_STREAM_FAILED","message":"뉴스 수집을 완료하지 못했습니다."}
            """.trim();

    private final PythonAiClient pythonAiClient;

    public PipelineController(PythonAiClient pythonAiClient) {
        this.pythonAiClient = pythonAiClient;
    }

    @GetMapping(value = "/refresh-stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public Flux<ServerSentEvent<String>> refreshStream(
            @RequestParam(name = "categories", required = false) String categories,
            @RequestParam(name = "runId", required = false) String runId,
            @RequestParam(name = "reset", required = false) String reset
    ) {
        return pythonAiClient.refreshStream(CategoryCatalog.parseIds(categories), runId, isReset(reset))
                .onErrorResume(this::errorEvent);
    }

    @PostMapping("/refresh-stream/{runId}/cancel")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public Mono<Void> cancelRefreshStream(@PathVariable String runId) {
        return pythonAiClient.cancelRefreshStream(runId)
                .onErrorResume(ex -> Mono.empty());
    }

    private Flux<ServerSentEvent<String>> errorEvent(Throwable ex) {
        return Flux.just(ServerSentEvent.<String>builder()
                .event("error")
                .data(REFRESH_STREAM_FAILED_DATA)
                .build());
    }

    private boolean isReset(String reset) {
        return "1".equals(reset) || "true".equalsIgnoreCase(reset);
    }
}
