package com.newspick.chat;

import com.github.tomakehurst.wiremock.WireMockServer;
import com.newspick.ai.PythonAiProperties;
import com.newspick.ai.PythonChatClient;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import org.springframework.beans.factory.annotation.Autowired;

import java.nio.charset.StandardCharsets;

import static com.github.tomakehurst.wiremock.client.WireMock.aResponse;
import static com.github.tomakehurst.wiremock.client.WireMock.equalTo;
import static com.github.tomakehurst.wiremock.client.WireMock.matchingJsonPath;
import static com.github.tomakehurst.wiremock.client.WireMock.post;
import static com.github.tomakehurst.wiremock.client.WireMock.urlEqualTo;
import static com.github.tomakehurst.wiremock.core.WireMockConfiguration.wireMockConfig;
import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.asyncDispatch;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.request;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(ChatController.class)
@Import({PythonChatClient.class, ChatLiveReadinessContractTest.PythonAiTestConfig.class})
class ChatLiveReadinessContractTest {

    static WireMockServer wireMock;

    @Autowired
    MockMvc mockMvc;

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
    void chat_proxy_contract_supports_token_done_and_error_events() throws Exception {
        String article = new String(
                getClass().getResourceAsStream("/contracts/article-card-summary.valid.json").readAllBytes(),
                StandardCharsets.UTF_8
        ).replace("\r\n", "\n").replace("\n", "");

        wireMock.stubFor(post(urlEqualTo("/chat-stream"))
                .withRequestBody(matchingJsonPath("$.message", equalTo("success")))
                .willReturn(aResponse()
                        .withStatus(200)
                        .withHeader("Content-Type", "text/event-stream")
                        .withBody("event: token\ndata: {\"text\":\"답변\"}\n\n"
                                + "event: done\ndata: {\"articles\":[" + article + "]}\n\n")));

        wireMock.stubFor(post(urlEqualTo("/chat-stream"))
                .withRequestBody(matchingJsonPath("$.message", equalTo("fail")))
                .willReturn(aResponse()
                        .withStatus(500)
                        .withHeader("Content-Type", "application/json")
                        .withBody("{\"code\":\"PYTHON_FAILED\"}")));

        String successBody = postChat("success");

        assertThat(successBody).containsPattern("event\\s*:\\s*token");
        assertThat(successBody).containsPattern("event\\s*:\\s*done");
        assertThat(successBody).contains("\"id\":\"article_001\"");
        assertThat(successBody).contains("\"title\":\"AI 에이전트 확산\"");
        assertThat(successBody).contains("\"source\":\"Example\"");
        assertThat(successBody).contains("\"publishedAt\":\"2026-05-12T00:00:00Z\"");

        String errorBody = postChat("fail");

        assertThat(errorBody).containsPattern("event\\s*:\\s*error");
        assertThat(errorBody).contains("\"code\":\"CHAT_STREAM_FAILED\"");
    }

    private String postChat(String message) throws Exception {
        MvcResult result = mockMvc.perform(
                        org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get("/api/chat-stream")
                        .param("q", message))
                .andExpect(request().asyncStarted())
                .andReturn();

        return mockMvc.perform(asyncDispatch(result))
                .andExpect(status().isOk())
                .andExpect(content().contentTypeCompatibleWith(MediaType.TEXT_EVENT_STREAM))
                .andReturn()
                .getResponse()
                .getContentAsString(StandardCharsets.UTF_8);
    }

    @TestConfiguration
    static class PythonAiTestConfig {

        @Bean
        PythonAiProperties pythonAiProperties() {
            return new PythonAiProperties(wireMock.baseUrl());
        }
    }
}
