package com.soma.ai13be.common.client;

import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.util.StringUtils;
import org.springframework.web.client.RestClient;

import com.soma.ai13be.common.client.dto.SolarChatRequest;
import com.soma.ai13be.common.client.dto.SolarChatResponse;

public class SolarApiClient {

	private final RestClient restClient;
	private final SolarApiProperties properties;

	public SolarApiClient(RestClient.Builder restClientBuilder, SolarApiProperties properties) {
		this.properties = properties;
		this.restClient = restClientBuilder
			.baseUrl(properties.getBaseUrl())
			.defaultHeader(HttpHeaders.CONTENT_TYPE, MediaType.APPLICATION_JSON_VALUE)
			.build();
	}

	public SolarChatResponse chatCompletion(SolarChatRequest request) {
		return restClient.post()
			.uri(properties.getChatCompletionsPath())
			.header(HttpHeaders.AUTHORIZATION, "Bearer " + requiredApiKey())
			.body(request.withDefaultModel(properties.getModel()))
			.retrieve()
			.body(SolarChatResponse.class);
	}

	private String requiredApiKey() {
		if (!StringUtils.hasText(properties.getApiKey())) {
			throw new IllegalStateException("Solar API key is required. Set solar.api.api-key.");
		}
		return properties.getApiKey();
	}
}
