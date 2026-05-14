package com.soma.ai13be.persona.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.util.List;
import java.util.Optional;

import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

import com.soma.ai13be.common.client.SolarApiClient;
import com.soma.ai13be.common.client.dto.SolarChatMessage;
import com.soma.ai13be.common.client.dto.SolarChatRequest;
import com.soma.ai13be.common.client.dto.SolarChatResponse;
import com.soma.ai13be.common.exception.CustomException;
import com.soma.ai13be.common.exception.ErrorCode;
import com.soma.ai13be.persona.entity.Persona;
import com.soma.ai13be.persona.repository.PersonaRepository;

class PersonaServiceTest {

	private final PersonaRepository personaRepository = org.mockito.Mockito.mock(PersonaRepository.class);
	private final SolarApiClient solarApiClient = org.mockito.Mockito.mock(SolarApiClient.class);
	private final PersonaService service = new PersonaService(personaRepository, solarApiClient);

	@Test
	void createsPersonaWithGeneratedSystemPrompt() {
		when(personaRepository.existsByDomainName("health")).thenReturn(false);
		when(solarApiClient.chatCompletion(any(SolarChatRequest.class)))
			.thenReturn(response("Generated health persona prompt"));
		when(personaRepository.save(any(Persona.class)))
			.thenAnswer(invocation -> invocation.getArgument(0));

		Persona persona = service.create(" health ");

		assertThat(persona.getDomainName()).isEqualTo("health");
		assertThat(persona.getName()).isEqualTo("health Persona");
		assertThat(persona.getSystemPrompt()).isEqualTo("Generated health persona prompt");
		assertThat(persona.isBuiltIn()).isFalse();
		assertThat(persona.isEnabled()).isTrue();

		ArgumentCaptor<SolarChatRequest> requestCaptor = ArgumentCaptor.forClass(SolarChatRequest.class);
		verify(solarApiClient).chatCompletion(requestCaptor.capture());
		SolarChatRequest request = requestCaptor.getValue();
		assertThat(request.temperature()).isEqualTo(0.2);
		assertThat(request.maxTokens()).isEqualTo(1200);
		assertThat(request.messages())
			.extracting(SolarChatMessage::role)
			.containsExactly("system", "user");
		assertThat(request.messages().get(1).content()).contains("Domain: health");
	}

	@Test
	void rejectsBlankDomainName() {
		assertThatThrownBy(() -> service.create(" "))
			.isInstanceOf(CustomException.class)
			.hasFieldOrPropertyWithValue("errorCode", ErrorCode.INVALID_REQUEST)
			.hasMessageContaining("domainName");
	}

	@Test
	void rejectsDuplicateDomainName() {
		when(personaRepository.existsByDomainName("health")).thenReturn(true);

		assertThatThrownBy(() -> service.create("health"))
			.isInstanceOf(CustomException.class)
			.hasFieldOrPropertyWithValue("errorCode", ErrorCode.DUPLICATE_PERSONA)
			.hasMessageContaining("health");
	}

	@Test
	void rejectsEmptyGeneratedPrompt() {
		when(personaRepository.existsByDomainName("health")).thenReturn(false);
		when(solarApiClient.chatCompletion(any(SolarChatRequest.class)))
			.thenReturn(emptyResponse());

		assertThatThrownBy(() -> service.create("health"))
			.isInstanceOf(CustomException.class)
			.hasFieldOrPropertyWithValue("errorCode", ErrorCode.PERSONA_PROMPT_GENERATION_FAILED)
			.hasMessageContaining("health");
	}

	@Test
	void deletesPersona() {
		Persona persona = persona("health", false);
		when(personaRepository.findById(1L)).thenReturn(Optional.of(persona));

		service.delete(1L);

		verify(personaRepository).delete(persona);
	}

	@Test
	void rejectsDeletingUnknownPersona() {
		when(personaRepository.findById(1L)).thenReturn(Optional.empty());

		assertThatThrownBy(() -> service.delete(1L))
			.isInstanceOf(CustomException.class)
			.hasFieldOrPropertyWithValue("errorCode", ErrorCode.PERSONA_NOT_FOUND)
			.hasMessageContaining("1");
	}

