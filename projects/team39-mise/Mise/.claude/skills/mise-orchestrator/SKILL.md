---
name: mise-orchestrator
description: "Mise 소설 이미지 생성 서비스 개발 오케스트레이터. 소설 이미지, Mise, 장면 분석, 이미지 생성, Streamlit, LangChain, Gemini, 백엔드 구현, 프론트엔드 구현, 프로젝트 초기 설정, 개발 시작, 코드 작성 요청 시 반드시 이 스킬을 사용. 후속 작업: Mise 결과 수정, 부분 재실행, 업데이트, 보완, 다시 실행, 이전 결과 개선, 백엔드만 다시, 프론트엔드만 수정, 테스트만 실행, API 연동만 수정 요청 시에도 반드시 이 스킬을 사용."
---

# Mise Orchestrator — 소설 이미지 생성 서비스 개발 조율

Mise 프로젝트의 에이전트 팀을 조율하여 소설 텍스트 → 장면 분석 → 이미지 생성 서비스를 구현하는 통합 스킬.

## 실행 모드: 에이전트 팀

## 에이전트 구성

| 팀원 | 에이전트 타입 | 역할 | 스킬 | 출력 |
|------|-------------|------|------|------|
| backend-engineer | general-purpose | 백엔드 구현 (LangChain, Gemini) | mise-backend | `_workspace/{phase}_backend_{artifact}.py` |
| frontend-engineer | general-purpose | 프론트엔드 구현 (Streamlit UI) | mise-frontend | `_workspace/{phase}_frontend_{artifact}.py` |
| qa-engineer | general-purpose | 통합 테스트 및 품질 검증 | (인라인) | `_workspace/{phase}_qa_report.md` |

## 워크플로우

### Phase 0: 컨텍스트 확인 (후속 작업 지원)

기존 산출물 존재 여부를 확인하여 실행 모드를 결정한다:

1. `_workspace/` 디렉토리 존재 여부 확인
2. 실행 모드 결정:
   - **`_workspace/` 미존재** → 초기 실행. Phase 1로 진행
   - **`_workspace/` 존재 + 사용자가 부분 수정 요청** → 부분 재실행. 해당 에이전트만 재호출
   - **`_workspace/` 존재 + 새 입력 제공** → 새 실행. 기존 `_workspace/`를 `_workspace_{YYYYMMDD_HHMMSS}/`로 이동 후 Phase 1 진행
3. 부분 재실행 시: 이전 산출물 경로를 에이전트 프롬프트에 포함

### Phase 1: 준비

1. 기획서 읽기: `prd/[EXT]프로젝트 기획서 양식_39조_소설 이미지 생성 서비스.md`
2. 프로젝트 디렉토리 구조 초기화:
   ```
   mise/
   ├── chains/
   ├── models/
   ├── api/
   ├── prompts/
   └── ...
   ```
3. `_workspace/` 생성
4. `requirements.txt` 생성 (langchain, langchain-google-genai, streamlit, pydantic, python-dotenv, requests)
5. `.env` 템플릿 생성 (API 키 placeholder)
6. `config.py` 생성 (환경 변수 로딩)

### Phase 2: 팀 구성

1. 팀 생성:
   ```
   TeamCreate(
     team_name: "mise-team",
     description: "Mise 소설 이미지 생성 서비스 개발 팀"
   )
   ```

2. 팀원 스폰 (각 `model: "opus"` 명시):
   - backend-engineer: `.claude/agents/backend-engineer.md` 정의 기반
   - frontend-engineer: `.claude/agents/frontend-engineer.md` 정의 기반
   - qa-engineer: `.claude/agents/qa-engineer.md` 정의 기반

3. 작업 등록 (의존성 포함):

   | 작업 ID | 작업명 | 담당 | 의존성 |
   |---------|--------|------|--------|
   | T1 | Pydantic 데이터 모델 정의 | backend-engineer | 없음 |
   | T2 | 장면 요소 추출 프롬프트 템플릿 작성 | backend-engineer | 없음 |
   | T3 | LangChain 장면 추출 체인 구현 | backend-engineer | T1, T2 |
   | T4 | 프롬프트 생성 체인 구현 | backend-engineer | T3 |
   | T5 | Gemini 이미지 생성 API 클라이언트 구현 | backend-engineer | 없음 |
   | T6 | 전체 파이프라인 통합 | backend-engineer | T4, T5 |
   | T7 | Streamlit 메인 레이아웃 구현 | frontend-engineer | T1 |
   | T8 | 텍스트 입력 + 스타일 선택 UI | frontend-engineer | 없음 |
   | T9 | 장면 요소 카드 UI 컴포넌트 | frontend-engineer | T7 |
   | T10 | 이미지 결과 표시 + 보정/재생성 UI | frontend-engineer | T7 |
   | T11 | Session State 관리 구현 | frontend-engineer | T7 |
   | T12 | 백엔드-프론트엔드 통합 연결 | frontend-engineer | T6, T10 |
   | T13 | 통합 테스트 실행 | qa-engineer | T12 |
   | T14 | 엣지 케이스 검증 | qa-engineer | T13 |

