package com.newspick.article;

import com.newspick.quiz.QuizQuestion;
import org.junit.jupiter.api.Test;

import java.time.Instant;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

class ArticleQuizDtoTest {

    @Test
    void article_detail_response_includes_quiz_items() {
        Article article = new Article();
        article.setId("article_001");
        article.setUrl("https://example.com/article_001");
        article.setTitle("제목");
        article.setSource("Example");
        article.setCategory("테크");
        article.setPublishedAt(Instant.parse("2026-05-12T00:00:00Z"));
        article.setStatus("summarized");
        article.setQuiz(List.of(
                new QuizQuestion("quiz_001", "본문 내용은 사실이다", true, "본문 근거")
        ));

        ArticleDetailResponse response = ArticleDetailResponse.from(article);

        assertThat(response.quiz()).hasSize(1);
        assertThat(response.quiz().get(0).id()).isEqualTo("quiz_001");
        assertThat(response.quiz().get(0).answer()).isTrue();
        assertThat(response.quiz().get(0).explanation()).isEqualTo("본문 근거");
    }
}
