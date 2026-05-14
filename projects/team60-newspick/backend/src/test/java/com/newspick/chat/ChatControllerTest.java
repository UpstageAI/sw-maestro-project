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
import static org.mockito.ArgumentCaptor.forClass;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.asyncDispatch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.request;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(ChatController.class)
class ChatControllerTest {

    @Autowired
    MockMvc mockMvc;

    @MockitoBean
    PythonChatClient pythonChatClient;

    @Test
    void chatStream_proxies_token_event() throws Exception {
        when(pythonChatClient.chatStream(any())).thenReturn(Flux.just(
                ServerSentEvent.<String>builder()
                        .event("token")
                        .data("{\"text\":\"안녕\"}")
                        .build(),
                ServerSentEvent.<String>builder()
                        .event("done")
                        .data("{\"articles\":[]}")
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

        assertThat(body).containsPattern("event\\s*:\\s*token");
        assertThat(body).contains("안녕");
        assertThat(body).containsPattern("event\\s*:\\s*done");
    }

    @Test
    void chatStream_whenPythonFails_emits_error_event() throws Exception {
        when(pythonChatClient.chatStream(any())).thenThrow(new ChatStreamException("timeout"));

        MvcResult result = mockMvc.perform(get("/api/chat-stream").param("q", "오늘 뉴스"))
                .andExpect(request().asyncStarted())
                .andReturn();

        String body = mockMvc.perform(asyncDispatch(result))
                .andExpect(status().isOk())
                .andExpect(content().contentTypeCompatibleWith(MediaType.TEXT_EVENT_STREAM))
                .andReturn()
                .getResponse()
                .getContentAsString(StandardCharsets.UTF_8);

        assertThat(body).containsPattern("event\\s*:\\s*error");
        assertThat(body).contains("\"code\":\"CHAT_STREAM_FAILED\"");
        assertThat(body).doesNotContain("ChatStreamException");
        assertThat(body).doesNotContain("at com.newspick");
    }

    @Test
    void chatStream_rejects_blank_q_and_trims_query_message() throws Exception {
        mockMvc.perform(get("/api/chat-stream").param("q", "   "))
                .andExpect(status().isBadRequest())
                .andExpect(content().contentTypeCompatibleWith(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$.code").value("INVALID_CHAT_MESSAGE"));

        mockMvc.perform(get("/api/chat-stream"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("INVALID_CHAT_MESSAGE"));

        when(pythonChatClient.chatStream(any())).thenReturn(Flux.just(
                ServerSentEvent.<String>builder()
                        .event("token")
                        .data("{\"text\":\"요약\"}")
                        .build()
        ));

        MvcResult result = mockMvc.perform(get("/api/chat-stream").param("q", " 요약해줘 "))
                .andExpect(request().asyncStarted())
                .andReturn();

        String body = mockMvc.perform(asyncDispatch(result))
                .andExpect(status().isOk())
                .andExpect(content().contentTypeCompatibleWith(MediaType.TEXT_EVENT_STREAM))
                .andReturn()
                .getResponse()
                .getContentAsString(StandardCharsets.UTF_8);

        var captor = forClass(ChatRequest.class);
        verify(pythonChatClient).chatStream(captor.capture());

        assertThat(captor.getValue().message()).isEqualTo("요약해줘");
        assertThat(captor.getValue().contextArticleIds()).isEmpty();
        assertThat(body).containsPattern("event\\s*:\\s*token");
    }
}
