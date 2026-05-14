# 페르소나 채팅 지식 그래프 컨텍스트 주입 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 페르소나 채팅 시 Solar API 호출에 해당 도메인의 지식 노드를 system 메시지로 주입하여 페르소나가 사용자의 실제 데이터를 바탕으로 응답하게 한다.

**Architecture:** `KnowledgeContextBuilder` 컴포넌트가 도메인별 노드를 최근 15개까지 조회해 system 메시지로 포맷팅한다. `ChatService`는 이 컴포넌트를 주입받아 기존 system 프롬프트 직후, 대화 히스토리 이전에 컨텍스트 메시지를 삽입한다. 노드가 없으면 기존 동작을 그대로 유지한다.

**Tech Stack:** Spring Boot, JPA, Mockito (테스트), Upstage Solar API

---

## 파일 구조

| 상태 | 경로 |
|------|------|
| **신규** | `src/main/java/com/soma/ai13be/knowledge/service/KnowledgeContextBuilder.java` |
| **수정** | `src/main/java/com/soma/ai13be/chat/service/ChatService.java` |
| **신규** | `src/test/java/com/soma/ai13be/knowledge/service/KnowledgeContextBuilderTest.java` |
| **수정** | `src/test/java/com/soma/ai13be/chat/service/ChatServiceTest.java` |

---

### Task 1: KnowledgeContextBuilder 실패 테스트 작성

**Files:**
- Create: `src/test/java/com/soma/ai13be/knowledge/service/KnowledgeContextBuilderTest.java`

- [ ] **Step 1: 테스트 파일 생성**

```java
package com.soma.ai13be.knowledge.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import java.util.List;
import java.util.Optional;
import java.util.stream.IntStream;

import org.junit.jupiter.api.Test;

import com.soma.ai13be.common.client.dto.SolarChatMessage;
import com.soma.ai13be.knowledge.entity.KnowledgeNode;
import com.soma.ai13be.knowledge.repository.KnowledgeNodeRepository;

class KnowledgeContextBuilderTest {

    private final KnowledgeNodeRepository nodeRepository = mock(KnowledgeNodeRepository.class);
    private final KnowledgeContextBuilder builder = new KnowledgeContextBuilder(nodeRepository);

    @Test
    void returnsEmptyWhenNoNodesExist() {
        when(nodeRepository.findByDomainNameOrderByCreatedAtDesc("건강")).thenReturn(List.of());

        Optional<SolarChatMessage> result = builder.buildContextMessage("건강");

        assertThat(result).isEmpty();
    }

    @Test
    void returnsSystemMessageWithFormattedNodes() {
        KnowledgeNode node1 = node("수면 패턴", "하루 5시간 수면");
        KnowledgeNode node2 = node("피로감", "오후에 집중력 저하");
        when(nodeRepository.findByDomainNameOrderByCreatedAtDesc("건강"))
            .thenReturn(List.of(node1, node2));

        Optional<SolarChatMessage> result = builder.buildContextMessage("건강");

        assertThat(result).isPresent();
        SolarChatMessage message = result.get();
        assertThat(message.role()).isEqualTo("system");
        assertThat(message.content()).contains("[사용자 지식 그래프 - 건강 도메인]");
        assertThat(message.content()).contains("수면 패턴");
        assertThat(message.content()).contains("하루 5시간 수면");
        assertThat(message.content()).contains("피로감");
        assertThat(message.content()).contains("오후에 집중력 저하");
    }

    @Test
    void limitsToMostRecent15Nodes() {
        List<KnowledgeNode> twentyNodes = IntStream.rangeClosed(1, 20)
            .mapToObj(i -> node("노드" + i, "내용" + i))
            .toList();
        when(nodeRepository.findByDomainNameOrderByCreatedAtDesc("건강"))
            .thenReturn(twentyNodes);

        Optional<SolarChatMessage> result = builder.buildContextMessage("건강");

        assertThat(result).isPresent();
        String content = result.get().content();
        assertThat(content).contains("노드1");
        assertThat(content).doesNotContain("노드16");
        assertThat(content).doesNotContain("노드20");
    }

    private KnowledgeNode node(String title, String content) {
        return KnowledgeNode.builder()
            .title(title)
            .content(content)
            .domainName("건강")
            .nodeType("USER_INPUT")
            .analyzed(false)
            .build();
    }
}
```

- [ ] **Step 2: 테스트 실행 — 컴파일 에러 확인**

```bash
./gradlew test --tests "com.soma.ai13be.knowledge.service.KnowledgeContextBuilderTest" 2>&1 | tail -20
```

예상 결과: `KnowledgeContextBuilder` 클래스가 없으므로 컴파일 에러

---

### Task 2: KnowledgeContextBuilder 구현

**Files:**
- Create: `src/main/java/com/soma/ai13be/knowledge/service/KnowledgeContextBuilder.java`

- [ ] **Step 1: KnowledgeContextBuilder 구현**

