package com.soma.ai13be.chat.entity;

import com.soma.ai13be.common.entity.BaseTimeEntity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

/**
 * 채팅 세션에 누적되는 메시지다.
 * createdAt이 같거나 밀리초 단위 정렬이 흔들려도 대화 재생 순서가 보장되도록 sequence를 별도로 저장한다.
 */
@Getter
@Entity
@Table(
	name = "chat_messages",
	uniqueConstraints = {
		@UniqueConstraint(name = "uk_chat_messages_session_sequence", columnNames = {"session_id", "message_sequence"})
	}
)
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class ChatMessage extends BaseTimeEntity {

	@Id
	@GeneratedValue(strategy = GenerationType.IDENTITY)
	private Long id;

	@ManyToOne(fetch = FetchType.LAZY, optional = false)
	@JoinColumn(name = "session_id", nullable = false)
	private ChatSession session;

	// 세션 안에서의 메시지 순서
	@Column(name = "message_sequence", nullable = false)
	private int sequence;

	// 메시지 역할: SYSTEM, USER, ASSISTANT
	@Enumerated(EnumType.STRING)
	@Column(nullable = false, length = 30)
	private ChatMessageRole role;

	// 메시지 내용
	@Column(nullable = false, columnDefinition = "TEXT")
	private String content;

	@Builder
	private ChatMessage(ChatSession session, int sequence, ChatMessageRole role, String content) {
		this.session = session;
		this.sequence = sequence;
		this.role = role;
		this.content = content;
	}
}
