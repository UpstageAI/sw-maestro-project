package com.newspick.article;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.skyscreamer.jsonassert.JSONAssert;
import org.skyscreamer.jsonassert.JSONCompareMode;
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

import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
@Testcontainers
class ArticleDetailContractTest {

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
    void article_detail_response_matches_contract_fixture() throws Exception {
        Article a = new Article();
        a.setId("article_001");
        a.setUrl("https://example.com/article_001");
        a.setTitle("제목");
        a.setSource("Example");
        a.setCategory("테크");
        a.setPublishedAt(Instant.parse("2026-05-12T00:00:00Z"));
        a.setStatus("summarized");
        a.setRawText("본문 첫 문단\n\n본문 둘째 문단");
        a.setRawTextStatus("full_text");
        a.setSummary(List.of("핵심 요약", "두 번째 요약", "세 번째 요약"));
        a.setKeywords(List.of("AI 에이전트", "오픈AI", "자동화"));
        a.setImportance("중요한 이유");
        a.setContext("추가 배경");
        a.setImportanceScore((short) 8);
        articleRepository.save(a);

        String expected = new String(
                getClass().getResourceAsStream("/contracts/article-detail.article_001.json").readAllBytes(),
                StandardCharsets.UTF_8
        );

        String actual = mockMvc.perform(get("/api/articles/article_001"))
                .andExpect(status().isOk())
                .andReturn()
                .getResponse()
                .getContentAsString(StandardCharsets.UTF_8);

        JSONAssert.assertEquals(expected, actual, JSONCompareMode.LENIENT);

        assertThat(actual).containsPattern(
                "\"publishedAt\":\"\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}"
        );
    }
}
