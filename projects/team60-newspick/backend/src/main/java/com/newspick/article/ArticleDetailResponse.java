package com.newspick.article;

import com.newspick.quiz.QuizQuestion;

import java.time.Instant;
import java.util.List;

public record ArticleDetailResponse(
        String id,
        String url,
        String title,
        String source,
        String category,
        Instant publishedAt,
        String status,
        String content,
        String rawText,
        String rawTextStatus,
        List<String> summary,
        List<String> keywords,
        String importance,
        String context,
        Short importanceScore,
        List<QuizQuestion> quiz
) {

    public static ArticleDetailResponse from(Article article) {
        return new ArticleDetailResponse(
                article.getId(),
                article.getUrl(),
                article.getTitle(),
                article.getSource(),
                article.getCategory(),
                article.getPublishedAt(),
                article.getStatus(),
                article.getRawText(),
                article.getRawText(),
                article.getRawTextStatus(),
                summary(article),
                keywords(article),
                article.getImportance(),
                article.getContext(),
                article.getImportanceScore(),
                quiz(article)
        );
    }

    private static List<String> summary(Article article) {
        return article.getSummary() == null ? List.of() : article.getSummary();
    }

    private static List<String> keywords(Article article) {
        return article.getKeywords() == null ? List.of() : article.getKeywords();
    }

    private static List<QuizQuestion> quiz(Article article) {
        if (article.getQuiz() == null) {
            return List.of();
        }
        return article.getQuiz();
    }
}
