package com.newspick.chat;

import com.newspick.ai.PythonChatClient;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.http.MediaType;
import org.springframework.http.codec.ServerSentEvent;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import reactor.core.publisher.Flux;

import java.nio.charset.StandardCharsets;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.asyncDispatch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.request;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(ChatController.class)
class ChatStreamContractTest {

    @Autowired
    MockMvc mockMvc;

    @MockitoBean
    PythonChatClient pythonChatClient;

    @Test
    void chat_stream_done_articles_match_article_card_summary_contract() throws Exception {
        when(pythonChatClient.chatStream(any())).thenReturn(Flux.just(
                ServerSentEvent.<String>builder()
                        .event("token")
                        .data("{\"text\":\"오늘 \"}")
                        .build(),
                ServerSentEvent.<String>builder()
                        .event("token")
                        .data("{\"text\":\"핵심\"}")
                        .build(),
                ServerSentEvent.<String>builder()
                        .event("done")
                        .data("{\"articles\":[{\"id\":\"article_001\",\"title\":\"AI 에이전트 확산\",\"source\":\"Example\",\"publishedAt\":\"2026-05-12T00:00:00Z\"}]}")
                        .build()
        ));

        MvcResult result = mockMvc.perform(get("/api/chat-stream").param("q", "오늘 뉴스"))
                .andExpect(request().asyncStarted())
                .andReturn();

        String body = mockMvc.perform(asyncDispatch(result))
                .andExpect(status().isOk())
                .andExpect(content().contentTypeCompatibleWith(MediaType.TEXT_EVENT_STREAM))
                .andReturn()
                .getResponse()
                .getContentAsString(StandardCharsets.UTF_8);

        String expected = new String(
                getClass().getResourceAsStream("/contracts/chat-stream.fixture.sse").readAllBytes(),
                StandardCharsets.UTF_8
        );

        assertThat(normalize(body)).isEqualTo(normalize(expected));
        assertThat(body.split("event:token", -1)).hasSize(3);
        assertThat(body.split("event:done", -1)).hasSize(2);
        assertThat(body).contains("\"id\":\"article_001\"");
        assertThat(body).contains("\"title\":\"AI 에이전트 확산\"");
        assertThat(body).contains("\"source\":\"Example\"");
        assertThat(body).contains("\"publishedAt\":\"2026-05-12T00:00:00Z\"");
    }

    private String normalize(String text) {
        return text.replace("\r\n", "\n").trim();
    }
}
