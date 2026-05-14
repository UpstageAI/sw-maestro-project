package com.newspick.chat;

import java.util.List;

public record ChatRequest(String message, List<String> contextArticleIds) {

    public ChatRequest(String message) {
        this(message, List.of());
    }

    public ChatRequest {
        contextArticleIds = contextArticleIds == null ? List.of() : List.copyOf(contextArticleIds);
    }
}
