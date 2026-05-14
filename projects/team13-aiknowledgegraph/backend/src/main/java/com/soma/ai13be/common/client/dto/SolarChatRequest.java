package com.soma.ai13be.common.client.dto;

import java.util.List;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

@JsonInclude(JsonInclude.Include.NON_NULL)
public record SolarChatRequest(
	String model,
	List<SolarChatMessage> messages,
	Double temperature,
	@JsonProperty("max_tokens")
	Integer maxTokens
) {

	public SolarChatRequest {
		if (messages == null || messages.isEmpty()) {
			throw new IllegalArgumentException("messages must not be empty");
		}
		messages = List.copyOf(messages);
	}

	public SolarChatRequest(List<SolarChatMessage> messages) {
		this(null, messages, null, null);
	}

	public SolarChatRequest(List<SolarChatMessage> messages, Double temperature, Integer maxTokens) {
		this(null, messages, temperature, maxTokens);
	}

	public SolarChatRequest withDefaultModel(String defaultModel) {
		if (model != null && !model.isBlank()) {
			return this;
		}
		return new SolarChatRequest(defaultModel, messages, temperature, maxTokens);
	}
}
