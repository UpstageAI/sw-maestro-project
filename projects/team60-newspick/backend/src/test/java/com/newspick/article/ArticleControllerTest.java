package com.newspick.article;

import org.junit.jupiter.api.Test;
import org.skyscreamer.jsonassert.JSONAssert;
import org.skyscreamer.jsonassert.JSONCompareMode;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Optional;

import static org.mockito.BDDMockito.given;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(ArticleController.class)
class ArticleControllerTest {

    @Autowired
    MockMvc mockMvc;

    @MockitoBean
    ArticleService articleService;

    @Test
    void getArticle_whenMissing_returns404JsonError() throws Exception {
        given(articleService.getById("missing-id")).willReturn(Optional.empty());

        mockMvc.perform(get("/api/articles/missing-id"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.code").value("ARTICLE_NOT_FOUND"))
                .andExpect(jsonPath("$.message").isNotEmpty());
    }

    @Test
    void getArticle_missing_matches_article_not_found_contract() throws Exception {
        given(articleService.getById("missing-id")).willReturn(Optional.empty());

        String expected = new String(
                getClass().getResourceAsStream("/contracts/article-not-found.json").readAllBytes(),
                StandardCharsets.UTF_8
        );

        String actual = mockMvc.perform(get("/api/articles/missing-id"))
                .andExpect(status().isNotFound())
                .andExpect(content().contentTypeCompatibleWith(MediaType.APPLICATION_JSON))
                .andReturn()
                .getResponse()
                .getContentAsString(StandardCharsets.UTF_8);

        JSONAssert.assertEquals(expected, actual, JSONCompareMode.LENIENT);
    }

    @Test
    void getArticle_whenFound_returns200WithBasicFields() throws Exception {
        Article article = new Article();
        article.setId("article_001");
        article.setUrl("https://example.com/a1");
        article.setTitle("첫 기사");
        article.setSource("Example");
        article.setCategory("tech");
        article.setPublishedAt(Instant.parse("2026-05-01T09:00:00Z"));
        article.setStatus("summarized");
        given(articleService.getById("article_001")).willReturn(Optional.of(article));

        mockMvc.perform(get("/api/articles/article_001"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value("article_001"))
                .andExpect(jsonPath("$.title").value("첫 기사"))
                .andExpect(jsonPath("$.source").value("Example"));
    }
}