```java
package com.soma.ai13be.knowledge.service;

import java.util.List;
import java.util.Optional;

import org.springframework.stereotype.Component;

import com.soma.ai13be.common.client.dto.SolarChatMessage;
import com.soma.ai13be.knowledge.entity.KnowledgeNode;
import com.soma.ai13be.knowledge.repository.KnowledgeNodeRepository;

import lombok.RequiredArgsConstructor;

@Component
@RequiredArgsConstructor
public class KnowledgeContextBuilder {

    private static final int MAX_NODES = 15;

    private final KnowledgeNodeRepository nodeRepository;

    public Optional<SolarChatMessage> buildContextMessage(String domainName) {
        List<KnowledgeNode> nodes = nodeRepository
            .findByDomainNameOrderByCreatedAtDesc(domainName)
            .stream()
            .limit(MAX_NODES)
            .toList();

        if (nodes.isEmpty()) {
            return Optional.empty();
        }

        return Optional.of(SolarChatMessage.system(formatNodes(domainName, nodes)));
    }

    private String formatNodes(String domainName, List<KnowledgeNode> nodes) {
        StringBuilder sb = new StringBuilder();
        sb.append("[사용자 지식 그래프 - ").append(domainName).append(" 도메인]");
        for (int i = 0; i < nodes.size(); i++) {
            KnowledgeNode node = nodes.get(i);
            sb.append("\n").append(i + 1).append(". 제목: ").append(node.getTitle());
            sb.append("\n   내용: ").append(node.getContent());
        }
        return sb.toString();
    }
}
```

- [ ] **Step 2: 테스트 실행 — 통과 확인**

```bash
./gradlew test --tests "com.soma.ai13be.knowledge.service.KnowledgeContextBuilderTest" 2>&1 | tail -20
```

예상 결과: `BUILD SUCCESSFUL`, 3개 테스트 통과

- [ ] **Step 3: 커밋**

```bash
git add src/main/java/com/soma/ai13be/knowledge/service/KnowledgeContextBuilder.java \
        src/test/java/com/soma/ai13be/knowledge/service/KnowledgeContextBuilderTest.java
git commit -m "feat: KnowledgeContextBuilder 구현 — 도메인별 지식 노드 system 메시지 포맷팅"
```

---

### Task 3: ChatService 실패 테스트 추가

**Files:**
- Modify: `src/test/java/com/soma/ai13be/chat/service/ChatServiceTest.java`

- [ ] **Step 1: 클래스 상단에 KnowledgeContextBuilder mock 필드 추가 및 service 생성자 수정**

`ChatServiceTest.java` 파일에서 아래 두 줄을:

```java
	private final SolarApiClient solarApiClient = org.mockito.Mockito.mock(SolarApiClient.class);
	private final ChatService service = new ChatService(sessionRepository, messageRepository, personaRepository, solarApiClient);
```

다음으로 교체:

```java
	private final SolarApiClient solarApiClient = org.mockito.Mockito.mock(SolarApiClient.class);
	private final com.soma.ai13be.knowledge.service.KnowledgeContextBuilder knowledgeContextBuilder =
		org.mockito.Mockito.mock(com.soma.ai13be.knowledge.service.KnowledgeContextBuilder.class);
	private final ChatService service = new ChatService(sessionRepository, messageRepository, personaRepository, solarApiClient, knowledgeContextBuilder);
```

- [ ] **Step 2: 기존 `includesConversationHistoryInApiRequest` 테스트에 mock 설정 추가**

기존 테스트 `includesConversationHistoryInApiRequest`에서 `when(sessionRepository.findById(1L))...` 바로 아래에 아래 줄 추가:

```java
		when(knowledgeContextBuilder.buildContextMessage("health")).thenReturn(java.util.Optional.empty());
```

- [ ] **Step 3: `sendsFirstMessageAndReturnsAssistantReply` 테스트에도 mock 설정 추가**

해당 테스트의 `when(sessionRepository.findById(1L))...` 바로 아래에 추가:

```java
		when(knowledgeContextBuilder.buildContextMessage("health")).thenReturn(java.util.Optional.empty());
```

- [ ] **Step 4: `assignsSequentialMessageNumbers` 테스트에도 mock 설정 추가**

해당 테스트의 `when(sessionRepository.findById(1L))...` 바로 아래에 추가:

```java
		when(knowledgeContextBuilder.buildContextMessage("health")).thenReturn(java.util.Optional.empty());
```

- [ ] **Step 5: 지식 컨텍스트 주입 검증 테스트 2개 추가 — 클래스 `// ── helpers` 섹션 바로 위에 삽입**

