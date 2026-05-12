# Discussion Feature Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a synchronous 3-round multi-persona discussion API that accepts a required topic, optional trigger knowledge node, and optional persona IDs.

**Architecture:** Add a focused `discussion` service layer that orchestrates Solar calls and persists `AgentDiscussion` plus `AgentDiscussionMessage` records. Keep prompt construction in `DiscussionPromptTemplates`, expose REST endpoints through `DiscussionController`, and follow the existing chat/persona DTO, Swagger, and mock-based test patterns.

**Tech Stack:** Java 21, Spring Boot 4, Spring Data JPA, Spring MVC, springdoc-openapi, JUnit 5, Mockito, AssertJ, MockMvc.

---

## File Structure

- Modify: `src/main/java/com/soma/ai13be/discussion/entity/AgentDiscussion.java`
  - Add state transition methods for `RUNNING`, `COMPLETED`, and `FAILED`.
- Create: `src/main/java/com/soma/ai13be/discussion/repository/AgentDiscussionRepository.java`
  - JPA repository for discussion aggregate roots.
- Create: `src/main/java/com/soma/ai13be/discussion/repository/AgentDiscussionMessageRepository.java`
  - JPA repository for ordered discussion messages.
- Create: `src/main/java/com/soma/ai13be/discussion/prompt/DiscussionPromptTemplates.java`
  - Round 1, Round 2, and Round 3 prompt builders.
- Create: `src/main/java/com/soma/ai13be/discussion/dto/request/CreateDiscussionCommand.java`
  - Request body for `POST /api/discussions`.
- Create: `src/main/java/com/soma/ai13be/discussion/dto/response/DiscussionMessageResult.java`
  - Response projection for one persisted round message.
- Create: `src/main/java/com/soma/ai13be/discussion/dto/response/DiscussionResult.java`
  - Response projection for discussion details and messages.
- Create: `src/main/java/com/soma/ai13be/discussion/service/DiscussionService.java`
  - Validate request, resolve personas/node, execute all rounds, persist results, and provide read APIs.
- Create: `src/main/java/com/soma/ai13be/discussion/controller/DiscussionController.java`
  - REST API with Swagger/OpenAPI annotations.
- Modify: `src/main/java/com/soma/ai13be/common/exception/ErrorCode.java`
  - Add `DISCUSSION_NOT_FOUND`.
- Create: `src/test/java/com/soma/ai13be/discussion/service/DiscussionServiceTest.java`
  - Unit tests for orchestration, validation, fallback selection, and Solar empty responses.
- Create: `src/test/java/com/soma/ai13be/discussion/controller/DiscussionControllerTest.java`
  - MockMvc tests for REST endpoints and error mappings.

## Task 1: Entity State Transitions And Repositories

**Files:**
- Modify: `src/main/java/com/soma/ai13be/discussion/entity/AgentDiscussion.java`
- Create: `src/main/java/com/soma/ai13be/discussion/repository/AgentDiscussionRepository.java`
- Create: `src/main/java/com/soma/ai13be/discussion/repository/AgentDiscussionMessageRepository.java`
- Modify: `src/main/java/com/soma/ai13be/common/exception/ErrorCode.java`

- [ ] **Step 1: Add discussion not found error code**

Modify `src/main/java/com/soma/ai13be/common/exception/ErrorCode.java` so the enum contains this entry after `CHAT_SESSION_NOT_FOUND`:

```java
	DISCUSSION_NOT_FOUND(HttpStatus.NOT_FOUND, "Discussion not found"),
```

- [ ] **Step 2: Add state transition methods**

Modify `src/main/java/com/soma/ai13be/discussion/entity/AgentDiscussion.java` and add these methods before the builder constructor:

```java
	public void markRunning() {
		this.status = DiscussionStatus.RUNNING;
	}

	public void markCompleted(String summary, String actionPlan) {
		this.status = DiscussionStatus.COMPLETED;
		this.summary = summary;
		this.actionPlan = actionPlan;
	}

	public void markFailed(String summary) {
		this.status = DiscussionStatus.FAILED;
		this.summary = summary;
	}
```

- [ ] **Step 3: Create discussion repository**

Create `src/main/java/com/soma/ai13be/discussion/repository/AgentDiscussionRepository.java`:

```java
package com.soma.ai13be.discussion.repository;

import org.springframework.data.jpa.repository.JpaRepository;

import com.soma.ai13be.discussion.entity.AgentDiscussion;

public interface AgentDiscussionRepository extends JpaRepository<AgentDiscussion, Long> {
}
```

- [ ] **Step 4: Create message repository**

Create `src/main/java/com/soma/ai13be/discussion/repository/AgentDiscussionMessageRepository.java`:

```java
package com.soma.ai13be.discussion.repository;

import java.util.List;

import org.springframework.data.jpa.repository.JpaRepository;

import com.soma.ai13be.discussion.entity.AgentDiscussion;
import com.soma.ai13be.discussion.entity.AgentDiscussionMessage;

public interface AgentDiscussionMessageRepository extends JpaRepository<AgentDiscussionMessage, Long> {

	List<AgentDiscussionMessage> findByDiscussionOrderByCreatedAtAscIdAsc(AgentDiscussion discussion);
}
```

- [ ] **Step 5: Compile**

Run:

```bash
./gradlew compileJava
```

Expected: `BUILD SUCCESSFUL`.

- [ ] **Step 6: Commit**

```bash
git add src/main/java/com/soma/ai13be/common/exception/ErrorCode.java \
  src/main/java/com/soma/ai13be/discussion/entity/AgentDiscussion.java \
  src/main/java/com/soma/ai13be/discussion/repository/AgentDiscussionRepository.java \
  src/main/java/com/soma/ai13be/discussion/repository/AgentDiscussionMessageRepository.java
git commit -m "feat: 토론 저장소와 상태 전이 추가"
```

## Task 2: Prompt Templates

**Files:**
- Create: `src/main/java/com/soma/ai13be/discussion/prompt/DiscussionPromptTemplates.java`
- Test: `src/test/java/com/soma/ai13be/discussion/prompt/DiscussionPromptTemplatesTest.java`

- [ ] **Step 1: Write failing prompt tests**

Create `src/test/java/com/soma/ai13be/discussion/prompt/DiscussionPromptTemplatesTest.java`:

