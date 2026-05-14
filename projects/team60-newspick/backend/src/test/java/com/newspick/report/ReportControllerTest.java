package com.newspick.report;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

import java.time.Clock;
import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.time.ZoneId;
import java.time.ZonedDateTime;
import java.util.List;
import java.util.Map;
import java.util.Optional;

import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(ReportController.class)
class ReportControllerTest {

    @Autowired
    MockMvc mockMvc;

    @MockitoBean
    DailyReportRepository dailyReportRepository;

    @MockitoBean
    Clock clock;

    @Test
    void getTodayReport_whenMissing_returns404ReportNotReady() throws Exception {
        ZoneId zone = ZoneId.of("Asia/Seoul");
        Clock fixed = Clock.fixed(
                ZonedDateTime.of(2026, 5, 12, 0, 0, 0, 0, zone).toInstant(),
                zone
        );
        when(clock.instant()).thenReturn(fixed.instant());
        when(clock.getZone()).thenReturn(fixed.getZone());
        when(dailyReportRepository.findById(LocalDate.of(2026, 5, 12)))
                .thenReturn(Optional.empty());

        mockMvc.perform(get("/api/report/today"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.code").value("REPORT_NOT_READY"))
                .andExpect(jsonPath("$.date").value("2026-05-12"));
    }

    @Test
    void getReportByDate_whenMissing_returns404ReportNotReady() throws Exception {
        when(dailyReportRepository.findById(LocalDate.of(2026, 5, 12)))
                .thenReturn(Optional.empty());

        mockMvc.perform(get("/api/report/2026-05-12"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.code").value("REPORT_NOT_READY"))
                .andExpect(jsonPath("$.date").value("2026-05-12"));
    }

    @Test
    void getReportByDate_whenFound_returnsReportResponse() throws Exception {
        DailyReport report = new DailyReport();
        report.setReportDate(LocalDate.of(2026, 5, 12));
        report.setReportUpdatedAt(OffsetDateTime.parse("2026-05-12T09:30:00+09:00"));
        report.setBriefing(Map.of("headline", "오늘의 헤드라인", "summary", "오늘의 요약"));
        report.setTimeline(List.of(Map.of("articleId", "a1", "title", "기사 제목")));
        report.setFlow(List.of(Map.of("category", "테크", "description", "테크 흐름")));
        report.setKeywords(List.of(Map.of("text", "AI", "weight", 9)));
        when(dailyReportRepository.findById(LocalDate.of(2026, 5, 12)))
                .thenReturn(Optional.of(report));

        mockMvc.perform(get("/api/report/2026-05-12"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.date").value("2026-05-12"))
                .andExpect(jsonPath("$.briefing.headline").value("오늘의 헤드라인"))
                .andExpect(jsonPath("$.briefing.summary").value("오늘의 요약"))
                .andExpect(jsonPath("$.timeline[0].articleId").value("a1"))
                .andExpect(jsonPath("$.flow[0].category").value("테크"))
                .andExpect(jsonPath("$.keywords[0].text").value("AI"));
    }
}