```java
	// ── knowledge context injection ─────────────────────────────────────────────

	@Test
	void injectsKnowledgeContextBetweenSystemPromptAndHistory() {
		ChatSession session = sessionWithPersona("health", "health system prompt");
		when(sessionRepository.findById(1L)).thenReturn(Optional.of(session));
		when(messageRepository.countBySession(session)).thenReturn(0L);
		when(messageRepository.findBySessionOrderBySequenceAsc(session)).thenReturn(List.of());
		when(messageRepository.save(any(ChatMessage.class))).thenAnswer(inv -> inv.getArgument(0));
		when(solarApiClient.chatCompletion(any(SolarChatRequest.class)))
			.thenReturn(solarResponse("답변"));
		when(knowledgeContextBuilder.buildContextMessage("health"))
			.thenReturn(Optional.of(SolarChatMessage.system("[사용자 지식 그래프 - health 도메인]\n1. 제목: 수면\n   내용: 5시간")));

		service.sendMessage(1L, "질문");

		ArgumentCaptor<SolarChatRequest> captor = ArgumentCaptor.forClass(SolarChatRequest.class);
		verify(solarApiClient).chatCompletion(captor.capture());

		List<SolarChatMessage> messages = captor.getValue().messages();
		// system(role) + system(knowledge) + user
		assertThat(messages).hasSize(3);
		assertThat(messages.get(0).role()).isEqualTo("system");
		assertThat(messages.get(0).content()).isEqualTo("health system prompt");
		assertThat(messages.get(1).role()).isEqualTo("system");
		assertThat(messages.get(1).content()).contains("[사용자 지식 그래프 - health 도메인]");
		assertThat(messages.get(2).role()).isEqualTo("user");
		assertThat(messages.get(2).content()).isEqualTo("질문");
	}

	@Test
	void skipsKnowledgeContextWhenNoNodes() {
		ChatSession session = sessionWithPersona("health", "health system prompt");
		when(sessionRepository.findById(1L)).thenReturn(Optional.of(session));
		when(messageRepository.countBySession(session)).thenReturn(0L);
		when(messageRepository.findBySessionOrderBySequenceAsc(session)).thenReturn(List.of());
		when(messageRepository.save(any(ChatMessage.class))).thenAnswer(inv -> inv.getArgument(0));
		when(solarApiClient.chatCompletion(any(SolarChatRequest.class)))
			.thenReturn(solarResponse("답변"));
		when(knowledgeContextBuilder.buildContextMessage("health"))
			.thenReturn(Optional.empty());

		service.sendMessage(1L, "질문");

		ArgumentCaptor<SolarChatRequest> captor = ArgumentCaptor.forClass(SolarChatRequest.class);
		verify(solarApiClient).chatCompletion(captor.capture());

		List<SolarChatMessage> messages = captor.getValue().messages();
		// system(role) + user only
		assertThat(messages).hasSize(2);
		assertThat(messages.get(0).content()).isEqualTo("health system prompt");
		assertThat(messages.get(1).role()).isEqualTo("user");
	}
```

- [ ] **Step 6: 테스트 실행 — 컴파일 에러 확인**

```bash
./gradlew test --tests "com.soma.ai13be.chat.service.ChatServiceTest" 2>&1 | tail -20
```

예상 결과: `ChatService` 생성자 시그니처 불일치로 컴파일 에러

---

### Task 4: ChatService 수정

**Files:**
- Modify: `src/main/java/com/soma/ai13be/chat/service/ChatService.java`

- [ ] **Step 1: import 및 필드 추가**

`ChatService.java`에서 아래 import를 추가:

```java
import com.soma.ai13be.knowledge.service.KnowledgeContextBuilder;
```

`private final SolarApiClient solarApiClient;` 아래에 필드 추가:

```java
	private final KnowledgeContextBuilder knowledgeContextBuilder;
```

- [ ] **Step 2: `callSolarApi()` 수정 — 지식 컨텍스트 메시지 삽입**

기존 `callSolarApi()` 메서드 전체를 아래로 교체:

```java
	private String callSolarApi(ChatSession session, List<ChatMessage> history, ChatMessage userMessage) {
		List<SolarChatMessage> messages = new ArrayList<>();

		Persona persona = session.getPersona();
		if (persona != null && StringUtils.hasText(persona.getSystemPrompt())) {
			messages.add(SolarChatMessage.system(persona.getSystemPrompt()));
		}

		if (persona != null && StringUtils.hasText(persona.getDomainName())) {
			knowledgeContextBuilder.buildContextMessage(persona.getDomainName())
				.ifPresent(messages::add);
		}

		for (ChatMessage msg : history) {
			messages.add(toSolarMessage(msg));
		}
		messages.add(SolarChatMessage.user(userMessage.getContent()));

		SolarChatRequest request = new SolarChatRequest(messages, CHAT_TEMPERATURE, CHAT_MAX_TOKENS);
		return solarApiClient.chatCompletion(request).firstContent();
	}
```

- [ ] **Step 3: 테스트 실행 — 모든 테스트 통과 확인**

```bash
./gradlew test --tests "com.soma.ai13be.chat.service.ChatServiceTest" 2>&1 | tail -20
```

예상 결과: `BUILD SUCCESSFUL`, 모든 테스트 통과

- [ ] **Step 4: 전체 테스트 실행 — 기존 테스트 회귀 없는지 확인**

```bash
./gradlew test 2>&1 | tail -30
```

예상 결과: `BUILD SUCCESSFUL`

- [ ] **Step 5: 커밋**

```bash
git add src/main/java/com/soma/ai13be/chat/service/ChatService.java \
        src/test/java/com/soma/ai13be/chat/service/ChatServiceTest.java
git commit -m "feat: 페르소나 채팅에 지식 그래프 컨텍스트 주입 — KnowledgeContextBuilder 연동"
```
