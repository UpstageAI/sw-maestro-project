package com.newspick.ai;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.context.properties.bind.ConstructorBinding;

import java.time.Duration;

@ConfigurationProperties(prefix = "newspick.ai-service")
public record PythonAiProperties(String baseUrl, Long timeoutSeconds) {

    public PythonAiProperties(String baseUrl) {
        this(baseUrl, 120L);
    }

    @ConstructorBinding
    public PythonAiProperties {
        if (baseUrl == null || baseUrl.isBlank()) {
            baseUrl = "http://localhost:8000";
        }
        if (timeoutSeconds == null || timeoutSeconds <= 0) {
            timeoutSeconds = 120L;
        }
    }

    public Duration timeout() {
        return Duration.ofSeconds(timeoutSeconds);
    }
}
