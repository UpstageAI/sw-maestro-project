package com.soma.ai13be.persona.service;

import java.util.List;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import com.soma.ai13be.common.client.SolarApiClient;
import com.soma.ai13be.common.client.dto.SolarChatMessage;
import com.soma.ai13be.common.client.dto.SolarChatRequest;
import com.soma.ai13be.common.client.dto.SolarChatResponse;
import com.soma.ai13be.common.exception.CustomException;
import com.soma.ai13be.common.exception.ErrorCode;
import com.soma.ai13be.persona.entity.Persona;
import com.soma.ai13be.persona.prompt.PersonaPromptTemplates;
import com.soma.ai13be.persona.repository.PersonaRepository;

import lombok.RequiredArgsConstructor;

@Service
@RequiredArgsConstructor
public class PersonaService {

	/*
	 * 생성된 systemPrompt는 Persona 테이블에 저장되어 반복 사용됩니다.
	 *
	 * 따라서 창의적인 문장 생성보다 일관성 있는 지침 생성이 중요하므로
	 * temperature는 낮게 설정합니다.
	 */
	private static final double PROMPT_GENERATION_TEMPERATURE = 0.2;
	private static final int PROMPT_GENERATION_MAX_TOKENS = 1200;

	private final PersonaRepository personaRepository;
	private final SolarApiClient solarApiClient;

	@Transactional
	public Persona create(String domainName) {
		String normalizedDomainName = normalizeDomainName(domainName);

		// 동일 도메인 페르소나가 중복 생성되지 않도록 방지
		if (personaRepository.existsByDomainName(normalizedDomainName)) {
			throw new CustomException(
				ErrorCode.DUPLICATE_PERSONA,
				"Persona already exists for domain: " + normalizedDomainName
			);
		}

		// 사용자가 입력한 도메인명만으로 토론용 system prompt를 생성해 Persona에 저장
		String systemPrompt = generateSystemPrompt(normalizedDomainName);
		Persona persona = Persona.builder()
			.domainName(normalizedDomainName)
			.name(normalizedDomainName + " Persona")
			.systemPrompt(systemPrompt)
			.builtIn(false)
			.enabled(true)
			.build();

		return personaRepository.save(persona);
	}

	@Transactional(readOnly = true)
	public List<Persona> findAll() {
		return personaRepository.findAll();
	}

	@Transactional
	public Persona regenerate(Long personaId) {
		Persona persona = personaRepository.findById(personaId)
			.orElseThrow(() -> personaNotFound(personaId));

		String newSystemPrompt = generateSystemPrompt(persona.getDomainName());
		persona.updateSystemPrompt(newSystemPrompt);
		return persona;
	}

	@Transactional
	public Persona update(Long personaId, String systemPrompt) {
		if (!StringUtils.hasText(systemPrompt)) {
			throw new CustomException(ErrorCode.INVALID_REQUEST, "systemPrompt must not be blank");
		}

		Persona persona = personaRepository.findById(personaId)
			.orElseThrow(() -> personaNotFound(personaId));

		persona.updateSystemPrompt(systemPrompt.strip());
		return persona;
	}

	@Transactional
	public void delete(Long personaId) {
		Persona persona = personaRepository.findById(personaId)
			.orElseThrow(() -> personaNotFound(personaId));

		// 초기 기본 페르소나일 경우
		if (persona.isBuiltIn()) {
			throw new CustomException(ErrorCode.BUILT_IN_PERSONA_DELETION, "Built-in persona cannot be deleted: " + personaId);
		}

		personaRepository.delete(persona);
	}

	/**
	 * 특정 도메인에 맞는 페르소나 systemPrompt를 LLM을 통해 생성합니다.
	 *
	 * system 메시지에는 "프롬프트 생성자"로서의 역할과 결과물 규칙을 전달하고,
	 * user 메시지에는 실제 생성 대상 도메인을 전달합니다.
	 *
	 * @param domainName systemPrompt를 생성할 도메인 이름
	 * @return 정제된 systemPrompt
	 */
	private String generateSystemPrompt(String domainName) {
		// system 메시지는 프롬프트 작성자의 역할을 고정하고, user 메시지에는 생성 대상 도메인을 전달합니다.
		SolarChatRequest request = new SolarChatRequest(
			List.of(
				SolarChatMessage.system(PersonaPromptTemplates.personaPromptGenerationSystemPrompt()),
				SolarChatMessage.user(PersonaPromptTemplates.personaPromptGenerationUserPrompt(domainName))
			),
			PROMPT_GENERATION_TEMPERATURE,
			PROMPT_GENERATION_MAX_TOKENS
		);
		SolarChatResponse response = solarApiClient.chatCompletion(request);
		String systemPrompt = response == null ? null : response.firstContent();

		// 응답이 비어 있거나 유효하지 않은 경우, 불완전한 Persona가 DB에 저장되지 않도록 예외를 발생
		if (!StringUtils.hasText(systemPrompt)) {
			throw new CustomException(
				ErrorCode.PERSONA_PROMPT_GENERATION_FAILED,
				"Failed to generate persona prompt for domain: " + domainName
			);
		}
		return systemPrompt.strip();
	}

	/**
	 * 도메인명을 저장 및 중복 검사에 사용할 수 있는 형태로 정규화합니다.
	 * 현재는 앞뒤 공백 제거만 수행합니다.
	 *
	 * @param domainName 사용자 입력 도메인 이름
	 * @return 정규화된 도메인 이름
	 */
	private String normalizeDomainName(String domainName) {
		if (!StringUtils.hasText(domainName)) {
			throw new CustomException(ErrorCode.INVALID_REQUEST, "domainName must not be blank");
		}
		return domainName.strip();
	}

	private CustomException personaNotFound(Long personaId) {
		return new CustomException(ErrorCode.PERSONA_NOT_FOUND, "Persona not found: " + personaId);
	}
}
