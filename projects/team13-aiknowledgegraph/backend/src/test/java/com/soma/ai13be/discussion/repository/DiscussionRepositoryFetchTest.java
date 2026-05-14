package com.soma.ai13be.discussion.repository;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.List;

import org.hibernate.Hibernate;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.transaction.annotation.Transactional;

import com.soma.ai13be.discussion.entity.AgentDiscussion;
import com.soma.ai13be.discussion.entity.AgentDiscussionMessage;
import com.soma.ai13be.discussion.entity.DiscussionRound;
import com.soma.ai13be.discussion.entity.DiscussionStatus;
import com.soma.ai13be.knowledge.entity.KnowledgeNode;
import com.soma.ai13be.persona.entity.Persona;

import jakarta.persistence.EntityManager;

@SpringBootTest(properties = {
	"solar.api.api-key=test",
	"spring.docker.compose.enabled=false"
})
@Transactional
class DiscussionRepositoryFetchTest {

	@Autowired
	private EntityManager entityManager;

	@Autowired
	private AgentDiscussionRepository discussionRepository;

	@Autowired
	private AgentDiscussionMessageRepository messageRepository;

	@Test
	void findByIdFetchesTriggerNode() {
		KnowledgeNode node = persist(node());
		AgentDiscussion discussion = persist(discussion(node));
		entityManager.flush();
		entityManager.clear();

		AgentDiscussion found = discussionRepository.findById(discussion.getId()).orElseThrow();

		assertThat(Hibernate.isInitialized(found.getTriggerNode())).isTrue();
	}

	@Test
	void findByDiscussionOrderByCreatedAtAscIdAscFetchesPersona() {
		KnowledgeNode node = persist(node());
		Persona persona = persist(persona());
		AgentDiscussion discussion = persist(discussion(node));
		persist(message(discussion, persona));
		entityManager.flush();
		entityManager.clear();

		AgentDiscussion foundDiscussion = entityManager.find(AgentDiscussion.class, discussion.getId());
		List<AgentDiscussionMessage> messages = messageRepository.findByDiscussionOrderByCreatedAtAscIdAsc(foundDiscussion);

		assertThat(messages).hasSize(1);
		assertThat(Hibernate.isInitialized(messages.getFirst().getPersona())).isTrue();
	}

	private <T> T persist(T entity) {
		entityManager.persist(entity);
		return entity;
	}

	private KnowledgeNode node() {
		return KnowledgeNode.builder()
			.title("피로 기록")
			.content("최근 피곤함")
			.domainName("health")
			.nodeType("symptom")
			.analyzed(true)
			.build();
	}

	private AgentDiscussion discussion(KnowledgeNode node) {
		return AgentDiscussion.builder()
			.triggerNode(node)
			.status(DiscussionStatus.COMPLETED)
			.title("피로 원인 분석")
			.summary("최종 요약")
			.actionPlan("1. 실행")
			.build();
	}

	private Persona persona() {
		return Persona.builder()
			.domainName("health")
			.name("health Persona")
			.systemPrompt("health prompt")
			.builtIn(false)
			.enabled(true)
			.build();
	}

	private AgentDiscussionMessage message(AgentDiscussion discussion, Persona persona) {
		return AgentDiscussionMessage.builder()
			.discussion(discussion)
			.persona(persona)
			.round(DiscussionRound.ANALYSIS)
			.content("건강 분석")
			.build();
	}
}
