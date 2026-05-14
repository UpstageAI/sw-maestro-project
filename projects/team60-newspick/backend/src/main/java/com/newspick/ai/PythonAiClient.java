package com.newspick.ai;

import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.codec.ServerSentEvent;
import org.springframework.http.client.reactive.ReactorClientHttpConnector;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;
import reactor.netty.http.client.HttpClient;

import java.util.List;

@Component
public class PythonAiClient {

    private final WebClient webClient;
    private final PythonAiProperties properties;

    public PythonAiClient(PythonAiProperties properties) {
        this.properties = properties;
        HttpClient httpClient = HttpClient.create()
                .responseTimeout(properties.timeout());
        this.webClient = WebClient.builder()
                .clientConnector(new ReactorClientHttpConnector(httpClient))
                .baseUrl(properties.baseUrl())
                .build();
    }

    public Flux<ServerSentEvent<String>> refreshStream() {
        return refreshStream(List.of());
    }

    public Flux<ServerSentEvent<String>> refreshStream(List<String> categoryIds) {
        return refreshStream(categoryIds, null, false);
    }

    public Flux<ServerSentEvent<String>> refreshStream(List<String> categoryIds, String runId) {
        return refreshStream(categoryIds, runId, false);
    }

    public Flux<ServerSentEvent<String>> refreshStream(
            List<String> categoryIds,
            String runId,
            boolean reset
    ) {
        return webClient.get()
                .uri(uriBuilder -> {
                    var builder = uriBuilder.path("/refresh-stream");
                    if (!categoryIds.isEmpty()) {
                        builder.queryParam("categories", String.join(",", categoryIds));
                    }
                    if (runId != null && !runId.isBlank()) {
                        builder.queryParam("runId", runId);
                    }
                    if (reset) {
                        builder.queryParam("reset", "1");
                    }
                    return builder.build();
                })
                .retrieve()
                .bodyToFlux(new ParameterizedTypeReference<ServerSentEvent<String>>() {})
                .timeout(properties.timeout());
    }

    public Mono<Void> cancelRefreshStream(String runId) {
        if (runId == null || runId.isBlank()) {
            return Mono.empty();
        }

        return webClient.post()
                .uri("/refresh-stream/{runId}/cancel", runId)
                .retrieve()
                .toBodilessEntity()
                .timeout(properties.timeout())
                .then();
    }
}
