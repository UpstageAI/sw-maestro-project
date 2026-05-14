package com.newspick.report;

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
import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
@Testcontainers
class DailyReportContractTest {

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
    DailyReportRepository dailyReportRepository;

    @BeforeEach
    void cleanDb() {
        dailyReportRepository.deleteAll();
    }

    @Test
    void daily_report_response_and_404_match_contract_fixtures() throws Exception {
        DailyReport report = new DailyReport();
        report.setReportDate(LocalDate.of(2026, 5, 12));
        report.setReportUpdatedAt(OffsetDateTime.parse("2026-05-12T09:30:00+09:00"));
        report.setBriefing(Map.of("headline", "오늘의 핵심", "summary", "두 가지 흐름"));
        report.setTimeline(List.of(
                Map.of(
                        "articleId", "article_001",
                        "category", "테크",
                        "timeLabel", "09:20",
                        "title", "AI 에이전트 확산",
                        "sourceCount", 4,
                        "summary", "업무 자동화가 빨라졌습니다"
                )
        ));
        report.setFlow(List.of(
                Map.of("label", "원인", "description", "AI 활용이 일상 업무로 넓어졌습니다")
        ));
        report.setKeywords(List.of(
                Map.of("text", "AI", "weight", 5)
        ));
        dailyReportRepository.save(report);

        String expectedReport = readContract("/contracts/daily-report.2026-05-12.json");
        String actualReport = mockMvc.perform(get("/api/report/2026-05-12"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.keywords[0].text").exists())
                .andExpect(jsonPath("$.keywords[0].weight").exists())
                .andReturn()
                .getResponse()
                .getContentAsString(StandardCharsets.UTF_8);

        JSONAssert.assertEquals(expectedReport, actualReport, JSONCompareMode.LENIENT);

        String expectedNotReady = readContract("/contracts/report-not-ready.2026-05-13.json");
        String actualNotReady = mockMvc.perform(get("/api/report/2026-05-13"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.code").value("REPORT_NOT_READY"))
                .andReturn()
                .getResponse()
                .getContentAsString(StandardCharsets.UTF_8);

        JSONAssert.assertEquals(expectedNotReady, actualNotReady, JSONCompareMode.LENIENT);
    }

    private String readContract(String path) throws Exception {
        return new String(getClass().getResourceAsStream(path).readAllBytes(), StandardCharsets.UTF_8);
    }
}
