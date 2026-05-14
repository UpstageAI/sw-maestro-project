package com.newspick.report;

import org.springframework.data.jpa.repository.JpaRepository;

import java.time.LocalDate;

public interface DailyReportRepository extends JpaRepository<DailyReport, LocalDate> {
}
