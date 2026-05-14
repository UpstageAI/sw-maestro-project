package com.soma.ai13be.common.client;

import org.springframework.boot.context.properties.ConfigurationProperties;

import lombok.Getter;
import lombok.Setter;

@Setter
@Getter
@ConfigurationProperties(prefix = "solar.api")
public class SolarApiProperties {

	private String baseUrl = "https://api.upstage.ai";

	private String chatCompletionsPath = "/v1/chat/completions";

	private String model = "solar-pro3";

	private String apiKey;

}