```java
package com.soma.ai13be.discussion.prompt;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

class DiscussionPromptTemplatesTest {

	@Test
	void analysisPromptContainsTopicAndNodeContext() {
		String prompt = DiscussionPromptTemplates.analysisUserPrompt(
			"요즘 피곤해",
			"제목: 수면\n내용: 5시간 수면"
		);

		assertThat(prompt).contains("요즘 피곤해");
		assertThat(prompt).contains("제목: 수면");
		assertThat(prompt).contains("Round 1");
		assertThat(prompt).contains("도메인 관점");
	}

	@Test
	void rebuttalPromptContainsPreviousAnalyses() {
		String prompt = DiscussionPromptTemplates.rebuttalUserPrompt(
			"피로 분석",
			"[health Persona]\n수면 부족"
		);

		assertThat(prompt).contains("피로 분석");
		assertThat(prompt).contains("수면 부족");
		assertThat(prompt).contains("Round 2");
		assertThat(prompt).contains("반론");
	}

	@Test
	void synthesisPromptRequestsSummaryAndActionPlanSections() {
		String systemPrompt = DiscussionPromptTemplates.synthesisSystemPrompt();
		String userPrompt = DiscussionPromptTemplates.synthesisUserPrompt(
			"피로 분석",
			"[Round 1]\n분석",
			"[Round 2]\n반론"
		);

		assertThat(systemPrompt).contains("종합");
		assertThat(userPrompt).contains("요약:");
		assertThat(userPrompt).contains("실행 계획:");
		assertThat(userPrompt).contains("분석");
		assertThat(userPrompt).contains("반론");
	}
}
```

- [ ] **Step 2: Run prompt tests and verify they fail**

Run:

```bash
./gradlew test --tests com.soma.ai13be.discussion.prompt.DiscussionPromptTemplatesTest
```

Expected: FAIL because `DiscussionPromptTemplates` does not exist.

- [ ] **Step 3: Implement prompt templates**

Create `src/main/java/com/soma/ai13be/discussion/prompt/DiscussionPromptTemplates.java`:

```java
package com.soma.ai13be.discussion.prompt;

import org.springframework.util.StringUtils;

public final class DiscussionPromptTemplates {

	private DiscussionPromptTemplates() {
	}

	public static String analysisUserPrompt(String topic, String triggerNodeContext) {
		return """
			Round 1 - 도메인 관점 독립 분석

			토론 주제:
			%s

			선택된 지식 노드:
			%s

			위 주제를 자신의 도메인 관점에서 분석하십시오.
			다음 항목을 포함하십시오.
			1. 가능한 원인
			2. 근거로 볼 수 있는 사용자 데이터
			3. 아직 확인이 필요한 점
			4. 사용자가 바로 시도할 수 있는 제안
			""".formatted(topic, contextOrNone(triggerNodeContext));
	}

	public static String rebuttalUserPrompt(String topic, String analysisTranscript) {
		return """
			Round 2 - 교차 도메인 반론

			토론 주제:
			%s

			Round 1 분석 내용:
			%s

			다른 페르소나의 분석을 검토하고 반론하십시오.
			다음 항목을 포함하십시오.
			1. 과도한 추론 또는 근거가 약한 주장
			2. 빠진 변수나 대안적 설명
			3. 자신의 도메인 관점에서 보완해야 할 해석
			""".formatted(topic, analysisTranscript);
	}

	public static String synthesisSystemPrompt() {
		return """
			당신은 멀티 에이전트 토론 결과를 종합하는 오케스트레이터입니다.
			각 페르소나의 분석과 반론을 비교해 사용자에게 실행 가능한 결론을 제공합니다.
			근거가 약한 내용은 단정하지 말고 확인이 필요한 항목으로 분리하십시오.
			""";
	}

	public static String synthesisUserPrompt(String topic, String analysisTranscript, String rebuttalTranscript) {
		return """
			Round 3 - 종합

			토론 주제:
			%s

			Round 1 분석:
			%s

			Round 2 반론:
			%s

			아래 형식을 반드시 지켜 최종 답변을 작성하십시오.

			요약:
			핵심 결론을 3-5문장으로 작성하십시오.

			실행 계획:
			사용자가 바로 실행할 수 있는 행동 항목을 번호 목록으로 작성하십시오.
			""".formatted(topic, analysisTranscript, rebuttalTranscript);
	}

	private static String contextOrNone(String context) {
		if (!StringUtils.hasText(context)) {
			return "선택된 지식 노드 없음";
		}
		return context;
	}
}
```

- [ ] **Step 4: Run prompt tests and verify they pass**

Run:

```bash
./gradlew test --tests com.soma.ai13be.discussion.prompt.DiscussionPromptTemplatesTest
```

Expected: `BUILD SUCCESSFUL`.

- [ ] **Step 5: Commit**

```bash
git add src/main/java/com/soma/ai13be/discussion/prompt/DiscussionPromptTemplates.java \
  src/test/java/com/soma/ai13be/discussion/prompt/DiscussionPromptTemplatesTest.java
git commit -m "feat: 토론 라운드 프롬프트 추가"
```

## Task 3: Service Orchestration

**Files:**
- Create: `src/main/java/com/soma/ai13be/discussion/service/DiscussionService.java`
- Test: `src/test/java/com/soma/ai13be/discussion/service/DiscussionServiceTest.java`

- [ ] **Step 1: Write failing service tests**

Create `src/test/java/com/soma/ai13be/discussion/service/DiscussionServiceTest.java`:

