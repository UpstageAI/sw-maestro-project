package com.newspick;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.utility.DockerImageName;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest
@ActiveProfiles("test")
@Testcontainers
class MigrationIntegrationTest {

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
    JdbcTemplate jdbc;

    @Test
    void flyway_migration_creates_articles_daily_reports_and_pgvector() {
        Boolean articlesExists = jdbc.queryForObject(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'articles')",
                Boolean.class
        );
        Boolean dailyReportsExists = jdbc.queryForObject(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'daily_reports')",
                Boolean.class
        );
        Boolean dailyReportBriefingIsJsonb = jdbc.queryForObject(
                """
                SELECT EXISTS (
                  SELECT 1
                  FROM information_schema.columns
                  WHERE table_schema = 'public'
                    AND table_name = 'daily_reports'
                    AND column_name = 'briefing'
                    AND udt_name = 'jsonb'
                )
                """,
                Boolean.class
        );
        Boolean dailyReportTimelineExists = jdbc.queryForObject(
                """
                SELECT EXISTS (
                  SELECT 1
                  FROM information_schema.columns
                  WHERE table_schema = 'public'
                    AND table_name = 'daily_reports'
                    AND column_name = 'timeline'
                    AND udt_name = 'jsonb'
                )
                """,
                Boolean.class
        );
        Boolean legacyReportColumnsRemoved = jdbc.queryForObject(
                """
                SELECT NOT EXISTS (
                  SELECT 1
                  FROM information_schema.columns
                  WHERE table_schema = 'public'
                    AND table_name = 'daily_reports'
                    AND column_name IN ('headline', 'sub_articles')
                )
                """,
                Boolean.class
        );
        Boolean vectorExtensionActive = jdbc.queryForObject(
                "SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')",
                Boolean.class
        );
        Boolean articlesUrlUnique = jdbc.queryForObject(
                """
                SELECT EXISTS (
                  SELECT 1
                  FROM information_schema.table_constraints tc
                  JOIN information_schema.constraint_column_usage ccu
                    ON tc.constraint_name = ccu.constraint_name
                   AND tc.table_schema = ccu.table_schema
                  WHERE tc.table_schema = 'public'
                    AND tc.table_name = 'articles'
                    AND tc.constraint_type = 'UNIQUE'
                    AND ccu.column_name = 'url'
                )
                """,
                Boolean.class
        );

        assertThat(articlesExists).as("articles table exists").isTrue();
        assertThat(dailyReportsExists).as("daily_reports table exists").isTrue();
        assertThat(dailyReportBriefingIsJsonb).as("daily_reports.briefing is jsonb").isTrue();
        assertThat(dailyReportTimelineExists).as("daily_reports.timeline exists").isTrue();
        assertThat(legacyReportColumnsRemoved).as("legacy daily report columns removed").isTrue();
        assertThat(vectorExtensionActive).as("pgvector extension active").isTrue();
        assertThat(articlesUrlUnique).as("articles.url unique constraint exists").isTrue();
    }
}
