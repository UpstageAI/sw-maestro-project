# Spring SSE

## 사용 범위

- `/api/refresh-stream` — 홈 진입 시 RSS 수집·AI 요약 진행률 스트리밍
- `/api/chat-stream` — AI 챗 토큰 스트리밍

## 구현 방식

**Spring Web MVC + `SseEmitter`** 사용. WebFlux 는 도입하지 않는다 (학습 곡선·디버깅 비용).

핵심 구조: Python(FastAPI) 의 SSE 를 Spring 이 `WebClient` 로 구독해 `SseEmitter` 로 그대로 흘려보낸다.

```
Browser (EventSource)
   ↓ HTTP/SSE
Spring (SseEmitter)
   ↓ HTTP/SSE 구독 (WebClient)
Python FastAPI (/refresh-stream)
   ↓ astream_events
LangGraph 파이프라인
```

## 의존성

```groovy
implementation 'org.springframework.boot:spring-boot-starter-web'        // SseEmitter
implementation 'org.springframework.boot:spring-boot-starter-webflux'    // WebClient
```

> WebFlux 는 SSE 를 **소비하기 위한** 클라이언트(WebClient)만 사용한다. 컨트롤러는 여전히 MVC.

## 컨트롤러 예시

```java
@RestController
public class PipelineController {

    private final PythonAiClient ai;

    @GetMapping("/api/refresh-stream")
    public SseEmitter refreshStream() {
        SseEmitter emitter = new SseEmitter(120_000L);  // 2분 타임아웃

        ai.streamRefresh()
          .doOnNext(event -> {
              try {
                  emitter.send(SseEmitter.event()
                      .name(event.name())
                      .data(event.data()));
              } catch (IOException e) {
                  emitter.completeWithError(e);
              }
          })
          .doOnComplete(emitter::complete)
          .doOnError(emitter::completeWithError)
          .subscribe();

        return emitter;
    }
}
```

## Python AI 서비스 SSE 구독

```java
@Component
public class PythonAiClient {

    private final WebClient webClient;

    public PythonAiClient(@Value("${newspick.ai-service.base-url}") String baseUrl) {
        this.webClient = WebClient.builder().baseUrl(baseUrl).build();
    }

    public Flux<SseEvent> streamRefresh() {
        return webClient.get()
            .uri("/refresh-stream")
            .accept(MediaType.TEXT_EVENT_STREAM)
            .retrieve()
            .bodyToFlux(new ParameterizedTypeReference<ServerSentEvent<String>>() {})
            .map(sse -> new SseEvent(sse.event(), sse.data()));
    }

    public record SseEvent(String name, String data) {}
}
```

## 이벤트 스키마

[architecture/realtime-ui-states.md](../architecture/realtime-ui-states.md) 의 `step / done / warn / error` 를 그대로 프록시한다. Spring 단에서 변형 X.

## 동시성

- `SseEmitter` 인스턴스는 요청별로 분리. 사용자가 동시에 여러 탭을 열어도 서로 영향 없음.
- 동시 챗 요청 시 Python 호출도 병렬 — Python 측 동시성 처리는 [ai/rag-chat.md](../ai/rag-chat.md).
- Spring 서버는 default 톰캣 풀(200 스레드) 로 충분 (3주 MVP, 시연 동시성 매우 낮음).

## 클라이언트 timeout / 재연결

- 서버 timeout: 120초.
- 클라이언트(Next.js)는 `EventSource` 의 자동 재연결을 활용 (브라우저 기본 동작). 명시적 재연결 로직 추가 X.
- 정상 완료 시 서버가 `event: done` 송신 후 emitter complete → 클라이언트 `EventSource.close()` 명시 호출 ([architecture/realtime-ui-states.md](../architecture/realtime-ui-states.md) 의 프론트 코드 참조).

## 주의점

- `SseEmitter` 의 `send()` 는 IO 스레드를 블록하므로, 무거운 처리는 비동기로 (`CompletableFuture` / Reactor). 위 예시는 WebClient 의 `Flux.subscribe()` 가 별도 스레드에서 push.
- SSE 는 HTTP/1.1 keep-alive 기반. 프록시(nginx 등) 도입 시 `proxy_buffering off` 설정 필요.
- Spring Web MVC + WebFlux 동시 의존 시 `spring.main.web-application-type=servlet` 명시 권장 (자동 감지가 reactive 로 갈 가능성 차단).

## 레퍼런스

- Spring SseEmitter: https://docs.spring.io/spring-framework/reference/web/webmvc/mvc-ann-async.html#mvc-ann-async-sse
- WebClient SSE 소비: https://docs.spring.io/spring-framework/reference/web/webflux-webclient/client-retrieve.html
- Reactor SSE: https://projectreactor.io/docs/core/release/reference/
