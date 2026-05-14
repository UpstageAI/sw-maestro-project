package com.newspick.article;

import com.newspick.quiz.QuizQuestion;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

import java.time.Instant;
import java.util.List;

@Entity
@Table(name = "articles")
@Getter
@Setter
@NoArgsConstructor
public class Article {

    @Id
    @Column(name = "id", nullable = false)
    private String id;

    @Column(name = "url", nullable = false, unique = true)
    private String url;

    @Column(name = "title", nullable = false)
    private String title;

    @Column(name = "source", nullable = false)
    private String source;

    @Column(name = "category", nullable = false)
    private String category;

    @Column(name = "published_at", nullable = false)
    private Instant publishedAt;

    @Column(name = "status", nullable = false)
    private String status;

    @Column(name = "raw_text")
    private String rawText;

    @Column(name = "raw_text_status")
    private String rawTextStatus;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "summary", columnDefinition = "jsonb")
    private List<String> summary;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "keywords", columnDefinition = "jsonb")
    private List<String> keywords;

    @Column(name = "importance")
    private String importance;

    @Column(name = "context")
    private String context;

    @Column(name = "importance_score")
    private Short importanceScore;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "quiz", columnDefinition = "jsonb")
    private List<QuizQuestion> quiz;
}
