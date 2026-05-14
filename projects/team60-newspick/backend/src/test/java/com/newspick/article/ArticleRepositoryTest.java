package com.newspick.article;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.jdbc.AutoConfigureTestDatabase;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.boot.test.autoconfigure.orm.jpa.TestEntityManager;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.utility.DockerImageName;

import java.time.Instant;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.boot.test.autoconfigure.jdbc.AutoConfigureTestDatabase.Replace.NONE;

@DataJpaTest
@AutoConfigureTestDatabase(replace = NONE)
@ActiveProfiles("test")
@Testcontainers
class ArticleRepositoryTest {

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
    TestEntityManager em;

    @Autowired
    ArticleRepository repository;

    @Test
    void save_then_findById_returns_article() {
        Instant publishedAt = Instant.parse("2026-05-01T09:00:00Z");
        Article article = new Article();
        article.setId("article_001");
        article.setUrl("https://example.com/a1");
        article.setTitle("첫 기사");
        article.setSource("Example");
        article.setCategory("tech");
        article.setPublishedAt(publishedAt);
        article.setStatus("summarized");

        repository.save(article);
        em.flush();
        em.clear();

        Optional<Article> found = repository.findById("article_001");

        assertThat(found).isPresent();
        Article got = found.get();
        assertThat(got.getTitle()).isEqualTo("첫 기사");
        assertThat(got.getSource()).isEqualTo("Example");
        assertThat(got.getCategory()).isEqualTo("tech");
        assertThat(got.getStatus()).isEqualTo("summarized");
        assertThat(got.getPublishedAt()).isEqualTo(publishedAt);
    }
}
