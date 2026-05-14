package com.newspick.ai;

import com.github.tomakehurst.wiremock.WireMockServer;
import com.newspick.chat.ChatRequest;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.codec.ServerSentEvent;

import java.time.Duration;
import java.util.List;

import static com.github.tomakehurst.wiremock.client.WireMock.aResponse;
import static com.github.tomakehurst.wiremock.client.WireMock.matchingJsonPath;
import static com.github.tomakehurst.wiremock.client.WireMock.post;
import static com.github.tomakehurst.wiremock.client.WireMock.urlEqualTo;
import static com.github.tomakehurst.wiremock.core.WireMockConfiguration.wireMockConfig;
import static org.assertj.core.api.Assertions.assertThat;

class PythonChatClientTest {

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
    void chatStream_posts_message_and_reads_token_event() {
        String sseBody = "event: token\ndata: {\"text\":\"안녕하세요\"}\n\n";

        wireMock.stubFor(post(urlEqualTo("/chat-stream"))
                .withRequestBody(matchingJsonPath("$.message", com.github.tomakehurst.wiremock.client.WireMock.equalTo("오늘 뉴스")))
                .willReturn(aResponse()
                        .withStatus(200)
                        .withHeader("Content-Type", "text/event-stream")
                        .withHeader("Cache-Control", "no-cache")
                        .withBody(sseBody)));

        PythonChatClient client = new PythonChatClient(new PythonAiProperties(wireMock.baseUrl()));

        List<ServerSentEvent<String>> events = client.chatStream(new ChatRequest("오늘 뉴스"))
                .take(1)
                .collectList()
                .block(Duration.ofSeconds(2));

        assertThat(events).isNotNull().hasSize(1);
        assertThat(events.get(0).event()).isEqualTo("token");
        assertThat(events.get(0).data()).contains("안녕하세요");
    }
}
