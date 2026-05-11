package com.soma.ai13be.persona.prompt;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

import com.soma.ai13be.persona.prompt.PersonaPromptTemplates;

class PersonaPromptTemplatesTest {

	@Test
	void createsSystemPromptForPromptGeneration() {
		assertThat(PersonaPromptTemplates.personaPromptGenerationSystemPrompt())
			.contains("multi-agent discussion service")
			.contains("Write the persona prompt in Korean")
			.contains("Return only the final system prompt text");
	}

	@Test
	void createsUserPromptWithDomainName() {
		assertThat(PersonaPromptTemplates.personaPromptGenerationUserPrompt("health"))
			.contains("Domain: health")
			.contains("perspective this persona should prioritize")
			.contains("safety rules");
	}

	@Test
	void usesGeneralDomainWhenDomainNameIsBlank() {
		assertThat(PersonaPromptTemplates.personaPromptGenerationUserPrompt(" "))
			.contains("Domain: general");
	}
}
