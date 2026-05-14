package com.newspick.report;

import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;

public record DailyReportResponse(
        LocalDate date,
        OffsetDateTime updatedAt,
        Briefing briefing,
        List<TimelineItem> timeline,
        List<FlowItem> flow,
        List<Keyword> keywords
) {

    public static DailyReportResponse from(DailyReport report) {
        Map<String, String> briefing = report.getBriefing();
        return new DailyReportResponse(
                report.getReportDate(),
                report.getReportUpdatedAt(),
                new Briefing(
                        stringValue(briefing, "headline", "title"),
                        stringValue(briefing, "summary", "briefing")
                ),
                mapTimeline(report.getTimeline()),
                mapFlow(report.getFlow()),
                mapKeywords(report.getKeywords())
        );
    }

    private static List<TimelineItem> mapTimeline(List<Map<String, Object>> items) {
        if (items == null) {
            return List.of();
        }
        return items.stream()
                .map(item -> {
                    int sourceCount = intValue(item, "sourceCount");
                    return new TimelineItem(
                            stringValue(item, "articleId"),
                            stringValueOrDefault(item, "이슈", "category"),
                            stringValue(item, "timeLabel"),
                            stringValue(item, "title"),
                            sourceCount > 0 ? sourceCount : 1,
                            stringValue(item, "summary")
                    );
                })
                .toList();
    }

    private static List<FlowItem> mapFlow(List<Map<String, String>> items) {
        if (items == null) {
            return List.of();
        }
        return items.stream()
                .map(item -> {
                    String label = stringValue(item, "label", "category");
                    return new FlowItem(label, label, stringValue(item, "description", "text"));
                })
                .toList();
    }

    private static List<Keyword> mapKeywords(List<Map<String, Object>> items) {
        if (items == null) {
            return List.of();
        }
        return items.stream()
                .map(item -> new Keyword(stringValue(item, "text"), intValue(item, "weight")))
                .toList();
    }

    private static String stringValue(Map<String, ?> item, String... keys) {
        if (item == null) {
            return null;
        }
        for (String key : keys) {
            Object value = item.get(key);
            if (value != null) {
                return value.toString();
            }
        }
        return null;
    }

    private static String stringValueOrDefault(Map<String, ?> item, String defaultValue, String... keys) {
        String value = stringValue(item, keys);
        return value == null || value.isBlank() ? defaultValue : value;
    }

    private static int intValue(Map<String, Object> item, String key) {
        if (item == null) {
            return 0;
        }
        Object value = item.get(key);
        if (value instanceof Number number) {
            return number.intValue();
        }
        if (value instanceof String text && !text.isBlank()) {
            return Integer.parseInt(text);
        }
        return 0;
    }

    public record Briefing(String headline, String summary) {}

    public record TimelineItem(
            String articleId,
            String category,
            String timeLabel,
            String title,
            int sourceCount,
            String summary
    ) {}

    public record FlowItem(String label, String category, String description) {}

    public record Keyword(String text, int weight) {}
}
