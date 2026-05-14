package com.newspick.ai;

import org.junit.jupiter.api.Test;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;

import static org.assertj.core.api.Assertions.assertThat;

class PythonAiPropertiesBindingTest {

    private final ApplicationContextRunner contextRunner = new ApplicationContextRunner()
            .withUserConfiguration(TestConfig.class);

    @Test
    void bindsNewspickAiServiceProperties() {
        contextRunner
                .withPropertyValues(
                        "newspick.ai-service.base-url=http://ai.example",
                        "newspick.ai-service.timeout-seconds=7"
                )
                .run(context -> {
                    PythonAiProperties properties = context.getBean(PythonAiProperties.class);

                    assertThat(properties.baseUrl()).isEqualTo("http://ai.example");
                    assertThat(properties.timeoutSeconds()).isEqualTo(7L);
                    assertThat(properties.timeout().getSeconds()).isEqualTo(7L);
                });
    }

    @EnableConfigurationProperties(PythonAiProperties.class)
    public static class TestConfig {
    }
}
