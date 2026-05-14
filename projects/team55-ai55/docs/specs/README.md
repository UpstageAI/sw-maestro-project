# PM 일정관리 Agent — Spec 문서

본 디렉토리는 55조 프로젝트의 AI native 개발을 위한 사양 문서 집합입니다.
원본 기획서: `../[55조]프로젝트 기획서 양식_55조_PM일정관리.pdf`

## 핵심 원칙

1. **결정성 우선**: Task 우선순위와 일정 배치 점수는 순수 함수, LLM은 Task 분해·마일스톤 제안·자연어화 역할만
2. **PM 승인 게이트**: 캘린더 반영, 핵심 Task 정보 수정은 항상 PM 승인 후에만 실행
3. **정량화된 추천**: 모든 추천(우선순위, 일정안, 리스크)은 명시적 rubric + 숫자 점수 + 근거(facts) 1:1 매핑
4. **주관 추론 금지**: "담당자가 게으르다", "이 Task는 쉬워 보인다" 같은 인격/난이도 추정 금지
5. **Schema-First**: 모든 인터페이스는 schema 머지 후 구현 (07-data-contracts)

## 읽는 순서

| 순서 | 문서 | 대상 |
|---|---|---|
| 1 | [00-overview.md](./00-overview.md) | 전원 (필독) |
| 2 | [01-architecture.md](./01-architecture.md) | 전원 |
| 3 | [07-data-contracts.md](./07-data-contracts.md) | 전원 (필독) |
| 4 | [08-roles-and-handoffs.md](./08-roles-and-handoffs.md) | 전원 (필독) |
| 5 | [02-agent-priority-spec.md](./02-agent-priority-spec.md) | Priority 담당 |
| 6 | [03-agent-schedule-spec.md](./03-agent-schedule-spec.md) | Schedule 담당 |
| 7 | [04-agent-risk-spec.md](./04-agent-risk-spec.md) | Risk 담당 |
| 8 | [05-backend-spec.md](./05-backend-spec.md) | Backend 담당 |
| 9 | [06-frontend-spec.md](./06-frontend-spec.md) | Frontend 담당 |

## 팀 구성 (5인)

원본 기획서 기준 참여자: 이준형, 강인화, 박민우, 손의현, 이성은

| 역할 | 담당 모듈 |
|---|---|
| AI Agent #1 (Priority) | Task 분해 + 우선순위 점수 산출 |
| AI Agent #2 (Schedule) | 캘린더 슬롯 배치 + 충돌 검사 |
| AI Agent #3 (Risk) | 마감 리스크 + 담당자 과부하 탐지 |
| Backend | FastAPI 게이트웨이 / Agent 오케스트레이션 / DTO 검증 |
| Frontend | React (or Next.js) UI / localStorage 저장소 / 내부 캘린더 |

상세 협업 인터페이스는 `08-roles-and-handoffs.md` 참조.

## MVP 경계 (한 줄 요약)

PM 1명 단일 계정, **내부 캘린더만** (Google Calendar 연동은 MVP 제외 — 원본 기획서 84행 명시),
localStorage 기반 영속화, FastAPI + Upstage API.
