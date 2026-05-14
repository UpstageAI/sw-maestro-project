package com.soma.ai13be.common.config;

import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import com.fasterxml.jackson.databind.ObjectMapper;

@Configuration
class JacksonConfiguration {

	@Bean
	@ConditionalOnMissingBean
	ObjectMapper objectMapper() {
		return new ObjectMapper();
	}
}
