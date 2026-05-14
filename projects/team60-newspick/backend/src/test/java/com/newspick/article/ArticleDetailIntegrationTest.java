package com.newspick.article;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.utility.DockerImageName;

import java.time.Instant;
import java.util.List;

import static org.hamcrest.Matchers.containsString;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
@Testcontainers
class ArticleDetailIntegrationTest {

    @Container
    static final PostgreSQLContainer<?> POSTGRES = new PostgreSQLContainer<>(
            DockerImageName.parse("pgvector/pgvector:pg16").asCompatibleSubstituteFor("postgres")
    );

    @DynamicPropertySource
    static void datasourceProperties(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", POSTGRES::getJdbcUrl);
        registry.add("spring.datasource.username", POSTGRES::getUsername);
        registry.add("spring.datasource.password", POSTGRES::getPassword);
    }

    @Autowired
    MockMvc mockMvc;

    @Autowired
    ArticleRepository articleRepository;

    @BeforeEach
    void cleanDb() {
        articleRepository.deleteAll();
    }

    @Test
    void getArticle_returns_full_content_from_database() throws Exception {
        Article a = new Article();
        a.setId("article_001");
        a.setUrl("https://example.com/article_001");
        a.setTitle("제목");
        a.setSource("Example");
        a.setCategory("테크");
        a.setPublishedAt(Instant.parse("2026-05-12T00:00:00Z"));
        a.setStatus("summarized");
        a.setRawText("본문 첫 문단\n\n본문 둘째 문단");
        a.setSummary(List.of("핵심 요약"));
        articleRepository.save(a);

        mockMvc.perform(get("/api/articles/article_001"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value("article_001"))
                .andExpect(jsonPath("$.url").value("https://example.com/article_001"))
                .andExpect(jsonPath("$.content").value(containsString("본문 첫 문단")))
                .andExpect(jsonPath("$.summary[0]").value("핵심 요약"));
    }
}
