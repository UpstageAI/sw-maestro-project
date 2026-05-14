package com.newspick.report;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

import java.time.Clock;
import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.util.Map;
import java.util.Optional;

import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(ReportController.class)
class ReportByDateControllerTest {

    @Autowired
    MockMvc mockMvc;

    @MockitoBean
    DailyReportRepository dailyReportRepository;

    @MockitoBean
    Clock clock;

    @Test
    void getReportByDate_returns_briefing() throws Exception {
        DailyReport report = new DailyReport();
        report.setReportDate(LocalDate.of(2026, 5, 12));
        report.setReportUpdatedAt(OffsetDateTime.parse("2026-05-12T09:30:00+09:00"));
        report.setBriefing(Map.of("headline", "오늘의 핵심", "summary", "두 가지 흐름"));

        when(dailyReportRepository.findById(LocalDate.of(2026, 5, 12)))
                .thenReturn(Optional.of(report));

        mockMvc.perform(get("/api/report/2026-05-12"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.date").value("2026-05-12"))
                .andExpect(jsonPath("$.briefing.headline").value("오늘의 핵심"))
                .andExpect(jsonPath("$.briefing.summary").value("두 가지 흐름"));
    }

    @Test
    void getReportByDate_rejects_invalid_date() throws Exception {
        mockMvc.perform(get("/api/report/2026-5-12"))
                .andExpect(status().isBadRequest());
    }
}
