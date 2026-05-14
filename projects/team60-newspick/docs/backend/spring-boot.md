# Spring Boot

## 선정 이유

- 팀 익숙도(Java 생태계).
- REST API + SSE + DB 접근 모두 네이티브 지원.
- AI 파이프라인은 Python(FastAPI + LangGraph) 으로 분리하므로, Spring 은 **Public API 게이트웨이 + 영속성 계층** 역할에 집중.

## 사용 범위

Spring 이 담당하는 것:

- REST API (홈 피드 / 기사 상세 / 데일리 리포트 / 챗 SSE 프록시 / 수집 트리거)
- DB 접근 (Articles / Quiz / DailyReport)
- Python AI 서비스 호출 (RestClient 동기, WebClient SSE 구독)
- 하단 SSE 게이트웨이 (Python 의 SSE 를 받아 그대로 Next.js 에 전달)
- Flyway 기반 스키마 관리

Spring 이 담당하지 않는 것:

- LLM 호출 (Solar API 직접 호출 X — Python 이 담당)
- 벡터 검색 / 클러스터링 (Python 이 담당)
- 인증/권한 (MVP 는 인증 없음 — [backend/auth.md](auth.md))

## 버전

| 항목 | 값 |
|---|---|
| Spring Boot | 3.4.x (latest stable) |
| Java | 17 (LTS) |
| 빌드 도구 | Gradle (Groovy DSL) |
| 패키지 매니저 | Gradle wrapper (`./gradlew`) |

## 모듈 구조

단일 모듈 (3주 MVP — 멀티모듈은 오버스펙).

```
src/main/java/com/newspick/
├── NewspickApplication.java
├── config/
│   ├── WebConfig.java          # CORS (Next.js dev port)
│   └── PythonAiClientConfig.java # RestClient/WebClient bean
├── article/
│   ├── ArticleController.java   # GET /api/articles, /api/articles/{id}
│   ├── ArticleService.java
│   ├── ArticleRepository.java
│   └── Article.java             # @Entity
├── feed/
│   └── FeedController.java      # GET /api/feed
├── report/
│   ├── ReportController.java    # GET /api/report/today
│   └── DailyReport.java
├── quiz/
│   ├── QuizController.java      # GET 기사별 퀴즈 (현재는 Article 에 임베드)
│   └── Quiz.java
├── pipeline/
│   ├── PipelineController.java  # GET /api/refresh-stream (SSE)
│   └── PythonAiClient.java      # Python FastAPI 호출 (SSE/REST)
└── chat/
    └── ChatController.java      # GET /api/chat-stream (SSE)
```

> Quiz 와 Article 의 관계가 1:N 이므로 Quiz 를 별도 엔티티로 둘지 Article 에 JSON 컬럼으로 묻을지는 [backend/jpa.md](jpa.md) 참조.

## 핵심 의존성 (build.gradle)

```groovy
dependencies {
    // 웹
    implementation 'org.springframework.boot:spring-boot-starter-web'
    implementation 'org.springframework.boot:spring-boot-starter-webflux'  // WebClient (SSE 소비용)

    // DB
    implementation 'org.springframework.boot:spring-boot-starter-data-jpa'
    runtimeOnly 'org.postgresql:postgresql'

    // pgvector 매핑은 Phase B 후반부 결정 (jpa.md)

    // 마이그레이션
    implementation 'org.flywaydb:flyway-core'
    implementation 'org.flywaydb:flyway-database-postgresql'

    // 검증
    implementation 'org.springframework.boot:spring-boot-starter-validation'

    // 개발 편의
    compileOnly 'org.projectlombok:lombok'
    annotationProcessor 'org.projectlombok:lombok'

    // 테스트
    testImplementation 'org.springframework.boot:spring-boot-starter-test'
    testImplementation 'org.testcontainers:postgresql'
}
```

## 설정 파일 (application.yml)

```yaml
spring:
  datasource:
    url: jdbc:postgresql://localhost:5432/newspick
    username: ${DB_USER:newspick}
    password: ${DB_PASSWORD:newspick}
  jpa:
    hibernate:
      ddl-auto: validate   # Flyway 가 스키마 관리, JPA 는 검증만
    properties:
      hibernate.format_sql: true
  flyway:
    enabled: true
    baseline-on-migrate: true

newspick:
  ai-service:
    base-url: ${AI_SERVICE_URL:http://localhost:8000}
    timeout-seconds: 120

server:
  port: 8080
```

## 포트

| 서비스 | 포트 |
|---|---|
| Spring | 8080 |
| Python AI | 8000 |
| Next.js (dev) | 3000 |
| PostgreSQL (Docker) | 5432 |

## 주의점

- LangGraph 의 `astream_events` 결과를 Spring 이 그대로 받아 SSE 로 흘리는 구조. 자세한 흐름은 [backend/sse.md](sse.md) + [architecture/realtime-ui-states.md](../architecture/realtime-ui-states.md).
- 작업환경(노트북·데스크톱) 자주 바뀌는 환경이므로 DB 는 Docker 로만 띄운다 ([infra/docker-compose.md](../infra/docker-compose.md)). Spring 자체는 호스트에서 실행해 IDE 연동·디버깅 우선.
- 로컬 개발 시 `dev` 프로파일에 CORS allowlist 로 `http://localhost:3000` 추가.

## 레퍼런스

- Spring Boot 3.4 Reference: https://docs.spring.io/spring-boot/docs/3.4.x/reference/html/
- SseEmitter: https://docs.spring.io/spring-framework/reference/web/webmvc/mvc-ann-async.html#mvc-ann-async-sse
