# 00. 프로젝트 개요 — PM 일정관리 Agent

## 1. 한 줄 정의
팀/소규모 조직의 Task와 내부 캘린더 일정을 입력받아, **정량화된 우선순위 점수 + 슬롯 배치안 + 마감 리스크 리포트**를 산출하는 PM 보조 Agent.

## 2. 서비스 정의 (사용자 관점)
PM이 프로젝트·Task·팀원 정보를 입력하면, AI가 **어떤 일을 / 누가 / 언제 / 어떤 순서로** 처리해야 하는지 추천하고, **PM이 승인한 항목만** 내부 캘린더에 반영한다.

## 3. 설계 철학 (가장 중요)

본 프로젝트는 "AI native 개발"을 지향한다. 모든 Agent 출력은 **재현 가능 / 검증 가능 / 정량화 가능**해야 하며, 다음 원칙을 따른다.

### 3.1 결정성 우선 (Determinism First)
- **우선순위 점수**, **슬롯 배치 적합도 점수**, **리스크 등급**은 모두 순수 함수(코드)로 계산한다.
- LLM은 다음 3가지 역할에만 사용:
  1. 자유 입력(프로젝트 목표) → 마일스톤/세부 Task **분해 제안**
  2. 사용자에게 보여줄 **자연어 설명** 생성 (facts/numbers를 포장)
  3. 누락 정보(예: 예상 소요시간) 추정 시 **range + confidence** 출력
- 동일 입력 → 동일 출력. LLM 호출은 `temperature=0`, JSON 강제, schema validation.

### 3.2 명시적 제외 영역 (Out-of-Scope)
다음 영역은 본 시스템에서 **다루지 않는다**.

| 제외 항목 | 이유 |
|---|---|
| "담당자가 의욕이 없어 보인다" | 인격 추정, 정량화 불가 |
| "이 Task는 쉬워 보인다" / 자체 난이도 추정 | PM이 입력한 중요도/소요시간만 사용 |
| Google Calendar 양방향 동기화 (생성/수정/삭제) | MVP 제외 — 원본 기획서 84,96행 명시 |
| 외부 메신저(Slack 등) 연동 알림 | MVP 제외 |
| 자동 일정 확정 (PM 승인 없는 캘린더 반영) | 안전 위반 — 항상 PM 승인 게이트 필수 |
| 팀원별 다중 계정 / 권한 관리 | MVP 제외, 단일 PM 계정 |
| 학습/파인튜닝 | 모든 추론은 zero-shot + 결정적 룰 |
| 인간 평가 점수 ("이 PM이 일을 잘한다") | 무관 + 윤리 위험 |

### 3.3 인간 승인 게이트 (Human Approval Gate)
시스템에는 **3개의 명시적 승인 지점**이 있고, Agent는 승인 없이 이 경계를 넘지 않는다.

| 게이트 | 승인 대상 | Agent의 사전 동작 |
|---|---|---|
| G1: 마일스톤 승인 | AI 제안 마일스톤 리스트 | 프로젝트 목표 → 제안만 |
| G2: 일정안 승인 | AI 제안 슬롯 배치 (Task → datetime) | 후보 슬롯 + 충돌 점수 산출 |
| G3: 핵심 정보 변경 | Task 중요도/마감/담당자/예상소요 변경 | Agent는 변경을 **제안만**, PM이 폼에서 직접 입력 |

G2가 본 프로젝트의 안전 핵심: **Agent는 슬롯 후보를 만들지만, 캘린더 INSERT는 PM이 명시 승인한 후에만 일어난다.**

### 3.4 평가 방식 — Score + Checks 혼합
본 시스템은 두 종류의 정량 산출물을 사용한다.

1. **Priority Score** (Task별 0~100): 결정적 가중합 (마감 임박도 + 중요도 + 의존성 + 진척률 + 담당자 부하)
2. **Risk Checks** (프로젝트별 N개 binary): pass / fail / not_applicable로 결정적 판정 + blocker 표시

**점수 산출:**
```
priority(t) = w_d * deadline_pressure(t)
            + w_i * importance(t)
            + w_p * predecessor_pressure(t)
            + w_g * progress_gap(t)
            - w_o * overload_penalty(assignee(t))
clamp [0, 100]
```
가중치는 `04-agent-risk-spec.md`의 기본값 표를 따르며, 변경은 PR 합의 사항.

### 3.5 설명 가능성 (Explainability)
- 모든 Priority Score는 **5개 사실(facts)**로 분해 가능: 남은 일수, 중요도 등급, 미완 선행 수, 진척률 갭, 담당자 동시 진행 수
- 모든 Risk Check는 자기 `evidence_facts`와 `fix_template`을 갖는다 → 사용자에게 보여주는 모든 추천은 1개 이상의 결정적 fact를 인용한다.
- LLM의 자유 서술은 **사실 보고형**으로 제한 (예: "마감까지 1.5일 / 평균 소요 4h / 선행 미완 1건 → 우선순위 87").

## 4. MVP 범위

