package com.newspick.feed;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import com.newspick.article.Article;
import com.newspick.article.ArticleRepository;
import org.junit.jupiter.api.Test;

import java.time.Instant;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class FeedDtoTest {

    @Test
    void feed_response_includes_summary_preview_and_nullable_thumbnail() throws Exception {
        ArticleRepository repository = mock(ArticleRepository.class);
        Article article = new Article();
        article.setId("article_001");
        article.setUrl("https://news.example.test/a");
        article.setTitle("제목");
        article.setSource("뉴스소스");
        article.setCategory("테크");
        article.setPublishedAt(Instant.parse("2026-05-12T00:00:00Z"));
        article.setStatus("summarized");
        article.setSummary(List.of("긴 요약 문장입니다"));
        when(repository.findByStatusOrderByPublishedAtDesc("summarized"))
                .thenReturn(List.of(article));

        FeedService service = new FeedService(repository);
        List<ArticleSummaryDto> result = service.listFeed();

        assertThat(result).hasSize(1);
        ArticleSummaryDto dto = result.get(0);
        assertThat(dto.summaryPreview()).isEqualTo("긴 요약 문장입니다");
        assertThat(dto.thumbnailUrl()).isNull();

        ObjectMapper mapper = new ObjectMapper().registerModule(new JavaTimeModule());
        String json = mapper.writeValueAsString(new FeedResponse(result));
        assertThat(json).contains("\"thumbnailUrl\":null");
        assertThat(json).contains("\"id\":\"article_001\"");
        assertThat(json).contains("\"title\":\"제목\"");
        assertThat(json).contains("\"source\":\"뉴스소스\"");
        assertThat(json).contains("\"publishedAt\":");
    }

    @Test
    void feed_service_builds_summary_preview_from_complete_sentences_without_cutting() {
        ArticleRepository repository = mock(ArticleRepository.class);
        Article article = new Article();
        article.setId("article_001");
        article.setUrl("https://news.example.test/a");
        article.setTitle("AI 반도체 지원");
        article.setSource("뉴스소스");
        article.setCategory("테크");
        article.setPublishedAt(Instant.parse("2026-05-12T00:00:00Z"));
        article.setStatus("summarized");
        article.setSummary(List.of(
                "정부가 AI 반도체 연구개발 지원과 인력 양성 예산을 함께 늘리며 국내 생산 기반과 장비 생태계를 강화하고 있어요.",
                "기업 투자가 늘면서 클라우드, 자동차, 모바일 분야에서 고성능 칩을 확보하려는 기술 경쟁도 더 빨라지고 있어요.",
                "추가 예산 논의도 이어지고 있어요."
        ));
        when(repository.findByStatusOrderByPublishedAtDesc("summarized"))
                .thenReturn(List.of(article));

        FeedService service = new FeedService(repository);
        List<ArticleSummaryDto> result = service.listFeed();
        String expectedPreview = "정부가 AI 반도체 연구개발 지원과 인력 양성 예산을 함께 늘리며 국내 생산 기반과 장비 생태계를 강화하고 있어요. "
                + "기업 투자가 늘면서 클라우드, 자동차, 모바일 분야에서 고성능 칩을 확보하려는 기술 경쟁도 더 빨라지고 있어요.";

        assertThat(result.get(0).summaryPreview()).isEqualTo(expectedPreview);
        assertThat(result.get(0).summaryPreview()).doesNotContain("추가 예산");
    }

    @Test
    void feed_service_filters_by_selected_category_labels() {
        ArticleRepository repository = mock(ArticleRepository.class);
        when(repository.findByStatusAndCategoryInOrderByPublishedAtDesc("summarized", List.of("테크")))
                .thenReturn(List.of());

        FeedService service = new FeedService(repository);
        List<ArticleSummaryDto> result = service.listFeed(List.of("tech"));

        assertThat(result).isEmpty();
    }

    @Test
    void feed_service_excludes_example_sample_articles() {
        ArticleRepository repository = mock(ArticleRepository.class);
        Article sample = new Article();
        sample.setId("article_001");
        sample.setUrl("https://example.com/articles/ai-agent-automation");
        sample.setTitle("Sample");
        sample.setSource("Example");
        sample.setCategory("?뚰겕");
        sample.setPublishedAt(Instant.parse("2026-05-12T00:00:00Z"));
        sample.setStatus("summarized");

        Article real = new Article();
        real.setId("real_001");
        real.setUrl("https://news.example.test/articles/real");
        real.setTitle("Real");
        real.setSource("News");
        real.setCategory("?뚰겕");
        real.setPublishedAt(Instant.parse("2026-05-12T01:00:00Z"));
        real.setStatus("summarized");

        when(repository.findByStatusOrderByPublishedAtDesc("summarized"))
                .thenReturn(List.of(real, sample));

        FeedService service = new FeedService(repository);
        List<ArticleSummaryDto> result = service.listFeed();

        assertThat(result).extracting(ArticleSummaryDto::id).containsExactly("real_001");
    }
}
