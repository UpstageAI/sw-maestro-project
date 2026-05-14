package com.newspick.feed;

import com.newspick.article.Article;
import com.newspick.article.ArticleRepository;
import com.newspick.category.CategoryCatalog;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.stream.Collectors;

@Service
public class FeedService {

    private static final String STATUS_SUMMARIZED = "summarized";
    private static final int PREVIEW_SENTENCE_COUNT = 2;

    private final ArticleRepository articleRepository;

    public FeedService(ArticleRepository articleRepository) {
        this.articleRepository = articleRepository;
    }

    public List<ArticleSummaryDto> listFeed() {
        return listFeed(List.of());
    }

    public List<ArticleSummaryDto> listFeed(List<String> categoryIds) {
        List<String> categoryLabels = CategoryCatalog.labelsForIds(categoryIds);
        List<Article> articles = categoryLabels.isEmpty()
                ? articleRepository.findByStatusOrderByPublishedAtDesc(STATUS_SUMMARIZED)
                : articleRepository.findByStatusAndCategoryInOrderByPublishedAtDesc(
                        STATUS_SUMMARIZED,
                        categoryLabels
                );

        return articles.stream()
                .filter(this::isDisplayableArticle)
                .map(this::toSummary)
                .toList();
    }

    private boolean isDisplayableArticle(Article a) {
        return a.getUrl() == null || !a.getUrl().startsWith("https://example.com/");
    }

    private ArticleSummaryDto toSummary(Article a) {
        return new ArticleSummaryDto(
                a.getId(),
                a.getTitle(),
                a.getSource(),
                a.getCategory(),
                a.getPublishedAt(),
                a.getStatus(),
                summaryPreview(a.getSummary()),
                null
        );
    }

    private String summaryPreview(List<String> summary) {
        if (summary == null || summary.isEmpty()) {
            return null;
        }
        String preview = summary.stream()
                .map(String::trim)
                .filter(sentence -> !sentence.isEmpty())
                .limit(PREVIEW_SENTENCE_COUNT)
                .collect(Collectors.joining(" "));
        return preview.isBlank() ? null : preview;
    }
}
