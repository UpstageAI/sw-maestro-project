package com.newspick.pipeline;

import com.newspick.ai.PythonAiClient;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.http.MediaType;
import org.springframework.http.codec.ServerSentEvent;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.asyncDispatch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.request;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(PipelineController.class)
class PipelineControllerTest {

    @Autowired
    MockMvc mockMvc;

    @MockitoBean
    PythonAiClient pythonAiClient;

    @Test
    void refreshStream_proxiesStepAndDoneEvents() throws Exception {
        when(pythonAiClient.refreshStream(java.util.List.of(), null, false)).thenReturn(Flux.just(
                ServerSentEvent.<String>builder()
                        .event("step")
                        .data("{\"step\":\"summarize\",\"current\":1,\"total\":2}")
                        .build(),
                ServerSentEvent.<String>builder()
                        .event("done")
                        .data("{\"articleIds\":[\"article_001\"]}")
                        .build()
        ));

        MvcResult result = mockMvc.perform(get("/api/refresh-stream"))
                .andExpect(request().asyncStarted())
                .andReturn();

        String body = mockMvc.perform(asyncDispatch(result))
                .andExpect(status().isOk())
                .andExpect(content().contentTypeCompatibleWith(MediaType.TEXT_EVENT_STREAM))
                .andReturn()
                .getResponse()
                .getContentAsString();

        assertThat(body).containsPattern("event\\s*:\\s*step");
        assertThat(body).contains("summarize");
        assertThat(body).containsPattern("event\\s*:\\s*done");
        assertThat(body).contains("article_001");
    }

    @Test
    void refreshStream_passesCategoriesAndRunIdToAiClient() throws Exception {
        when(pythonAiClient.refreshStream(java.util.List.of("tech"), "run-123", false)).thenReturn(Flux.just(
                ServerSentEvent.<String>builder()
                        .event("done")
                        .data("{\"articleIds\":[]}")
                        .build()
        ));

        MvcResult result = mockMvc.perform(
                        get("/api/refresh-stream")
                                .param("categories", "tech")
                                .param("runId", "run-123"))
                .andExpect(request().asyncStarted())
                .andReturn();

        mockMvc.perform(asyncDispatch(result))
                .andExpect(status().isOk());

        verify(pythonAiClient).refreshStream(java.util.List.of("tech"), "run-123", false);
    }

    @Test
    void refreshStream_passesResetFlagToAiClient() throws Exception {
        when(pythonAiClient.refreshStream(java.util.List.of("tech"), "run-123", true)).thenReturn(Flux.just(
                ServerSentEvent.<String>builder()
                        .event("done")
                        .data("{\"articleIds\":[]}")
                        .build()
        ));

        MvcResult result = mockMvc.perform(
                        get("/api/refresh-stream")
                                .param("categories", "tech")
                                .param("runId", "run-123")
                                .param("reset", "1"))
                .andExpect(request().asyncStarted())
                .andReturn();

        mockMvc.perform(asyncDispatch(result))
                .andExpect(status().isOk());

        verify(pythonAiClient).refreshStream(java.util.List.of("tech"), "run-123", true);
    }

    @Test
    void refreshStream_whenPythonFails_emitsJsonErrorEvent() throws Exception {
        when(pythonAiClient.refreshStream(java.util.List.of(), null, false))
                .thenReturn(Flux.error(new RuntimeException("boom")));

        MvcResult result = mockMvc.perform(get("/api/refresh-stream"))
                .andExpect(request().asyncStarted())
                .andReturn();

        String body = mockMvc.perform(asyncDispatch(result))
                .andExpect(status().isOk())
                .andExpect(content().contentTypeCompatibleWith(MediaType.TEXT_EVENT_STREAM))
                .andReturn()
                .getResponse()
                .getContentAsString();

        assertThat(body).containsPattern("event\\s*:\\s*error");
        assertThat(body).contains("\"code\":\"REFRESH_STREAM_FAILED\"");
        assertThat(body).contains("\"message\"");
        assertThat(body).doesNotContain("RuntimeException");
    }

    @Test
    void cancelRefreshStream_proxiesCancelToAiClient() throws Exception {
        when(pythonAiClient.cancelRefreshStream("run-123")).thenReturn(Mono.empty());

        mockMvc.perform(post("/api/refresh-stream/run-123/cancel"))
                .andExpect(status().isNoContent());

        verify(pythonAiClient).cancelRefreshStream("run-123");
    }

    @Test
    void refreshStream_withInvalidCategory_returnsBadRequest() throws Exception {
        mockMvc.perform(get("/api/refresh-stream").param("categories", "unknown"))
                .andExpect(status().isBadRequest());
    }
}
