package com.newspick.article;

import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface ArticleRepository extends JpaRepository<Article, String> {

    List<Article> findByStatusOrderByPublishedAtDesc(String status);

    List<Article> findByStatusAndCategoryInOrderByPublishedAtDesc(String status, List<String> categories);
}
