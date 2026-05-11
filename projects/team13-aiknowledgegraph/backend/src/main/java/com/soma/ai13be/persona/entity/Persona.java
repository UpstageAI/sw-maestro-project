package com.soma.ai13be.persona.entity;

import com.soma.ai13be.common.entity.BaseTimeEntity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

/**
 * 토론에 참여하는 도메인별 AI 페르소나입니다.
 *
 * <p>기본 페르소나는 {@code data.sql}로 미리 저장하고, 사용자가 추가하는 페르소나는
 * {@code PersonaService}가 Solar를 호출해 생성한 system prompt를 저장합니다.</p>
 */
@Getter
@Entity
@Table(name = "personas")
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class Persona extends BaseTimeEntity {

	@Id
	@GeneratedValue(strategy = GenerationType.IDENTITY)
	private Long id;

	/**
	 * 페르소나가 담당하는 도메인 이름입니다.
	 * 별도 도메인 테이블 없이 이 값을 기준으로 중복 생성을 막고 토론 참여자를 구분합니다.
	 */
	@Column(nullable = false, unique = true, length = 100)
	private String domainName;

	/**
	 * 화면에 표시할 페르소나 이름입니다.
	 */
	@Column(nullable = false, length = 100)
	private String name;

	/**
	 * 토론 중 이 페르소나가 응답할 때 Solar system 메시지로 사용할 프롬프트입니다.
	 */
	@Column(nullable = false, columnDefinition = "TEXT")
	private String systemPrompt;

	/**
	 * 초기 데이터로 제공되는 기본 페르소나인지 구분합니다.
	 */
	@Column(nullable = false)
	private boolean builtIn;

	/**
	 * 삭제 대신 비활성화할 때 사용하는 플래그입니다.
	 */
	@Column(nullable = false)
	private boolean enabled;

	public void updateSystemPrompt(String systemPrompt) {
		this.systemPrompt = systemPrompt;
	}

	@Builder
	private Persona(String domainName, String name, String systemPrompt, boolean builtIn, boolean enabled) {
		this.domainName = domainName;
		this.name = name;
		this.systemPrompt = systemPrompt;
		this.builtIn = builtIn;
		this.enabled = enabled;
	}
}
