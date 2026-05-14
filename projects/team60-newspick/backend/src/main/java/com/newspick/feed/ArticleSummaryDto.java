package com.newspick.feed;

import java.time.Instant;

public record ArticleSummaryDto(
        String id,
        String title,
        String source,
        String category,
        Instant publishedAt,
        String status,
        String summaryPreview,
        String thumbnailUrl
) {
}
