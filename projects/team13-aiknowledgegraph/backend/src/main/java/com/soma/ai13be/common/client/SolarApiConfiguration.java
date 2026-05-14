package com.soma.ai13be.common.client;

import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.client.RestClient;

@Configuration
@EnableConfigurationProperties(SolarApiProperties.class)
class SolarApiConfiguration {

	@Bean
	@ConditionalOnMissingBean
	RestClient.Builder restClientBuilder() {
		return RestClient.builder();
	}

	@Bean
	SolarApiClient solarApiClient(RestClient.Builder restClientBuilder, SolarApiProperties properties) {
		return new SolarApiClient(restClientBuilder, properties);
	}
}
