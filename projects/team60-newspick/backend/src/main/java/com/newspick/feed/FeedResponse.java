package com.newspick.feed;

import java.util.List;

public record FeedResponse(List<ArticleSummaryDto> articles) {
}
