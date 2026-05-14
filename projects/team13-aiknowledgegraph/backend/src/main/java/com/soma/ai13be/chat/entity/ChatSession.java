package com.soma.ai13be.chat.entity;

import com.soma.ai13be.common.entity.BaseTimeEntity;
import com.soma.ai13be.persona.entity.Persona;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

/**
 * 페르소나 채팅의 대화 컨텍스트다.
 * 라우터가 질문을 분석한 뒤 페르소나를 결정할 수 있으므로 persona는 선택값으로 둔다.
 */
@Getter
@Entity
@Table(name = "chat_sessions")
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class ChatSession extends BaseTimeEntity {

	@Id
	@GeneratedValue(strategy = GenerationType.IDENTITY)
	private Long id;

	@ManyToOne(fetch = FetchType.LAZY)
	@JoinColumn(name = "persona_id")
	private Persona persona;

	// 채팅방 제목
	@Column(nullable = false, length = 255)
	private String title;

	@Builder
	private ChatSession(Persona persona, String title) {
		this.persona = persona;
		this.title = title;
	}
}
