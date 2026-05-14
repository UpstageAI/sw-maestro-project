package com.soma.ai13be.discussion.entity;

import com.soma.ai13be.common.entity.BaseTimeEntity;
import com.soma.ai13be.persona.entity.Persona;

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
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

/**
 * 토론 중 특정 라운드에서 특정 페르소나가 생성한 응답입니다.
 * 어떤 페르소나가 어느 라운드에서 어떤 주장을 했는지 추적하기 위해 별도 테이블로 분리합니다.
 */
@Getter
@Entity
@Table(name = "agent_discussion_messages")
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class AgentDiscussionMessage extends BaseTimeEntity {

	@Id
	@GeneratedValue(strategy = GenerationType.IDENTITY)
	private Long id;

	@ManyToOne(fetch = FetchType.LAZY, optional = false)
	@JoinColumn(name = "discussion_id", nullable = false)
	private AgentDiscussion discussion;

	@ManyToOne(fetch = FetchType.LAZY)
	@JoinColumn(name = "persona_id")
	private Persona persona;

	@Enumerated(EnumType.STRING)
	@Column(nullable = false, length = 30)
	private DiscussionRound round;

	@Column(nullable = false, columnDefinition = "TEXT")
	private String content;

	@Builder
	private AgentDiscussionMessage(
		AgentDiscussion discussion,
		Persona persona,
		DiscussionRound round,
		String content
	) {
		this.discussion = discussion;
		this.persona = persona;
		this.round = round;
		this.content = content;
	}
}
