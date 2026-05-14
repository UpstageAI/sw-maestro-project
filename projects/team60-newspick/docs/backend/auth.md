# 인증 (Auth)

## MVP 정책: 인증 없음

3주 MVP·로컬 시연 환경에 맞춰 **인증을 도입하지 않는다**. 모든 API 엔드포인트가 공개되며, 사용자 식별·권한 체크 코드를 작성하지 않는다.

## 영향 범위

- [architecture/data-schema.md](../architecture/data-schema.md) 의 `UserActivity` 스키마는 **MVP 미사용**. 향후 확장용 정의로만 보존.
- 데일리 리포트의 "사용자가 읽은 기사" / "퀴즈 정답률" 통계는 생성하지 않는다 ([ai/agents.md](../ai/agents.md) 의 5번 리포트 에이전트 입력에서 사용자 활동 부분은 MVP 범위 밖).
- 챗 대화 히스토리는 **세션 메모리 기반 1인용**. 동시에 여러 사람이 접속하면 서로 보는 히스토리가 섞일 수 있는데, 시연용 1회 수준에선 문제없음.

## Spring Security 도입 여부

도입하지 않는다. `spring-boot-starter-security` 의존성을 추가하면 자동으로 모든 엔드포인트가 401 로 막히므로, 의도치 않게 활성화되지 않도록 주의.

## CORS

인증 없음이지만 dev 환경에서 Next.js dev server (`http://localhost:3000`) 의 cross-origin 요청은 허용해야 한다. 자세한 설정은 [backend/spring-boot.md](spring-boot.md) 의 `WebConfig`.

## 향후 확장 (Phase B 이후)

운영을 전제로 가지 않는 프로젝트라 현 시점 우선순위 0. 만약 도입한다면:

- 익명 세션 UUID 발급 (쿠키 기반) — UserActivity 기록 활성화
- OAuth (구글/GitHub) — Spring Security + spring-security-oauth2-client
- 비밀번호 인증은 도입하지 않는다 (보안 부담만 늘어남)

## 주의점

- 발표 시연 시 외부 IP 노출 X. 로컬 네트워크 안에서만 데모.
- API 키(Solar, LangSmith) 가 환경변수로 백엔드에 보관 — Next.js 에 절대 노출 금지. 챗·수집은 항상 Spring 또는 Python 을 거치게 함.
