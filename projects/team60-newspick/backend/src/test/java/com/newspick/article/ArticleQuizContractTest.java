package com.newspick.article;

import com.newspick.quiz.QuizQuestion;
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

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
@Testcontainers
class ArticleQuizContractTest {

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
    void article_detail_with_quiz_matches_contract_fixture() throws Exception {
        Article article = new Article();
        article.setId("article_001");
        article.setUrl("https://example.com/article_001");
        article.setTitle("제목");
        article.setSource("Example");
        article.setCategory("테크");
        article.setPublishedAt(Instant.parse("2026-05-12T00:00:00Z"));
        article.setStatus("summarized");
        article.setRawText("본문 첫 문단\n\n본문 둘째 문단");
        article.setSummary(List.of("핵심 요약", "두 번째 요약", "세 번째 요약"));
        article.setQuiz(List.of(
                new QuizQuestion("quiz_001", "본문 내용은 사실이다", true, "본문 근거"),
                new QuizQuestion("quiz_002", "본문 내용은 사실이 아니다", false, "반대 근거")
        ));
        articleRepository.save(article);

        String expected = new String(
                getClass().getResourceAsStream("/contracts/article-detail-with-quiz.article_001.json").readAllBytes(),
                StandardCharsets.UTF_8
        );

        String actual = mockMvc.perform(get("/api/articles/article_001"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.quiz.length()").value(2))
                .andExpect(jsonPath("$.quiz[0].id").value("quiz_001"))
                .andExpect(jsonPath("$.quiz[0].question").exists())
                .andExpect(jsonPath("$.quiz[0].answer").isBoolean())
                .andExpect(jsonPath("$.quiz[0].explanation").exists())
                .andExpect(jsonPath("$.quiz[1].id").value("quiz_002"))
                .andReturn()
                .getResponse()
                .getContentAsString(StandardCharsets.UTF_8);

        JSONAssert.assertEquals(expected, actual, JSONCompareMode.LENIENT);
    }
}
