package com.newspick.report;

import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.Clock;
import java.time.LocalDate;

@RestController
@RequestMapping("/api")
public class ReportController {

    private final DailyReportRepository dailyReportRepository;
    private final Clock clock;

    public ReportController(DailyReportRepository dailyReportRepository, Clock clock) {
        this.dailyReportRepository = dailyReportRepository;
        this.clock = clock;
    }

    @GetMapping("/report/today")
    public ResponseEntity<Object> getTodayReport() {
        return getByDate(LocalDate.now(clock));
    }

    @GetMapping("/report/{date}")
    public ResponseEntity<Object> getReportByDate(
            @PathVariable @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate date) {
        return getByDate(date);
    }

    private ResponseEntity<Object> getByDate(LocalDate date) {
        return dailyReportRepository.findById(date)
                .<ResponseEntity<Object>>map(r -> ResponseEntity.ok(toResponse(r)))
                .orElseGet(() -> ResponseEntity.status(404)
                        .body(new ReportNotReadyResponse("REPORT_NOT_READY", date)));
    }

    private DailyReportResponse toResponse(DailyReport r) {
        return DailyReportResponse.from(r);
    }

    record ReportNotReadyResponse(String code, LocalDate date) {}
}
