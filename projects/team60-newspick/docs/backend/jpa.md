# JPA

## 사용 범위

Spring 은 **읽기 위주** 로 DB 에 접근한다 — 쓰기는 대부분 Python AI 파이프라인이 담당.

| 엔티티 | Spring 의 작업 |
|---|---|
| Article | 읽기 (홈 피드/상세). 쓰기는 Python Persistor 노드. |
| Quiz | 읽기 (기사 상세에 포함). 쓰기는 Python QuizGenerator. |
| DailyReport | 읽기 (리포트 페이지). 쓰기는 Python ReportPersistor. |

Spring 은 `embedding` 컬럼을 직접 만질 일이 거의 없다 (벡터 검색은 Python 이 함). JPA 매핑에서는 **읽지도 쓰지도 않는** `@Transient` 또는 `insertable=false, updatable=false` 로 둔다.

## 엔티티 매핑 메모

### Article

```java
@Entity
@Table(name = "articles")
public class Article {

    @Id
    private String id;

    @Column(nullable = false, unique = true)
    private String url;

    @Column(nullable = false)
    private String title;

    @Column(nullable = false)
    private String source;

    @Column(nullable = false)
    private String category;

    @Column(name = "published_at", nullable = false)
    private OffsetDateTime publishedAt;

    @Column(name = "raw_text", columnDefinition = "text")
    private String rawText;

    @Type(JsonBinaryType.class)        // hypersistence-utils 또는 jakarta.persistence 3.2+
    @Column(columnDefinition = "jsonb")
    private List<String> summary;

    @Type(JsonBinaryType.class)
    @Column(columnDefinition = "jsonb")
    private List<String> keywords;

    @Column
    private String importance;

    @Column(columnDefinition = "text")
    private String context;

    @Column(name = "importance_score")
    private Short importanceScore;

    @Column(nullable = false)
    private String status;

    // embedding 은 매핑하지 않음 — Python 전용
    // 필요 시 native query 로 별도 처리

    // ...
}
```

### Quiz

기사 1건당 3문항 — 별도 테이블로 정규화하기보다 **Article 의 jsonb 컬럼**으로 묻는 것이 단순하다 (3주 MVP, 검색 대상 아님).

```java
@Entity
@Table(name = "articles")
public class Article {
    // ...
    @Type(JsonBinaryType.class)
    @Column(columnDefinition = "jsonb")
    private List<QuizItem> quiz;   // [{question, answer, explanation}, ...]
}

public record QuizItem(String question, Boolean answer, String explanation) {}
```

> 별도 `quiz` 테이블이 필요해지면(예: 사용자별 풀이 이력) 그때 분리. MVP 인증 없음 정책상 풀이 이력 자체가 없다.

### DailyReport

```java
@Entity
@Table(name = "daily_reports")
public class DailyReport {

    @Id
    @Column(name = "report_date")
    private LocalDate reportDate;

    @Column(name = "report_updated_at")
    private OffsetDateTime updatedAt;

    @Column(columnDefinition = "text")
    private String briefing;

    @Type(JsonBinaryType.class)
    @Column(columnDefinition = "jsonb")
    private List<FlowItem> flow;          // [{category, text}]

    @Type(JsonBinaryType.class)
    @Column(columnDefinition = "jsonb")
    private TimelineItem headline;        // {articleId, sourceCount, ...}

    @Type(JsonBinaryType.class)
    @Column(columnDefinition = "jsonb")
    private List<TimelineItem> subArticles;

    @Type(JsonBinaryType.class)
    @Column(columnDefinition = "jsonb")
    private List<KeywordWeight> keywords; // [{text, weight}]
}
```

## pgvector 컬럼 처리

Spring 은 `embedding vector(4096)` 을 JPA 매핑하지 않는다. 이유:

1. Spring 이 직접 벡터 검색을 수행할 일이 없음.
2. 4096차원 벡터를 Java 객체로 매핑하면 비용만 들고 쓰임 없음.
3. Hibernate 6 의 vector 지원, pgvector-java 등은 좋은 선택지지만 **MVP 에서는 도입 불요**.

만약 향후 Spring 에서도 벡터 검색을 해야 한다면 그때 `pgvector-java` 또는 Hibernate 6 vector 타입을 도입하고 본 문서를 갱신한다.

## 의존성 (build.gradle)

```groovy
implementation 'org.springframework.boot:spring-boot-starter-data-jpa'
runtimeOnly 'org.postgresql:postgresql'
implementation 'io.hypersistence:hypersistence-utils-hibernate-63:3.9.0'   // jsonb 매핑
```

> hypersistence-utils 는 Hibernate 6.3 호환 버전. Spring Boot 3.4 가 사용하는 Hibernate 버전에 맞춰 조정한다.

## 트랜잭션·격리 수준

- 읽기 위주이므로 `@Transactional(readOnly = true)` 를 서비스 메서드에 부착.
- 쓰기 작업은 Python 이 별도 트랜잭션으로 처리하므로 Spring 쪽 동시성 이슈는 거의 없다.
- 이격 락이 필요한 경우는 `@Lock(LockModeType.PESSIMISTIC_WRITE)` 까지 가지 말고 그 시점에 다시 평가.

## 주의점

- DDL 은 Flyway 가 단독 권한자. `ddl-auto: validate` 로 둬서 JPA 가 임의로 스키마 변경하지 못하게 함.
- jsonb 컬럼의 검색은 GIN 인덱스 별도 정의 필요할 수 있음 — MVP 에서는 풀스캔으로도 충분.
- `embedding` 컬럼은 어떠한 JPA `SELECT *` 에도 포함되지 않도록 `@Column(insertable = false, updatable = false)` + 명시적 SELECT 절 사용.

## 레퍼런스

- Hibernate 6 JSON: https://docs.jboss.org/hibernate/orm/6.6/userguide/html_single/Hibernate_User_Guide.html#json
- hypersistence-utils: https://github.com/vladmihalcea/hypersistence-utils
- pgvector 컬럼 정의: [data/pgvector.md](../data/pgvector.md)
