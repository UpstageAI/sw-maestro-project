package com.newspick.ai;

import com.github.tomakehurst.wiremock.WireMockServer;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.codec.ServerSentEvent;

import java.time.Duration;
import java.util.List;

import static com.github.tomakehurst.wiremock.client.WireMock.aResponse;
import static com.github.tomakehurst.wiremock.client.WireMock.equalTo;
import static com.github.tomakehurst.wiremock.client.WireMock.get;
import static com.github.tomakehurst.wiremock.client.WireMock.post;
import static com.github.tomakehurst.wiremock.client.WireMock.urlPathEqualTo;
import static com.github.tomakehurst.wiremock.client.WireMock.urlEqualTo;
import static com.github.tomakehurst.wiremock.core.WireMockConfiguration.wireMockConfig;
import static org.assertj.core.api.Assertions.assertThat;

class PythonAiClientTest {

    static WireMockServer wireMock;

    @BeforeAll
    static void startWireMock() {
        wireMock = new WireMockServer(wireMockConfig().dynamicPort());
        wireMock.start();
    }

    @AfterAll
    static void stopWireMock() {
        wireMock.stop();
    }

    @BeforeEach
    void resetWireMock() {
        wireMock.resetAll();
    }

    @Test
    void refreshStream_readsStepAndDoneEventsFromWireMock() {
        String sseBody = "event: step\ndata: {\"stage\":\"collect\"}\n\n"
                + "event: done\ndata: {\"articleIds\":[\"article_001\"]}\n\n";

        wireMock.stubFor(get(urlEqualTo("/refresh-stream"))
                .willReturn(aResponse()
                        .withStatus(200)
                        .withHeader("Content-Type", "text/event-stream")
                        .withHeader("Cache-Control", "no-cache")
                        .withBody(sseBody)));

        PythonAiClient client = new PythonAiClient(new PythonAiProperties(wireMock.baseUrl()));

        List<ServerSentEvent<String>> events = client.refreshStream()
                .take(2)
                .collectList()
                .block(Duration.ofSeconds(2));

        assertThat(events).isNotNull().hasSize(2);
        assertThat(events.get(0).event()).isEqualTo("step");
        assertThat(events.get(0).data()).contains("collect");
        assertThat(events.get(events.size() - 1).event()).isEqualTo("done");
        assertThat(events.get(events.size() - 1).data()).contains("article_001");
    }

    @Test
    void refreshStream_sendsSelectedCategoryQuery() {
        String sseBody = "event: done\ndata: {\"articleIds\":[]}\n\n";

        wireMock.stubFor(get(urlPathEqualTo("/refresh-stream"))
                .withQueryParam("categories", equalTo("tech,economy"))
                .willReturn(aResponse()
                        .withStatus(200)
                        .withHeader("Content-Type", "text/event-stream")
                        .withBody(sseBody)));

        PythonAiClient client = new PythonAiClient(new PythonAiProperties(wireMock.baseUrl()));

        List<ServerSentEvent<String>> events = client.refreshStream(List.of("tech", "economy"))
                .take(1)
                .collectList()
                .block(Duration.ofSeconds(2));

        assertThat(events).isNotNull().hasSize(1);
        assertThat(events.get(0).event()).isEqualTo("done");
    }

    @Test
    void refreshStream_sendsRunIdQuery() {
        String sseBody = "event: done\ndata: {\"articleIds\":[]}\n\n";

        wireMock.stubFor(get(urlPathEqualTo("/refresh-stream"))
                .withQueryParam("runId", equalTo("run-123"))
                .willReturn(aResponse()
                        .withStatus(200)
                        .withHeader("Content-Type", "text/event-stream")
                        .withBody(sseBody)));

        PythonAiClient client = new PythonAiClient(new PythonAiProperties(wireMock.baseUrl()));

        List<ServerSentEvent<String>> events = client.refreshStream(List.of(), "run-123")
                .take(1)
                .collectList()
                .block(Duration.ofSeconds(2));

        assertThat(events).isNotNull().hasSize(1);
        assertThat(events.get(0).event()).isEqualTo("done");
    }

    @Test
    void refreshStream_sendsResetQuery() {
        String sseBody = "event: done\ndata: {\"articleIds\":[]}\n\n";

        wireMock.stubFor(get(urlPathEqualTo("/refresh-stream"))
                .withQueryParam("categories", equalTo("tech"))
                .withQueryParam("runId", equalTo("run-123"))
                .withQueryParam("reset", equalTo("1"))
                .willReturn(aResponse()
                        .withStatus(200)
                        .withHeader("Content-Type", "text/event-stream")
                        .withBody(sseBody)));

        PythonAiClient client = new PythonAiClient(new PythonAiProperties(wireMock.baseUrl()));

        List<ServerSentEvent<String>> events = client.refreshStream(List.of("tech"), "run-123", true)
                .take(1)
                .collectList()
                .block(Duration.ofSeconds(2));

        assertThat(events).isNotNull().hasSize(1);
        assertThat(events.get(0).event()).isEqualTo("done");
    }

    @Test
    void cancelRefreshStream_postsCancelRequest() {
        wireMock.stubFor(post(urlEqualTo("/refresh-stream/run-123/cancel"))
                .willReturn(aResponse().withStatus(204)));

        PythonAiClient client = new PythonAiClient(new PythonAiProperties(wireMock.baseUrl()));

        client.cancelRefreshStream("run-123").block(Duration.ofSeconds(2));
    }
}