```java
package com.soma.ai13be.discussion.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.util.List;
import java.util.Optional;

import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.test.util.ReflectionTestUtils;

import com.soma.ai13be.common.client.SolarApiClient;
import com.soma.ai13be.common.client.dto.SolarChatMessage;
import com.soma.ai13be.common.client.dto.SolarChatRequest;
import com.soma.ai13be.common.client.dto.SolarChatResponse;
import com.soma.ai13be.common.exception.CustomException;
import com.soma.ai13be.common.exception.ErrorCode;
import com.soma.ai13be.discussion.entity.AgentDiscussion;
import com.soma.ai13be.discussion.entity.AgentDiscussionMessage;
import com.soma.ai13be.discussion.entity.DiscussionRound;
import com.soma.ai13be.discussion.entity.DiscussionStatus;
import com.soma.ai13be.discussion.repository.AgentDiscussionMessageRepository;
import com.soma.ai13be.discussion.repository.AgentDiscussionRepository;
import com.soma.ai13be.knowledge.entity.KnowledgeNode;
import com.soma.ai13be.knowledge.repository.KnowledgeNodeRepository;
import com.soma.ai13be.knowledge.service.KnowledgeContextBuilder;
import com.soma.ai13be.persona.entity.Persona;
import com.soma.ai13be.persona.repository.PersonaRepository;

class DiscussionServiceTest {

	private final AgentDiscussionRepository discussionRepository = org.mockito.Mockito.mock(AgentDiscussionRepository.class);
	private final AgentDiscussionMessageRepository messageRepository = org.mockito.Mockito.mock(AgentDiscussionMessageRepository.class);
	private final PersonaRepository personaRepository = org.mockito.Mockito.mock(PersonaRepository.class);
	private final KnowledgeNodeRepository knowledgeNodeRepository = org.mockito.Mockito.mock(KnowledgeNodeRepository.class);
	private final KnowledgeContextBuilder knowledgeContextBuilder = org.mockito.Mockito.mock(KnowledgeContextBuilder.class);
	private final SolarApiClient solarApiClient = org.mockito.Mockito.mock(SolarApiClient.class);

	private final DiscussionService service = new DiscussionService(
		discussionRepository,
		messageRepository,
		personaRepository,
		knowledgeNodeRepository,
		knowledgeContextBuilder,
		solarApiClient
	);

	@Test
	void runsThreeRoundDiscussionWithSelectedPersonas() {
		Persona health = persona("health");
		Persona study = persona("study");
		KnowledgeNode node = node("피로 기록", "최근 5시간 수면");

		when(knowledgeNodeRepository.findById(1L)).thenReturn(Optional.of(node));
		when(personaRepository.findAllById(List.of(1L, 2L))).thenReturn(List.of(health, study));
		when(discussionRepository.save(any(AgentDiscussion.class))).thenAnswer(inv -> inv.getArgument(0));
		when(messageRepository.save(any(AgentDiscussionMessage.class))).thenAnswer(inv -> inv.getArgument(0));
		when(knowledgeContextBuilder.buildContextMessage("health")).thenReturn(Optional.of(SolarChatMessage.system("health context")));
		when(knowledgeContextBuilder.buildContextMessage("study")).thenReturn(Optional.empty());
		when(solarApiClient.chatCompletion(any(SolarChatRequest.class)))
			.thenReturn(response("health analysis"))
			.thenReturn(response("study analysis"))
			.thenReturn(response("health rebuttal"))
			.thenReturn(response("study rebuttal"))
			.thenReturn(response("요약:\n수면과 학습 부담이 함께 작용했습니다.\n\n실행 계획:\n1. 수면 시간을 기록합니다."));

		AgentDiscussion discussion = service.createDiscussion(" 피로 원인 분석 ", 1L, List.of(1L, 2L));

		assertThat(discussion.getStatus()).isEqualTo(DiscussionStatus.COMPLETED);
		assertThat(discussion.getTitle()).isEqualTo("피로 원인 분석");
		assertThat(discussion.getTriggerNode()).isEqualTo(node);
		assertThat(discussion.getSummary()).contains("수면과 학습 부담");
		assertThat(discussion.getActionPlan()).contains("수면 시간을 기록");

		ArgumentCaptor<AgentDiscussionMessage> messageCaptor = ArgumentCaptor.forClass(AgentDiscussionMessage.class);
		verify(messageRepository, org.mockito.Mockito.times(5)).save(messageCaptor.capture());
		assertThat(messageCaptor.getAllValues())
			.extracting(AgentDiscussionMessage::getRound)
			.containsExactly(
				DiscussionRound.ANALYSIS,
				DiscussionRound.ANALYSIS,
				DiscussionRound.REBUTTAL,
				DiscussionRound.REBUTTAL,
				DiscussionRound.SYNTHESIS
			);
	}

	@Test
	void usesAllEnabledPersonasWhenPersonaIdsAreMissing() {
		Persona health = persona("health");
		Persona study = persona("study");
		when(personaRepository.findByEnabledTrueOrderByDomainNameAsc()).thenReturn(List.of(health, study));
		when(discussionRepository.save(any(AgentDiscussion.class))).thenAnswer(inv -> inv.getArgument(0));
		when(messageRepository.save(any(AgentDiscussionMessage.class))).thenAnswer(inv -> inv.getArgument(0));
		when(knowledgeContextBuilder.buildContextMessage(any())).thenReturn(Optional.empty());
		when(solarApiClient.chatCompletion(any(SolarChatRequest.class)))
			.thenReturn(response("health analysis"))
			.thenReturn(response("study analysis"))
			.thenReturn(response("health rebuttal"))
			.thenReturn(response("study rebuttal"))
			.thenReturn(response("요약:\n최종 요약\n\n실행 계획:\n1. 행동"));

		AgentDiscussion discussion = service.createDiscussion("주제", null, null);

		assertThat(discussion.getStatus()).isEqualTo(DiscussionStatus.COMPLETED);
		verify(personaRepository).findByEnabledTrueOrderByDomainNameAsc();
	}

	@Test
	void rejectsBlankTopic() {
		assertThatThrownBy(() -> service.createDiscussion(" ", null, List.of(1L, 2L)))
			.isInstanceOf(CustomException.class)
			.hasFieldOrPropertyWithValue("errorCode", ErrorCode.INVALID_REQUEST)
			.hasMessageContaining("topic");
	}

	@Test
	void rejectsWhenLessThanTwoPersonasParticipate() {
		when(personaRepository.findAllById(List.of(1L))).thenReturn(List.of(persona("health")));

		assertThatThrownBy(() -> service.createDiscussion("주제", null, List.of(1L)))
			.isInstanceOf(CustomException.class)
			.hasFieldOrPropertyWithValue("errorCode", ErrorCode.INVALID_REQUEST)
			.hasMessageContaining("at least 2");
	}

	@Test
	void rejectsMissingPersonaId() {
		when(personaRepository.findAllById(List.of(1L, 99L))).thenReturn(List.of(persona("health")));

		assertThatThrownBy(() -> service.createDiscussion("주제", null, List.of(1L, 99L)))
			.isInstanceOf(CustomException.class)
			.hasFieldOrPropertyWithValue("errorCode", ErrorCode.PERSONA_NOT_FOUND)
			.hasMessageContaining("99");
	}

	@Test
	void rejectsMissingKnowledgeNode() {
		when(knowledgeNodeRepository.findById(99L)).thenReturn(Optional.empty());

		assertThatThrownBy(() -> service.createDiscussion("주제", 99L, List.of(1L, 2L)))
			.isInstanceOf(CustomException.class)
			.hasFieldOrPropertyWithValue("errorCode", ErrorCode.KNOWLEDGE_NODE_NOT_FOUND)
			.hasMessageContaining("99");
	}

	@Test
	void rejectsEmptySolarResponse() {
		Persona health = persona("health");
		Persona study = persona("study");
		when(personaRepository.findAllById(List.of(1L, 2L))).thenReturn(List.of(health, study));
		when(discussionRepository.save(any(AgentDiscussion.class))).thenAnswer(inv -> inv.getArgument(0));
		when(knowledgeContextBuilder.buildContextMessage(any())).thenReturn(Optional.empty());
		when(solarApiClient.chatCompletion(any(SolarChatRequest.class))).thenReturn(emptyResponse());

		assertThatThrownBy(() -> service.createDiscussion("주제", null, List.of(1L, 2L)))
			.isInstanceOf(CustomException.class)
			.hasFieldOrPropertyWithValue("errorCode", ErrorCode.SOLAR_RESPONSE_EMPTY);
	}

	@Test
	void returnsDiscussionMessagesInStoredOrder() {
		AgentDiscussion discussion = AgentDiscussion.builder()
			.title("주제")
			.status(DiscussionStatus.COMPLETED)
			.summary("요약")
			.actionPlan("실행")
			.build();
		AgentDiscussionMessage message = AgentDiscussionMessage.builder()
			.discussion(discussion)
			.persona(persona("health"))
			.round(DiscussionRound.ANALYSIS)
			.content("분석")
			.build();
		when(discussionRepository.findById(1L)).thenReturn(Optional.of(discussion));
		when(messageRepository.findByDiscussionOrderByCreatedAtAscIdAsc(discussion)).thenReturn(List.of(message));

		List<AgentDiscussionMessage> messages = service.getMessages(1L);

		assertThat(messages).containsExactly(message);
	}

	private Persona persona(String domainName) {
		Persona persona = Persona.builder()
			.domainName(domainName)
			.name(domainName + " Persona")
			.systemPrompt(domainName + " prompt")
			.builtIn(false)
			.enabled(true)
			.build();
		long id = switch (domainName) {
			case "health" -> 1L;
			case "study" -> 2L;
			default -> 3L;
		};
		ReflectionTestUtils.setField(persona, "id", id);
		return persona;
	}

	private KnowledgeNode node(String title, String content) {
		KnowledgeNode node = KnowledgeNode.builder()
			.title(title)
			.content(content)
			.domainName("health")
			.nodeType("symptom")
			.analyzed(true)
			.build();
		ReflectionTestUtils.setField(node, "id", 1L);
		return node;
	}

	private SolarChatResponse response(String content) {
		return new SolarChatResponse(
			"chatcmpl-test",
			"chat.completion",
			1710000000L,
			"solar-pro3",
			List.of(new SolarChatResponse.Choice(0, SolarChatMessage.assistant(content), "stop")),
			new SolarChatResponse.Usage(5, 10, 15)
		);
	}

	private SolarChatResponse emptyResponse() {
		return new SolarChatResponse(
			"chatcmpl-test",
			"chat.completion",
			1710000000L,
			"solar-pro3",
			List.of(new SolarChatResponse.Choice(0, null, "stop")),
			new SolarChatResponse.Usage(5, 0, 5)
		);
	}
}
```

