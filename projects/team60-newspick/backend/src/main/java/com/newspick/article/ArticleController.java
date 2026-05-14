package com.newspick.article;

import com.newspick.common.ApiErrorResponse;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/articles")
public class ArticleController {

    private static final String CODE_NOT_FOUND = "ARTICLE_NOT_FOUND";
    private static final String MESSAGE_NOT_FOUND = "기사를 찾을 수 없습니다";

    private final ArticleService articleService;

    public ArticleController(ArticleService articleService) {
        this.articleService = articleService;
    }

    @GetMapping("/{id}")
    public ResponseEntity<?> getArticle(@PathVariable String id) {
        return articleService.getById(id)
                .<ResponseEntity<?>>map(article -> ResponseEntity.ok(ArticleDetailResponse.from(article)))
                .orElseGet(() -> ResponseEntity.status(404).body(
                        new ApiErrorResponse(CODE_NOT_FOUND, MESSAGE_NOT_FOUND)
                ));
    }
}
