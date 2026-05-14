package com.newspick.report;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;

@Entity
@Table(name = "daily_reports")
@Getter
@Setter
@NoArgsConstructor
public class DailyReport {

    @Id
    @Column(name = "report_date")
    private LocalDate reportDate;

    @Column(name = "report_updated_at")
    private OffsetDateTime reportUpdatedAt;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "briefing", columnDefinition = "jsonb")
    private Map<String, String> briefing;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "timeline", columnDefinition = "jsonb")
    private List<Map<String, Object>> timeline;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "flow", columnDefinition = "jsonb")
    private List<Map<String, String>> flow;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "keywords", columnDefinition = "jsonb")
    private List<Map<String, Object>> keywords;
}