- [ ] **Step 2: Run service tests and verify they fail**

Run:

```bash
./gradlew test --tests com.soma.ai13be.discussion.service.DiscussionServiceTest
```

Expected: FAIL because `DiscussionService` does not exist.

- [ ] **Step 3: Implement discussion service**

Create `src/main/java/com/soma/ai13be/discussion/service/DiscussionService.java`:

```java
package com.soma.ai13be.discussion.service;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Optional;
import java.util.Set;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import com.soma.ai13be.common.client.SolarApiClient;
import com.soma.ai13be.common.client.dto.SolarChatMessage;
import com.soma.ai13be.common.client.dto.SolarChatRequest;
import com.soma.ai13be.common.exception.CustomException;
import com.soma.ai13be.common.exception.ErrorCode;
import com.soma.ai13be.discussion.entity.AgentDiscussion;
import com.soma.ai13be.discussion.entity.AgentDiscussionMessage;
import com.soma.ai13be.discussion.entity.DiscussionRound;
import com.soma.ai13be.discussion.entity.DiscussionStatus;
import com.soma.ai13be.discussion.prompt.DiscussionPromptTemplates;
import com.soma.ai13be.discussion.repository.AgentDiscussionMessageRepository;
import com.soma.ai13be.discussion.repository.AgentDiscussionRepository;
import com.soma.ai13be.knowledge.entity.KnowledgeNode;
import com.soma.ai13be.knowledge.repository.KnowledgeNodeRepository;
import com.soma.ai13be.knowledge.service.KnowledgeContextBuilder;
import com.soma.ai13be.persona.entity.Persona;
import com.soma.ai13be.persona.repository.PersonaRepository;

import lombok.RequiredArgsConstructor;

@Service
@RequiredArgsConstructor
public class DiscussionService {

	private static final double DISCUSSION_TEMPERATURE = 0.4;
	private static final int DISCUSSION_MAX_TOKENS = 1200;

	private final AgentDiscussionRepository discussionRepository;
	private final AgentDiscussionMessageRepository messageRepository;
	private final PersonaRepository personaRepository;
	private final KnowledgeNodeRepository knowledgeNodeRepository;
	private final KnowledgeContextBuilder knowledgeContextBuilder;
	private final SolarApiClient solarApiClient;

	@Transactional
	public AgentDiscussion createDiscussion(String topic, Long knowledgeNodeId, List<Long> personaIds) {
		String normalizedTopic = normalizeTopic(topic);
		KnowledgeNode triggerNode = resolveTriggerNode(knowledgeNodeId);
		List<Persona> personas = resolvePersonas(personaIds);

		AgentDiscussion discussion = discussionRepository.save(AgentDiscussion.builder()
			.triggerNode(triggerNode)
			.status(DiscussionStatus.REQUESTED)
			.title(normalizedTopic)
			.build());
		discussion.markRunning();

		try {
			List<AgentDiscussionMessage> analyses = runAnalysisRound(discussion, normalizedTopic, triggerNode, personas);
			List<AgentDiscussionMessage> rebuttals = runRebuttalRound(discussion, normalizedTopic, personas, analyses);
			AgentDiscussionMessage synthesis = runSynthesisRound(discussion, normalizedTopic, analyses, rebuttals);
			DiscussionSummary summary = parseSynthesis(synthesis.getContent());
			discussion.markCompleted(summary.summary(), summary.actionPlan());
			return discussion;
		} catch (RuntimeException ex) {
			discussion.markFailed(ex.getMessage());
			throw ex;
		}
	}

	@Transactional(readOnly = true)
	public AgentDiscussion getDiscussion(Long discussionId) {
		return discussionRepository.findById(discussionId)
			.orElseThrow(() -> new CustomException(ErrorCode.DISCUSSION_NOT_FOUND, "Discussion not found: " + discussionId));
	}

	@Transactional(readOnly = true)
	public List<AgentDiscussionMessage> getMessages(Long discussionId) {
		AgentDiscussion discussion = getDiscussion(discussionId);
		return messageRepository.findByDiscussionOrderByCreatedAtAscIdAsc(discussion);
	}

	private List<AgentDiscussionMessage> runAnalysisRound(
		AgentDiscussion discussion,
		String topic,
		KnowledgeNode triggerNode,
		List<Persona> personas
	) {
		List<AgentDiscussionMessage> messages = new ArrayList<>();
		String triggerNodeContext = formatTriggerNode(triggerNode);
		for (Persona persona : personas) {
			List<SolarChatMessage> requestMessages = personaMessages(persona);
			knowledgeContextBuilder.buildContextMessage(persona.getDomainName()).ifPresent(requestMessages::add);
			requestMessages.add(SolarChatMessage.user(DiscussionPromptTemplates.analysisUserPrompt(topic, triggerNodeContext)));
			String content = callSolar(requestMessages);
			messages.add(saveMessage(discussion, persona, DiscussionRound.ANALYSIS, content));
		}
		return messages;
	}

	private List<AgentDiscussionMessage> runRebuttalRound(
		AgentDiscussion discussion,
		String topic,
		List<Persona> personas,
		List<AgentDiscussionMessage> analyses
	) {
		List<AgentDiscussionMessage> messages = new ArrayList<>();
		String analysisTranscript = formatTranscript(analyses);
		for (Persona persona : personas) {
			List<SolarChatMessage> requestMessages = personaMessages(persona);
			requestMessages.add(SolarChatMessage.user(DiscussionPromptTemplates.rebuttalUserPrompt(topic, analysisTranscript)));
			String content = callSolar(requestMessages);
			messages.add(saveMessage(discussion, persona, DiscussionRound.REBUTTAL, content));
		}
		return messages;
	}

	private AgentDiscussionMessage runSynthesisRound(
		AgentDiscussion discussion,
		String topic,
		List<AgentDiscussionMessage> analyses,
		List<AgentDiscussionMessage> rebuttals
	) {
		List<SolarChatMessage> requestMessages = List.of(
			SolarChatMessage.system(DiscussionPromptTemplates.synthesisSystemPrompt()),
			SolarChatMessage.user(DiscussionPromptTemplates.synthesisUserPrompt(
				topic,
				formatTranscript(analyses),
				formatTranscript(rebuttals)
			))
		);
		String content = callSolar(requestMessages);
		return saveMessage(discussion, null, DiscussionRound.SYNTHESIS, content);
	}

	private AgentDiscussionMessage saveMessage(
		AgentDiscussion discussion,
		Persona persona,
		DiscussionRound round,
		String content
	) {
		return messageRepository.save(AgentDiscussionMessage.builder()
			.discussion(discussion)
			.persona(persona)
			.round(round)
			.content(content)
			.build());
	}

	private String callSolar(List<SolarChatMessage> messages) {
		SolarChatRequest request = new SolarChatRequest(messages, DISCUSSION_TEMPERATURE, DISCUSSION_MAX_TOKENS);
		String content = solarApiClient.chatCompletion(request).firstContent();
		if (!StringUtils.hasText(content)) {
			throw new CustomException(ErrorCode.SOLAR_RESPONSE_EMPTY, "Solar API returned empty response");
		}
		return content.strip();
	}

	private List<SolarChatMessage> personaMessages(Persona persona) {
		List<SolarChatMessage> messages = new ArrayList<>();
		if (StringUtils.hasText(persona.getSystemPrompt())) {
			messages.add(SolarChatMessage.system(persona.getSystemPrompt()));
		}
		return messages;
	}

	private String normalizeTopic(String topic) {
		if (!StringUtils.hasText(topic)) {
			throw new CustomException(ErrorCode.INVALID_REQUEST, "topic must not be blank");
		}
		return topic.strip();
	}

	private KnowledgeNode resolveTriggerNode(Long knowledgeNodeId) {
		if (knowledgeNodeId == null) {
			return null;
		}
		return knowledgeNodeRepository.findById(knowledgeNodeId)
			.orElseThrow(() -> new CustomException(ErrorCode.KNOWLEDGE_NODE_NOT_FOUND, "Knowledge node not found: " + knowledgeNodeId));
	}

	private List<Persona> resolvePersonas(List<Long> personaIds) {
		List<Persona> personas;
		if (personaIds == null || personaIds.isEmpty()) {
			personas = personaRepository.findByEnabledTrueOrderByDomainNameAsc();
		} else {
			personas = personaRepository.findAllById(personaIds);
			validateAllPersonaIdsExist(personaIds, personas);
		}

		if (personas.size() < 2) {
			throw new CustomException(ErrorCode.INVALID_REQUEST, "discussion requires at least 2 personas");
		}
		return personas;
	}

	private void validateAllPersonaIdsExist(List<Long> requestedIds, List<Persona> personas) {
		Set<Long> foundIds = new HashSet<>();
		for (Persona persona : personas) {
			if (persona.getId() != null) {
				foundIds.add(persona.getId());
			}
		}

		List<Long> missingIds = requestedIds.stream()
			.distinct()
			.filter(id -> !foundIds.contains(id))
			.toList();

		if (!missingIds.isEmpty()) {
			throw new CustomException(ErrorCode.PERSONA_NOT_FOUND, "Persona not found: " + missingIds);
		}
	}

	private String formatTriggerNode(KnowledgeNode node) {
		if (node == null) {
			return null;
		}
		return "제목: %s%n도메인: %s%n유형: %s%n내용: %s".formatted(
			node.getTitle(),
			node.getDomainName(),
			node.getNodeType(),
			node.getContent()
		);
	}

	private String formatTranscript(List<AgentDiscussionMessage> messages) {
		StringBuilder sb = new StringBuilder();
		for (AgentDiscussionMessage message : messages) {
			String speaker = Optional.ofNullable(message.getPersona())
				.map(Persona::getName)
				.orElse("Synthesis");
			sb.append("[").append(speaker).append("]\n");
			sb.append(message.getContent()).append("\n\n");
		}
		return sb.toString().strip();
	}

	private DiscussionSummary parseSynthesis(String content) {
		String marker = "실행 계획:";
		int actionIndex = content.indexOf(marker);
		if (actionIndex < 0) {
			return new DiscussionSummary(content, "");
		}

		String summary = content.substring(0, actionIndex)
			.replaceFirst("^요약:\\s*", "")
			.strip();
		String actionPlan = content.substring(actionIndex + marker.length()).strip();
		return new DiscussionSummary(summary, actionPlan);
	}

	private record DiscussionSummary(String summary, String actionPlan) {
	}
}
```

