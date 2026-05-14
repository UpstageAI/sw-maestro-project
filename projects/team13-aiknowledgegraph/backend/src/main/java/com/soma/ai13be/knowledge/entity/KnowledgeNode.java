package com.soma.ai13be.knowledge.entity;

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
 * 사용자 텍스트 입력과 에이전트가 생성한 인사이트/실행 계획을 그래프 노드로 저장한다.
 */
@Getter
@Entity
@Table(name = "knowledge_nodes")
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class KnowledgeNode extends BaseTimeEntity {

	@Id
	@GeneratedValue(strategy = GenerationType.IDENTITY)
	private Long id;

	@Column(nullable = false, length = 255)
	private String title;

	@Column(nullable = false, columnDefinition = "TEXT")
	private String content;

	@Column(nullable = false, length = 100)
	private String domainName;

	// 프롬프트 개선에 따라 노드 유형이 자주 바뀔 수 있어 enum으로 고정하지 않는다.
	@Column(nullable = false, length = 80)
	private String nodeType;

	// 노드 관리 에이전트가 같은 노드를 반복 분석하지 않도록 처리 완료 여부를 저장한다.
	@Column(nullable = false)
	private boolean analyzed;

	@Builder
	private KnowledgeNode(
		String title,
		String content,
		String domainName,
		String nodeType,
		boolean analyzed
	) {
		this.title = title;
		this.content = content;
		this.domainName = domainName;
		this.nodeType = nodeType;
		this.analyzed = analyzed;
	}
}