### 포함 (단계별 로드맵 1~6단계)
- PM 단일 계정 + 프로젝트 1~N개 관리
- 팀원·근무가능시간 입력
- AI 마일스톤 제안 (G1 승인)
- Task CRUD + 의존성 + 진척률 + 지연사유
- **결정적 우선순위 계산** + AI Task 분해/담당자 배정 제안
- AI 슬롯 배치 제안 → PM 승인 (G2) → **내부 캘린더** 반영
- 마감 리스크 / 담당자 과부하 알림
- localStorage 기반 영속화 + FastAPI 백엔드

### 제외
- Google Calendar 양방향 동기화 (조회조차 MVP에서는 제외; 원본 기획서 84행 "외부 캘린더 연동은 MVP 범위에서 제외")
- 다중 계정 / 초대 / 권한
- 자동 알림 (Slack, 이메일, push)
- 모바일 앱 / PWA 오프라인
- 학습 기반 개인화

## 5. 대상 사용자
- 소규모 팀 (2~10명) PM, 캡스톤/프로젝트 팀장
- 1인 PM이 팀원 정보와 Task를 관리하는 구조
- 여러 Task의 마감/우선순위를 머릿속으로 계산하는 데 시간을 쓰는 사용자

## 6. 핵심 가치
> 단순 Task 리스트가 아니라, **현재 Task들의 우선순위와 슬롯 배치를 정량 지표로 판정하고, 마감 리스크/과부하를 사전에 탐지해 PM이 승인할 수 있는 형태의 추천을 제시한다.**

## 7. 성공 지표 (KPI)

| 지표 | 정의 | 측정 방법 | 목표 |
|---|---|---|---|
| Schema Pass Rate | LLM 출력이 schema 검증 통과한 비율 | 서버 로그 | ≥ 98% |
| Priority Reproducibility | 동일 입력 5회 호출 시 priority 점수 표준편차 | 자동 테스트 | **= 0** (결정적 함수) |
| Slot Suggestion Validity | AI 제안 슬롯이 (1) 충돌 없음 (2) 근무가능시간 안 (3) 선행 완료 후 모두 만족 | 자동 테스트 | ≥ 99% |
| Risk Detection Recall | 골든 시나리오의 마감 위험/과부하를 잡아내는 비율 | 골든 셋 | ≥ 90% |
| Latency (P95) | Task 입력 후 추천 화면 표시 | 클라이언트 측정 | ≤ 7초 (LLM 4회 일부 병렬), simulate(hard lane) ≤ 300ms |
| LLM Reranker Safety | Schedule LLM 재정렬이 verify_rerank를 통과한 비율 | 자동 측정 | ≥ 99% |
| Soft Check Hallucination Rate | LLM이 환각 task_id/낮은 confidence로 verify에 차단된 비율 | 자동 측정 | ≤ 10% |
| Suggestion Acceptance | PM이 추천 슬롯/우선순위를 승인한 비율 | 프론트 이벤트 | ≥ 60% |
| Score-Action Coherence | PM이 Risk fix를 적용했을 때 시뮬 priority delta | 자동 검증 | ≥ +5점 |

## 8. 팀 구성 (5인)

원본 기획서 참여자: **이준형, 강인화, 박민우, 손의현, 이성은**.
역할 매핑은 팀 협의에 따라 확정. 본 spec은 5개 단일 책임 모듈로 분리되어 있어 1:1 배정 가능.

| 역할 | 책임 문서 |
|---|---|
| Priority Agent | `02-agent-priority-spec.md` |
| Schedule Agent | `03-agent-schedule-spec.md` |
| Risk Agent | `04-agent-risk-spec.md` |
| Backend | `05-backend-spec.md` |
| Frontend | `06-frontend-spec.md` |

## 9. 문서 맵
```
docs/specs/
├── 00-overview.md              # 본 문서
├── 01-architecture.md          # 시스템 아키텍처 (LangGraph super-graph 포함)
├── 02-agent-priority-spec.md   # Priority Agent
├── 03-agent-schedule-spec.md   # Schedule Agent
├── 04-agent-risk-spec.md       # Risk Agent
├── 05-backend-spec.md          # Backend (FastAPI / 오케스트레이션)
├── 06-frontend-spec.md         # Frontend (React or Next.js)
├── 07-data-contracts.md        # JSON 스키마 / API 계약 (모든 역할 공통)
└── 08-roles-and-handoffs.md    # 역할 분담 / 인터페이스 / 마일스톤
```

## 10. 원본 기획서와의 매핑

| 기획서 항목 | 본 spec 위치 |
|---|---|
| 4가지 핵심 문제 (우선순위 판단/일정 변경/도구 분리/리스크 탐지) | `04-agent-risk-spec.md` Risk Checks + `02-agent-priority-spec.md` |
| Agent 자율 동작 6가지 | `01-architecture.md §2` 시퀀스 |
| PM 승인 필요 2가지 | `00-overview.md §3.3` (G1, G2, G3) |
| MVP 16개 항목 | `08-roles-and-handoffs.md §5` 마일스톤 |
| 6단계 로드맵 | `08-roles-and-handoffs.md §5` 주차 매핑 |
| 제약사항 5가지 | `01-architecture.md §5.2` 실패 처리 |