- [ ] **Step 4: Run service tests and verify they pass**

Run:

```bash
./gradlew test --tests com.soma.ai13be.discussion.service.DiscussionServiceTest
```

Expected: `BUILD SUCCESSFUL`.

- [ ] **Step 5: Commit**

```bash
git add src/main/java/com/soma/ai13be/discussion/service/DiscussionService.java \
  src/test/java/com/soma/ai13be/discussion/service/DiscussionServiceTest.java
git commit -m "feat: 토론 오케스트레이션 서비스 추가"
```

## Task 4: DTOs And Controller

**Files:**
- Create: `src/main/java/com/soma/ai13be/discussion/dto/request/CreateDiscussionCommand.java`
- Create: `src/main/java/com/soma/ai13be/discussion/dto/response/DiscussionMessageResult.java`
- Create: `src/main/java/com/soma/ai13be/discussion/dto/response/DiscussionResult.java`
- Create: `src/main/java/com/soma/ai13be/discussion/controller/DiscussionController.java`
- Test: `src/test/java/com/soma/ai13be/discussion/controller/DiscussionControllerTest.java`

- [ ] **Step 1: Write failing controller tests**

Create `src/test/java/com/soma/ai13be/discussion/controller/DiscussionControllerTest.java`:

```java
package com.soma.ai13be.discussion.controller;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.util.List;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.test.util.ReflectionTestUtils;

import com.soma.ai13be.common.exception.CustomException;
import com.soma.ai13be.common.exception.ErrorCode;
import com.soma.ai13be.common.exception.GlobalExceptionHandler;
import com.soma.ai13be.discussion.entity.AgentDiscussion;
import com.soma.ai13be.discussion.entity.AgentDiscussionMessage;
import com.soma.ai13be.discussion.entity.DiscussionRound;
import com.soma.ai13be.discussion.entity.DiscussionStatus;
import com.soma.ai13be.discussion.service.DiscussionService;
import com.soma.ai13be.knowledge.entity.KnowledgeNode;
import com.soma.ai13be.persona.entity.Persona;

class DiscussionControllerTest {

	private final DiscussionService discussionService = org.mockito.Mockito.mock(DiscussionService.class);
	private final MockMvc mockMvc = MockMvcBuilders.standaloneSetup(new DiscussionController(discussionService))
		.setControllerAdvice(new GlobalExceptionHandler())
		.build();

	@Test
	void createsDiscussion() throws Exception {
		AgentDiscussion discussion = completedDiscussion(node());
		when(discussionService.createDiscussion("피로 원인 분석", 1L, List.of(1L, 2L))).thenReturn(discussion);
		when(discussionService.getMessages(1L)).thenReturn(List.of(message(discussion, persona("health"), DiscussionRound.ANALYSIS, "건강 분석")));

		mockMvc.perform(post("/api/discussions")
				.contentType(MediaType.APPLICATION_JSON)
				.content("""
					{
					  "topic": "피로 원인 분석",
					  "knowledgeNodeId": 1,
					  "personaIds": [1, 2]
					}
					"""))
			.andExpect(status().isCreated())
			.andExpect(jsonPath("$.status").value("COMPLETED"))
			.andExpect(jsonPath("$.title").value("피로 원인 분석"))
			.andExpect(jsonPath("$.summary").value("최종 요약"))
			.andExpect(jsonPath("$.actionPlan").value("1. 실행"))
			.andExpect(jsonPath("$.messages[0].round").value("ANALYSIS"))
			.andExpect(jsonPath("$.messages[0].content").value("건강 분석"));
	}

	@Test
	void returnsBadRequestWhenTopicIsBlank() throws Exception {
		when(discussionService.createDiscussion(any(), any(), any()))
			.thenThrow(new CustomException(ErrorCode.INVALID_REQUEST, "topic must not be blank"));

		mockMvc.perform(post("/api/discussions")
				.contentType(MediaType.APPLICATION_JSON)
				.content("""
					{
					  "topic": " "
					}
					"""))
			.andExpect(status().isBadRequest())
			.andExpect(jsonPath("$.code").value("INVALID_REQUEST"));
	}

	@Test
	void returnsNotFoundWhenDiscussionDoesNotExist() throws Exception {
		when(discussionService.getDiscussion(99L))
			.thenThrow(new CustomException(ErrorCode.DISCUSSION_NOT_FOUND, "Discussion not found: 99"));

		mockMvc.perform(get("/api/discussions/{discussionId}", 99L))
			.andExpect(status().isNotFound())
			.andExpect(jsonPath("$.code").value("DISCUSSION_NOT_FOUND"))
			.andExpect(jsonPath("$.message").value("Discussion not found: 99"));
	}

	@Test
	void returnsDiscussionDetail() throws Exception {
		AgentDiscussion discussion = completedDiscussion(node());
		when(discussionService.getDiscussion(1L)).thenReturn(discussion);
		when(discussionService.getMessages(1L)).thenReturn(List.of(message(discussion, persona("study"), DiscussionRound.REBUTTAL, "학업 반론")));

		mockMvc.perform(get("/api/discussions/{discussionId}", 1L))
			.andExpect(status().isOk())
			.andExpect(jsonPath("$.status").value("COMPLETED"))
			.andExpect(jsonPath("$.messages[0].personaName").value("study Persona"))
			.andExpect(jsonPath("$.messages[0].round").value("REBUTTAL"));
	}

	@Test
	void returnsDiscussionMessages() throws Exception {
		AgentDiscussion discussion = completedDiscussion(null);
		when(discussionService.getMessages(1L)).thenReturn(List.of(
			message(discussion, persona("health"), DiscussionRound.ANALYSIS, "건강 분석"),
			message(discussion, null, DiscussionRound.SYNTHESIS, "종합")
		));

		mockMvc.perform(get("/api/discussions/{discussionId}/messages", 1L))
			.andExpect(status().isOk())
			.andExpect(jsonPath("$[0].personaName").value("health Persona"))
			.andExpect(jsonPath("$[1].personaName").doesNotExist())
			.andExpect(jsonPath("$[1].round").value("SYNTHESIS"));
	}

	private AgentDiscussion completedDiscussion(KnowledgeNode node) {
		AgentDiscussion discussion = AgentDiscussion.builder()
			.triggerNode(node)
			.status(DiscussionStatus.COMPLETED)
			.title("피로 원인 분석")
			.summary("최종 요약")
			.actionPlan("1. 실행")
			.build();
		ReflectionTestUtils.setField(discussion, "id", 1L);
		return discussion;
	}

	private AgentDiscussionMessage message(AgentDiscussion discussion, Persona persona, DiscussionRound round, String content) {
		AgentDiscussionMessage message = AgentDiscussionMessage.builder()
			.discussion(discussion)
			.persona(persona)
			.round(round)
			.content(content)
			.build();
		ReflectionTestUtils.setField(message, "id", 1L);
		return message;
	}

	private Persona persona(String domain) {
		Persona persona = Persona.builder()
			.domainName(domain)
			.name(domain + " Persona")
			.systemPrompt(domain + " prompt")
			.builtIn(false)
			.enabled(true)
			.build();
		long id = switch (domain) {
			case "health" -> 1L;
			case "study" -> 2L;
			default -> 3L;
		};
		ReflectionTestUtils.setField(persona, "id", id);
		return persona;
	}

	private KnowledgeNode node() {
		KnowledgeNode node = KnowledgeNode.builder()
			.title("피로 기록")
			.content("최근 피곤함")
			.domainName("health")
			.nodeType("symptom")
			.analyzed(true)
			.build();
		ReflectionTestUtils.setField(node, "id", 1L);
		return node;
	}
}
```

