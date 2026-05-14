package com.newspick.category;

import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

public final class CategoryCatalog {

    private static final Map<String, String> LABELS_BY_ID = Map.of(
            "tech", "테크",
            "economy", "경제",
            "policy", "정책",
            "issue", "이슈"
    );

    private CategoryCatalog() {
    }

    public static List<String> parseIds(String rawCategories) {
        if (rawCategories == null || rawCategories.isBlank()) {
            return List.of();
        }

        Set<String> categoryIds = new LinkedHashSet<>();
        for (String part : rawCategories.split(",")) {
            String categoryId = part.trim();
            if (!categoryId.isEmpty()) {
                validate(categoryId);
                categoryIds.add(categoryId);
            }
        }

        return new ArrayList<>(categoryIds);
    }

    public static List<String> labelsForIds(List<String> categoryIds) {
        return categoryIds.stream()
                .map(CategoryCatalog::labelForId)
                .toList();
    }

    private static String labelForId(String categoryId) {
        validate(categoryId);
        return LABELS_BY_ID.get(categoryId);
    }

    private static void validate(String categoryId) {
        if (!LABELS_BY_ID.containsKey(categoryId)) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST,
                    "Unsupported category: " + categoryId
            );
        }
    }
}
