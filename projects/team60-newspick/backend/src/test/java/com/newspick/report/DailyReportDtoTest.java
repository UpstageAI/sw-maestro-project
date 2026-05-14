package com.newspick.report;

import org.junit.jupiter.api.Test;

import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

class DailyReportDtoTest {

    @Test
    void daily_report_response_maps_timeline_flow_keywords() {
        DailyReport report = new DailyReport();
        report.setReportDate(LocalDate.of(2026, 5, 12));
        report.setReportUpdatedAt(OffsetDateTime.parse("2026-05-12T09:30:00+09:00"));
        report.setBriefing(Map.of("headline", "today headline", "summary", "today summary"));
        report.setTimeline(List.of(
                Map.of(
                        "articleId", "article_001",
                        "category", "tech",
                        "timeLabel", "09:20",
                        "title", "AI agent expansion",
                        "sourceCount", 4,
                        "summary", "automation is spreading"
                ),
                Map.of(
                        "articleId", "article_002",
                        "category", "economy",
                        "timeLabel", "10:10",
                        "title", "export recovery",
                        "sourceCount", 3
                ),
                Map.of(
                        "articleId", "article_003",
                        "category", "issue",
                        "timeLabel", "11:00",
                        "title", "policy debate",
                        "sourceCount", 2
                )
        ));
        report.setFlow(List.of(
                Map.of("category", "tech", "description", "AI adoption is expanding"),
                Map.of("category", "economy", "description", "exports are recovering"),
                Map.of("category", "issue", "description", "policy debate continues")
        ));
        report.setKeywords(List.of(
                Map.of("text", "AI", "weight", 5),
                Map.of("text", "automation", "weight", 4),
                Map.of("text", "work", "weight", 3)
        ));

        DailyReportResponse response = DailyReportResponse.from(report);

        assertThat(response.briefing().headline()).isEqualTo("today headline");
        assertThat(response.briefing().summary()).isEqualTo("today summary");
        assertThat(response.timeline()).hasSize(3);
        assertThat(response.flow().get(0).label()).isEqualTo("tech");
        assertThat(response.flow().get(0).category()).isEqualTo("tech");
        assertThat(response.keywords().get(0).text()).isEqualTo("AI");
        assertThat(response.keywords().get(0).weight()).isEqualTo(5);
    }

    @Test
    void daily_report_response_defaults_legacy_timeline_fields() {
        DailyReport report = new DailyReport();
        report.setReportDate(LocalDate.of(2026, 5, 13));
        report.setReportUpdatedAt(OffsetDateTime.parse("2026-05-13T09:30:00+09:00"));
        report.setBriefing(Map.of("headline", "today headline", "summary", "today summary"));
        report.setTimeline(List.of(
                Map.of(
                        "articleId", "article_001",
                        "timeLabel", "09:20",
                        "title", "legacy report item"
                )
        ));

        DailyReportResponse response = DailyReportResponse.from(report);

        assertThat(response.timeline().get(0).category()).isEqualTo("이슈");
        assertThat(response.timeline().get(0).sourceCount()).isEqualTo(1);
    }
}