- [ ] **Step 2: Run controller tests and verify they fail**

Run:

```bash
./gradlew test --tests com.soma.ai13be.discussion.controller.DiscussionControllerTest
```

Expected: FAIL because controller and DTOs do not exist.

- [ ] **Step 3: Create request DTO**

Create `src/main/java/com/soma/ai13be/discussion/dto/request/CreateDiscussionCommand.java`:

```java
package com.soma.ai13be.discussion.dto.request;

import java.util.List;

import io.swagger.v3.oas.annotations.media.Schema;

@Schema(description = "토론 생성 요청")
public record CreateDiscussionCommand(
	@Schema(description = "토론 주제", example = "요즘 피곤한 이유를 건강과 학업 관점에서 분석해줘")
	String topic,

	@Schema(description = "토론의 근거로 사용할 지식 노드 ID. 없으면 주제만으로 토론합니다.", example = "1", nullable = true)
	Long knowledgeNodeId,

	@Schema(description = "참여 페르소나 ID 목록. 비어 있으면 활성화된 모든 페르소나가 참여합니다.", example = "[1, 2]", nullable = true)
	List<Long> personaIds
) {
}
```

- [ ] **Step 4: Create message response DTO**

Create `src/main/java/com/soma/ai13be/discussion/dto/response/DiscussionMessageResult.java`:

