package com.soma.ai13be.common.client.dto;

import java.util.List;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

@JsonIgnoreProperties(ignoreUnknown = true)
public record SolarChatResponse(
	String id,
	String object,
	Long created,
	String model,
	List<Choice> choices,
	Usage usage
) {

	public String firstContent() {
		if (choices == null || choices.isEmpty() || choices.getFirst().message() == null) {
			return null;
		}
		return choices.getFirst().message().content();
	}

	@JsonIgnoreProperties(ignoreUnknown = true)
	public record Choice(
		Integer index,
		SolarChatMessage message,
		@JsonProperty("finish_reason")
		String finishReason
	) {
	}

	@JsonIgnoreProperties(ignoreUnknown = true)
	public record Usage(
		@JsonProperty("prompt_tokens")
		Integer promptTokens,
		@JsonProperty("completion_tokens")
		Integer completionTokens,
		@JsonProperty("total_tokens")
		Integer totalTokens
	) {
	}
}
