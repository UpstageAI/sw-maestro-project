# 페르소나 채팅 지식 그래프 컨텍스트 주입 설계

## 개요

페르소나 채팅 시 Solar API 호출에 사용자의 개인 지식 그래프 데이터를 컨텍스트로 주입한다.
현재 `ChatService`는 `persona.getSystemPrompt()`만 사용하며 지식 노드를 전혀 참조하지 않는다.
이 기능을 추가하면 페르소나가 사용자의 실제 도메인 데이터를 바탕으로 응답할 수 있게 되고,
이후 토론 오케스트레이터 구현 시 동일한 컴포넌트를 재사용할 수 있다.

---

## 아키텍처

### 새 컴포넌트: `KnowledgeContextBuilder`

- 위치: `knowledge/service/KnowledgeContextBuilder.java`
- 의존성: `KnowledgeNodeRepository`
- 단일 public 메서드:

```java
public Optional<SolarChatMessage> buildContextMessage(String domainName)
```

#### 동작

1. `KnowledgeNodeRepository.findByDomainNameOrderByCreatedAtDesc(domainName)`으로 노드 조회
2. 최근 15개로 제한 (토큰 한도 방어)
3. 노드가 없으면 `Optional.empty()` 반환
4. 노드가 있으면 아래 형식으로 포맷팅 후 `SolarChatMessage.system(...)` 반환

```
[사용자 지식 그래프 - {domainName} 도메인]
1. 제목: {title}
   내용: {content}
2. 제목: {title}
   내용: {content}
...
```

---

### `ChatService` 변경

- `KnowledgeContextBuilder` 주입 추가
- `callSolarApi()` 내부 메시지 조립 순서 변경:

```
[system] persona.systemPrompt        ← 기존 (페르소나 역할)
[system] 사용자 지식 그래프           ← 신규 (노드 있을 때만 추가)
[user/assistant] 대화 히스토리        ← 기존
[user] 현재 메시지                    ← 기존
```

- 노드가 없는 경우(새 사용자, 해당 도메인 노드 미존재) 기존 동작과 동일하게 유지

---

## 결정 사항

| 항목 | 결정 | 이유 |
|------|------|------|
| 노드 범위 | 해당 도메인만 | 페르소나는 자기 도메인 관점으로만 분석 (기획 원칙) |
| 노드 수 상한 | 최근 15개 | 토큰 한도 방어, MVP에서는 전수 조회해도 무방하나 상한 설정 |
| 주입 방식 | 별도 system 메시지 | 역할 프롬프트와 데이터 컨텍스트 분리, 토론에서 재사용 용이 |
| 엣지 포함 여부 | 미포함 | 단순 채팅에서는 노드 텍스트만으로 충분, 토론 시 추가 검토 |

---

## 토론 기능과의 연계

`KnowledgeContextBuilder`는 `ChatService` 외에 토론 오케스트레이터에서도 동일하게 사용한다.
각 도메인 에이전트가 토론 참여 시 자신의 도메인 노드를 컨텍스트로 받는 패턴이 자연스럽게 성립된다.

---

## 변경 범위

- 신규: `KnowledgeContextBuilder.java`
- 수정: `ChatService.java` (의존성 추가, `callSolarApi()` 내부 수정)
- 테스트: `ChatServiceTest.java` (지식 노드 있을 때/없을 때 케이스 추가)
- 테스트: `KnowledgeContextBuilderTest.java` (신규)
