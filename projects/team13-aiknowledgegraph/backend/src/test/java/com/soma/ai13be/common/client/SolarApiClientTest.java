package com.soma.ai13be.common.client;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.client.ExpectedCount.once;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.content;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.header;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

import java.util.List;

import org.junit.jupiter.api.Test;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;

import com.soma.ai13be.common.client.dto.SolarChatMessage;
import com.soma.ai13be.common.client.dto.SolarChatRequest;
import com.soma.ai13be.common.client.dto.SolarChatResponse;

class SolarApiClientTest {

	@Test
	void sendsChatCompletionRequestAndReturnsAssistantMessage() {
		RestClient.Builder restClientBuilder = RestClient.builder();
		MockRestServiceServer server = MockRestServiceServer.bindTo(restClientBuilder).build();
		SolarApiProperties properties = new SolarApiProperties();
		properties.setApiKey("test-api-key");
		SolarApiClient client = new SolarApiClient(restClientBuilder, properties);

		server.expect(once(), requestTo("https://api.upstage.ai/v1/chat/completions"))
			.andExpect(method(HttpMethod.POST))
			.andExpect(header("Authorization", "Bearer test-api-key"))
			.andExpect(content().contentType(MediaType.APPLICATION_JSON))
			.andExpect(content().json("""
				{
				  "model": "solar-pro3",
				  "messages": [
				    {"role": "user", "content": "안녕"}
				  ]
				}
				"""))
			.andRespond(withSuccess("""
				{
				  "id": "chatcmpl-test",
				  "object": "chat.completion",
				  "created": 1710000000,
				  "model": "solar-pro3",
				  "choices": [
				    {
				      "index": 0,
				      "message": {"role": "assistant", "content": "안녕하세요."},
				      "finish_reason": "stop"
				    }
				  ],
				  "usage": {
				    "prompt_tokens": 3,
				    "completion_tokens": 5,
				    "total_tokens": 8
				  }
				}
				""", MediaType.APPLICATION_JSON));

		SolarChatResponse response = client.chatCompletion(
			new SolarChatRequest(List.of(SolarChatMessage.user("안녕")))
		);

		assertThat(response.firstContent()).isEqualTo("안녕하세요.");
		assertThat(response.usage().totalTokens()).isEqualTo(8);
		server.verify();
	}

	@Test
	void includesConfiguredModelAndOptionalGenerationParameters() {
		RestClient.Builder restClientBuilder = RestClient.builder();
		MockRestServiceServer server = MockRestServiceServer.bindTo(restClientBuilder).build();
		SolarApiProperties properties = new SolarApiProperties();
		properties.setApiKey("test-api-key");
		properties.setModel("solar-mini");
		SolarApiClient client = new SolarApiClient(restClientBuilder, properties);

		server.expect(once(), requestTo("https://api.upstage.ai/v1/chat/completions"))
			.andExpect(content().json("""
				{
				  "model": "solar-mini",
				  "messages": [
				    {"role": "system", "content": "짧게 답해"},
				    {"role": "user", "content": "서울의 수도는?"}
				  ],
				  "temperature": 0.2,
				  "max_tokens": 100
				}
				"""))
			.andRespond(withSuccess("""
				{
				  "choices": [
				    {
				      "message": {"role": "assistant", "content": "대한민국의 수도는 서울입니다."}
				    }
				  ]
				}
				""", MediaType.APPLICATION_JSON));

		SolarChatResponse response = client.chatCompletion(
			new SolarChatRequest(
				List.of(
					SolarChatMessage.system("짧게 답해"),
					SolarChatMessage.user("서울의 수도는?")
				),
				0.2,
				100
			)
		);

		assertThat(response.firstContent()).isEqualTo("대한민국의 수도는 서울입니다.");
		server.verify();
	}
}
