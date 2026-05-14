package com.newspick.feed;

import com.newspick.article.Article;
import com.newspick.article.ArticleRepository;
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

import static org.hamcrest.Matchers.hasItem;
import static org.hamcrest.Matchers.not;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
@Testcontainers
class FeedIntegrationTest {

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
    void getFeed_returnsSummarizedArticlesOrderedByPublishedAtDesc() throws Exception {
        Article recent = articleFixture("article_recent", "https://news.example.test/recent", "Recent",
                Instant.parse("2026-05-10T09:00:00Z"), "summarized");
        Article old = articleFixture("article_old", "https://news.example.test/old", "Old",
                Instant.parse("2026-05-01T09:00:00Z"), "summarized");
        Article raw = articleFixture("article_raw", "https://news.example.test/raw", "Raw",
                Instant.parse("2026-05-12T09:00:00Z"), "collected");

        articleRepository.saveAll(List.of(recent, old, raw));

        mockMvc.perform(get("/api/feed"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.articles.length()").value(2))
                .andExpect(jsonPath("$.articles[0].id").value("article_recent"))
                .andExpect(jsonPath("$.articles[*].id").value(not(hasItem("article_raw"))));
    }

    @Test
    void getFeed_withCategoryFilter_returnsOnlySelectedCategories() throws Exception {
        Article tech = articleFixture("article_tech", "https://news.example.test/tech", "Tech",
                Instant.parse("2026-05-10T09:00:00Z"), "summarized", "테크");
        Article economy = articleFixture("article_economy", "https://news.example.test/economy", "Economy",
                Instant.parse("2026-05-11T09:00:00Z"), "summarized", "경제");

        articleRepository.saveAll(List.of(tech, economy));

        mockMvc.perform(get("/api/feed").param("categories", "tech"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.articles.length()").value(1))
                .andExpect(jsonPath("$.articles[0].id").value("article_tech"));
    }

    @Test
    void getFeed_excludesLegacyExampleSampleArticles() throws Exception {
        Article real = articleFixture("article_real", "https://news.example.test/real", "Real",
                Instant.parse("2026-05-10T09:00:00Z"), "summarized");
        Article sample = articleFixture("article_sample", "https://example.com/articles/ai-agent-automation", "Sample",
                Instant.parse("2026-05-11T09:00:00Z"), "summarized");

        articleRepository.saveAll(List.of(real, sample));

        mockMvc.perform(get("/api/feed"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.articles.length()").value(1))
                .andExpect(jsonPath("$.articles[0].id").value("article_real"))
                .andExpect(jsonPath("$.articles[*].id").value(not(hasItem("article_sample"))));
    }

    private Article articleFixture(String id, String url, String title, Instant publishedAt, String status) {
        return articleFixture(id, url, title, publishedAt, status, "테크");
    }

    private Article articleFixture(
            String id,
            String url,
            String title,
            Instant publishedAt,
            String status,
            String category
    ) {
        Article a = new Article();
        a.setId(id);
        a.setUrl(url);
        a.setTitle(title);
        a.setSource("Example");
        a.setCategory(category);
        a.setPublishedAt(publishedAt);
        a.setStatus(status);
        return a;
    }
}