	@Test
	void rejectsDeletingBuiltInPersona() {
		Persona persona = persona("health", true);
		when(personaRepository.findById(1L)).thenReturn(Optional.of(persona));

		assertThatThrownBy(() -> service.delete(1L))
			.isInstanceOf(CustomException.class)
			.hasFieldOrPropertyWithValue("errorCode", ErrorCode.BUILT_IN_PERSONA_DELETION)
			.hasMessageContaining("1");
		verify(personaRepository, never()).delete(any(Persona.class));
	}

	@Test
	void regeneratesSystemPrompt() {
		Persona persona = persona("health", false);
		when(personaRepository.findById(1L)).thenReturn(Optional.of(persona));
		when(solarApiClient.chatCompletion(any(SolarChatRequest.class)))
			.thenReturn(response("Regenerated health persona prompt"));

		Persona updated = service.regenerate(1L);

		assertThat(updated.getSystemPrompt()).isEqualTo("Regenerated health persona prompt");
		ArgumentCaptor<SolarChatRequest> captor = ArgumentCaptor.forClass(SolarChatRequest.class);
		verify(solarApiClient).chatCompletion(captor.capture());
		assertThat(captor.getValue().messages().get(1).content()).contains("Domain: health");
	}

	@Test
	void rejectsRegenerateOfUnknownPersona() {
		when(personaRepository.findById(99L)).thenReturn(Optional.empty());

		assertThatThrownBy(() -> service.regenerate(99L))
			.isInstanceOf(CustomException.class)
			.hasFieldOrPropertyWithValue("errorCode", ErrorCode.PERSONA_NOT_FOUND)
			.hasMessageContaining("99");
	}

	@Test
	void throwsExceptionWhenRegeneratedPromptIsEmpty() {
		Persona persona = persona("health", false);
		when(personaRepository.findById(1L)).thenReturn(Optional.of(persona));
		when(solarApiClient.chatCompletion(any(SolarChatRequest.class)))
			.thenReturn(emptyResponse());

		assertThatThrownBy(() -> service.regenerate(1L))
			.isInstanceOf(CustomException.class)
			.hasFieldOrPropertyWithValue("errorCode", ErrorCode.PERSONA_PROMPT_GENERATION_FAILED)
			.hasMessageContaining("health");
	}

	@Test
	void updatesSystemPrompt() {
		Persona persona = persona("health", false);
		when(personaRepository.findById(1L)).thenReturn(Optional.of(persona));

		Persona updated = service.update(1L, "  New system prompt  ");

		assertThat(updated.getSystemPrompt()).isEqualTo("New system prompt");
	}

	@Test
	void rejectsUpdateWithBlankSystemPrompt() {
		assertThatThrownBy(() -> service.update(1L, " "))
			.isInstanceOf(CustomException.class)
			.hasFieldOrPropertyWithValue("errorCode", ErrorCode.INVALID_REQUEST)
			.hasMessageContaining("systemPrompt");
	}

	@Test
	void rejectsUpdateOfUnknownPersona() {
		when(personaRepository.findById(99L)).thenReturn(Optional.empty());

		assertThatThrownBy(() -> service.update(99L, "New prompt"))
			.isInstanceOf(CustomException.class)
			.hasFieldOrPropertyWithValue("errorCode", ErrorCode.PERSONA_NOT_FOUND)
			.hasMessageContaining("99");
	}

	private Persona persona(String domainName, boolean builtIn) {
		return Persona.builder()
			.domainName(domainName)
			.name(domainName + " Persona")
			.systemPrompt(domainName + " prompt")
			.builtIn(builtIn)
			.enabled(true)
			.build();
	}

	private SolarChatResponse response(String content) {
		return new SolarChatResponse(
			"chatcmpl-test",
			"chat.completion",
			1710000000L,
			"solar-pro3",
			List.of(new SolarChatResponse.Choice(
				0,
				SolarChatMessage.assistant(content),
				"stop"
			)),
			new SolarChatResponse.Usage(3, 5, 8)
		);
	}

	private SolarChatResponse emptyResponse() {
		return new SolarChatResponse(
			"chatcmpl-test",
			"chat.completion",
			1710000000L,
			"solar-pro3",
			List.of(new SolarChatResponse.Choice(
				0,
				null,
				"stop"
			)),
			new SolarChatResponse.Usage(3, 0, 3)
		);
	}
}