```java
package com.soma.ai13be.discussion.dto.response;

import java.time.Instant;

import com.soma.ai13be.discussion.entity.AgentDiscussionMessage;

import io.swagger.v3.oas.annotations.media.Schema;

@Schema(description = "토론 라운드 메시지 응답")
public record DiscussionMessageResult(
	@Schema(description = "메시지 ID", example = "10")
	Long id,

	@Schema(description = "페르소나 ID. 서버 합성 메시지는 null입니다.", example = "1", nullable = true)
	Long personaId,

	@Schema(description = "페르소나 이름. 서버 합성 메시지는 null입니다.", example = "health Persona", nullable = true)
	String personaName,

	@Schema(description = "토론 라운드 (ANALYSIS, REBUTTAL, SYNTHESIS)", example = "ANALYSIS")
	String round,

	@Schema(description = "라운드 메시지 내용", example = "건강 관점 분석입니다.")
	String content,

	@Schema(description = "생성 시각")
	Instant createdAt
) {

	public static DiscussionMessageResult from(AgentDiscussionMessage message) {
		return new DiscussionMessageResult(
			message.getId(),
			message.getPersona() != null ? message.getPersona().getId() : null,
			message.getPersona() != null ? message.getPersona().getName() : null,
			message.getRound().name(),
			message.getContent(),
			message.getCreatedAt()
		);
	}
}
```

- [ ] **Step 5: Create discussion response DTO**

Create `src/main/java/com/soma/ai13be/discussion/dto/response/DiscussionResult.java`:

```java
package com.soma.ai13be.discussion.dto.response;

import java.time.Instant;
import java.util.List;

import com.soma.ai13be.discussion.entity.AgentDiscussion;
import com.soma.ai13be.discussion.entity.AgentDiscussionMessage;

import io.swagger.v3.oas.annotations.media.Schema;

@Schema(description = "토론 상세 응답")
public record DiscussionResult(
	@Schema(description = "토론 ID", example = "1")
	Long id,

	@Schema(description = "토론을 트리거한 지식 노드 ID. 주제만으로 시작한 토론은 null입니다.", example = "1", nullable = true)
	Long triggerNodeId,

	@Schema(description = "토론 상태", example = "COMPLETED")
	String status,

	@Schema(description = "토론 제목", example = "요즘 피곤한 이유 분석")
	String title,

	@Schema(description = "최종 요약", example = "수면 부족과 학업 부담이 함께 작용했습니다.")
	String summary,

	@Schema(description = "실행 계획", example = "1. 수면 시간을 기록합니다.")
	String actionPlan,

	@Schema(description = "생성 시각")
	Instant createdAt,

	@Schema(description = "라운드별 메시지")
	List<DiscussionMessageResult> messages
) {

	public static DiscussionResult from(AgentDiscussion discussion, List<AgentDiscussionMessage> messages) {
		return new DiscussionResult(
			discussion.getId(),
			discussion.getTriggerNode() != null ? discussion.getTriggerNode().getId() : null,
			discussion.getStatus().name(),
			discussion.getTitle(),
			discussion.getSummary(),
			discussion.getActionPlan(),
			discussion.getCreatedAt(),
			messages.stream().map(DiscussionMessageResult::from).toList()
		);
	}
}
```

- [ ] **Step 6: Create controller**

Create `src/main/java/com/soma/ai13be/discussion/controller/DiscussionController.java`:

