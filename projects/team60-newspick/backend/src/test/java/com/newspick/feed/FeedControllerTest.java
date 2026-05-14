package com.newspick.feed;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.context.annotation.Import;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

import com.newspick.common.CorsConfig;

import java.util.List;

import static org.mockito.BDDMockito.given;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.options;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(FeedController.class)
@Import(CorsConfig.class)
class FeedControllerTest {

    @Autowired
    MockMvc mockMvc;

    @MockitoBean
    FeedService feedService;

    @Test
    void getFeed_whenNoArticles_returnsEmptyArticlesArray() throws Exception {
        given(feedService.listFeed(List.of())).willReturn(List.of());

        mockMvc.perform(get("/api/feed"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.articles").isArray())
                .andExpect(jsonPath("$.articles.length()").value(0));
    }

    @Test
    void getFeed_withCategories_passesCategoryIdsToService() throws Exception {
        given(feedService.listFeed(List.of("tech", "economy"))).willReturn(List.of());

        mockMvc.perform(get("/api/feed").param("categories", "tech,economy"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.articles").isArray());
    }

    @Test
    void getFeed_withInvalidCategory_returnsBadRequest() throws Exception {
        mockMvc.perform(get("/api/feed").param("categories", "unknown"))
                .andExpect(status().isBadRequest());
    }

    @Test
    void getFeed_allowsLocalFrontendCorsOrigin() throws Exception {
        mockMvc.perform(options("/api/feed")
                        .header("Origin", "http://localhost:3000")
                        .header("Access-Control-Request-Method", "GET"))
                .andExpect(status().isOk())
                .andExpect(header().string("Access-Control-Allow-Origin", "http://localhost:3000"));
    }

    @Test
    void getFeed_allowsNetworkFrontendCorsOrigin() throws Exception {
        mockMvc.perform(options("/api/feed")
                        .header("Origin", "http://118.32.150.169:3000")
                        .header("Access-Control-Request-Method", "GET"))
                .andExpect(status().isOk())
                .andExpect(header().string("Access-Control-Allow-Origin", "http://118.32.150.169:3000"));
    }
}