### Phase 3: 백엔드 + 프론트엔드 병렬 개발

**실행 방식:** 팀원들이 자체 조율

**병렬 실행 그룹:**
- **그룹 A (backend-engineer):** T1, T2, T5 (독립 작업, 병렬 가능)
- **그룹 B (frontend-engineer):** T8 (독립 작업)

**순차 실행 (의존성 해결 후):**
- T3, T4 → T6 (backend-engineer)
- T7 → T9, T10, T11 (frontend-engineer)

**팀원 간 통신 규칙:**
- backend-engineer은 T1(데이터 모델) 완료 시 frontend-engineer에게 SendMessage로 스키마 공유
- frontend-engineer은 필요한 API 인터페이스를 backend-engineer에게 SendMessage로 요청
- qa-engineer은 T6(파이프라인 통합) 완료 확인 후 테스트 준비

**산출물 저장:**

| 팀원 | 출력 경로 |
|------|----------|
| backend-engineer | `mise/chains/`, `mise/models/`, `mise/api/`, `mise/prompts/`, `mise/config.py` |
| frontend-engineer | `mise/app.py`, `mise/components/` |

**리더 모니터링:**
- 팀원이 유휴 상태가 되면 자동 알림 수신
- 의존성이 해결된 작업을 해당 팀원에게 할당
- 백엔드-프론트엔드 인터페이스 불일치 시 중재

### Phase 4: 통합 및 QA

1. T12: frontend-engineer이 백엔드 파이프라인과 프론트엔드 UI를 연결
2. T13: qa-engineer이 통합 테스트 실행
   - 장면 요소 추출 JSON 스키마 검증
   - API 응답-프론트엔드 데이터 바인딩 일치 확인
   - 엣지 케이스: 빈 입력, 1000자 초과, 특수문자, 비한글
   - 부적절 콘텐츠 필터 동작 확인
3. T14: qa-engineer이 엣지 케이스 검증 및 버그 리포트
4. 버그 발견 시 해당 에이전트에게 SendMessage로 수정 요청
5. 최종 실행 가능한 `mise/` 디렉토리 완성

### Phase 5: 정리

1. 팀원들에게 종료 요청 (SendMessage)
2. 팀 정리 (TeamDelete)
3. `_workspace/` 보존
4. 사용자에게 결과 요약 보고:
   - 구현된 모듈 목록
   - 실행 방법 (`streamlit run mise/app.py`)
   - 필요 환경 변수
   - 알려진 제약사항

## 데이터 흐름

```
[리더] → TeamCreate → [backend-engineer] ←SendMessage→ [frontend-engineer]
                            │                              │
                            ↓                              ↓
                    chains/models/api/               app.py/components/
                    prompts/config.py
                            │                              │
                            └─────── qa-engineer 검증 ──────┘
                                         ↓
                                  통합된 mise/ 디렉토리
```

## 에러 핸들링

| 상황 | 전략 |
|------|------|
| 팀원 1명 실패/중지 | 리더가 감지 → SendMessage로 상태 확인 → 재시작 또는 다른 팀원이 대체 |
| 팀원 과반 실패 | 사용자에게 알리고 진행 여부 확인 |
| 타임아웃 | 현재까지 수집된 부분 결과 사용, 미완료 팀원 종료 |
| 백엔드-프론트엔드 인터페이스 불일치 | 리더가 중재, backend-engineer의 스키마를 기준으로 frontend-engineer 수정 |
| API 키 미설정 | config.py에서 감지 → 안내 메시지와 .env 설정 가이드 |
| QA 버그 리포트 | 해당 에이전트에게 SendMessage 전달, 수정 후 QA 재실행 |

## 테스트 시나리오

### 정상 흐름
1. 사용자가 "Mise 프로젝트 개발 시작" 요청
2. Phase 1에서 프로젝트 구조 초기화 + 기획서 분석
3. Phase 2에서 팀 구성 (3명 팀원 + 14개 작업)
4. Phase 3에서 backend-engineer과 frontend-engineer가 병렬 작업
5. Phase 4에서 qa-engineer이 통합 테스트 수행
6. Phase 5에서 팀 정리
7. 예상 결과: `mise/` 디렉토리에 실행 가능한 Streamlit 앱 생성

### 에러 흐름
1. Phase 3에서 backend-engineer이 Gemini API 연동 실패
2. 리더가 유휴 알림 수신
3. SendMessage로 상태 확인 → API 키 설정 문제 확인
4. .env 가이드 제공 후 재시도
5. 재시도 성공 → Phase 4 진행
6. 재시도 실패 시 mock 모드로 전환, 프롬프트 생성까지만 동작

## 실행 명령

```bash
# 개발 완료 후 실행
cd mise
streamlit run app.py
```