```java
package com.soma.ai13be.discussion.controller;

import java.util.List;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.soma.ai13be.common.dto.ErrorResponse;
import com.soma.ai13be.discussion.dto.request.CreateDiscussionCommand;
import com.soma.ai13be.discussion.dto.response.DiscussionMessageResult;
import com.soma.ai13be.discussion.dto.response.DiscussionResult;
import com.soma.ai13be.discussion.entity.AgentDiscussion;
import com.soma.ai13be.discussion.entity.AgentDiscussionMessage;
import com.soma.ai13be.discussion.service.DiscussionService;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.media.ArraySchema;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;

@Tag(name = "Discussion", description = "멀티 페르소나 토론 API")
@RestController
@RequestMapping("/api/discussions")
@RequiredArgsConstructor
public class DiscussionController {

	private final DiscussionService discussionService;

	@Operation(
		summary = "토론 생성 및 실행",
		description = "토론 주제, 선택 지식 노드, 선택 페르소나 목록을 받아 3라운드 토론을 동기식으로 실행합니다."
	)
	@ApiResponses({
		@ApiResponse(responseCode = "201", description = "토론 실행 성공",
			content = @Content(schema = @Schema(implementation = DiscussionResult.class))),
		@ApiResponse(responseCode = "400", description = "topic이 공백이거나 참여 페르소나가 2명 미만",
			content = @Content(schema = @Schema(implementation = ErrorResponse.class))),
		@ApiResponse(responseCode = "404", description = "지식 노드 또는 페르소나를 찾을 수 없음",
			content = @Content(schema = @Schema(implementation = ErrorResponse.class))),
		@ApiResponse(responseCode = "502", description = "Solar API 응답 오류",
			content = @Content(schema = @Schema(implementation = ErrorResponse.class)))
	})
	@PostMapping
	public ResponseEntity<DiscussionResult> createDiscussion(@RequestBody CreateDiscussionCommand command) {
		AgentDiscussion discussion = discussionService.createDiscussion(
			command.topic(),
			command.knowledgeNodeId(),
			command.personaIds()
		);
		List<AgentDiscussionMessage> messages = discussionService.getMessages(discussion.getId());
		return ResponseEntity.status(HttpStatus.CREATED).body(DiscussionResult.from(discussion, messages));
	}

	@Operation(
		summary = "토론 상세 조회",
		description = "토론의 최종 요약, 실행 계획, 라운드별 메시지를 조회합니다."
	)
	@ApiResponses({
		@ApiResponse(responseCode = "200", description = "토론 조회 성공",
			content = @Content(schema = @Schema(implementation = DiscussionResult.class))),
		@ApiResponse(responseCode = "404", description = "토론을 찾을 수 없음",
			content = @Content(schema = @Schema(implementation = ErrorResponse.class)))
	})
	@GetMapping("/{discussionId}")
	public ResponseEntity<DiscussionResult> getDiscussion(
		@Parameter(description = "토론 ID", example = "1")
		@PathVariable Long discussionId
	) {
		AgentDiscussion discussion = discussionService.getDiscussion(discussionId);
		List<AgentDiscussionMessage> messages = discussionService.getMessages(discussionId);
		return ResponseEntity.ok(DiscussionResult.from(discussion, messages));
	}

	@Operation(
		summary = "토론 메시지 조회",
		description = "해당 토론의 라운드별 메시지를 생성 순서대로 조회합니다."
	)
	@ApiResponses({
		@ApiResponse(responseCode = "200", description = "토론 메시지 조회 성공",
			content = @Content(array = @ArraySchema(schema = @Schema(implementation = DiscussionMessageResult.class)))),
		@ApiResponse(responseCode = "404", description = "토론을 찾을 수 없음",
			content = @Content(schema = @Schema(implementation = ErrorResponse.class)))
	})
	@GetMapping("/{discussionId}/messages")
	public ResponseEntity<List<DiscussionMessageResult>> getMessages(
		@Parameter(description = "토론 ID", example = "1")
		@PathVariable Long discussionId
	) {
		List<DiscussionMessageResult> messages = discussionService.getMessages(discussionId).stream()
			.map(DiscussionMessageResult::from)
			.toList();
		return ResponseEntity.ok(messages);
	}
}
```

- [ ] **Step 7: Run controller tests**

Run:

```bash
./gradlew test --tests com.soma.ai13be.discussion.controller.DiscussionControllerTest
```

Expected: `BUILD SUCCESSFUL`.

- [ ] **Step 8: Commit**

```bash
git add src/main/java/com/soma/ai13be/discussion/dto/request/CreateDiscussionCommand.java \
  src/main/java/com/soma/ai13be/discussion/dto/response/DiscussionMessageResult.java \
  src/main/java/com/soma/ai13be/discussion/dto/response/DiscussionResult.java \
  src/main/java/com/soma/ai13be/discussion/controller/DiscussionController.java \
  src/test/java/com/soma/ai13be/discussion/controller/DiscussionControllerTest.java
git commit -m "feat: 토론 API 추가"
```

## Task 5: Final Verification And Swagger Check

**Files:**
- Modify only if tests or Swagger coverage reveal a concrete issue.

- [ ] **Step 1: Run focused discussion tests**

Run:

```bash
./gradlew test --tests 'com.soma.ai13be.discussion.*'
```

Expected: `BUILD SUCCESSFUL`.

- [ ] **Step 2: Run full test suite**

Run:

```bash
./gradlew test
```

Expected: `BUILD SUCCESSFUL`.

- [ ] **Step 3: Verify Swagger annotation coverage manually**

Open `src/main/java/com/soma/ai13be/discussion/controller/DiscussionController.java` and confirm:

- Controller has `@Tag`.
- Each endpoint has `@Operation`.
- Each endpoint has `@ApiResponses`.
- Path variable `discussionId` has `@Parameter`.
- Success response schemas use `DiscussionResult` or `DiscussionMessageResult`.
- Error responses use `ErrorResponse`.
- Request DTO fields have `@Schema` descriptions and examples.

- [ ] **Step 4: Check git status**

Run:

```bash
git status --short
```

Expected: only intentional files are modified; unrelated `serena-extension/` may still be untracked and must not be added.

- [ ] **Step 5: Commit any final fixes**

If Step 1-4 required fixes, commit them:

```bash
git add <only-the-files-fixed-for-discussion>
git commit -m "fix: 토론 기능 검증 보완"
```

If no fixes were needed, skip this commit.

## Self-Review

- Spec coverage: The plan covers the synchronous `POST /api/discussions` flow, optional `knowledgeNodeId`, optional `personaIds`, default active persona selection, 3-round persistence, detail lookup, message lookup, validation errors, Solar empty response handling, and Swagger documentation.
- Scope check: The plan intentionally excludes automatic triggers, async execution, HITL, result node creation, and parallel Solar calls as stated in the design.
- Type consistency: The service method is `createDiscussion(String topic, Long knowledgeNodeId, List<Long> personaIds)` everywhere. DTO fields are `topic`, `knowledgeNodeId`, and `personaIds`. Round enum values match the existing `DiscussionRound` enum.
- Placeholder scan: No task relies on unspecified future work.
