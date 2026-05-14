# Two Week Plan

기준 날짜: 2026-05-05부터 2026-05-18까지 14일

## Week 1: 뼈대와 연결

| 날짜 | 목표 | 담당 |
| --- | --- | --- |
| 2026-05-05 | repo 초기화, reference 문서 확정, 역할별 인터페이스 합의 | 전체 |
| 2026-05-06 | FastAPI 기본 서버, Next.js 기본 화면 생성 | Backend, Frontend |
| 2026-05-07 | 단일 LLM 호출로 7개 섹션 JSON 생성 | AI, Backend |
| 2026-05-08 | Frontend에서 mock JSON 표시, API contract 검증 | Frontend, Backend |
| 2026-05-09 | 검색 결과 수집 또는 샘플 근거 fallback 구현 | AI, RAG |
| 2026-05-10 | `/api/generate` 실제 연결, 에러 상태 처리 | Backend, Frontend |
| 2026-05-11 | 발표용 입력 3개로 end-to-end 1차 성공 | 전체 |

## Week 2: 품질과 데모 안정화

| 날짜 | 목표 | 담당 |
| --- | --- | --- |
| 2026-05-12 | 청구항 프롬프트 튜닝, 문체 개선 | AI |
| 2026-05-13 | 특허 문서 스타일 UI 개선, 결과 레이아웃 정리 | Frontend |
| 2026-05-14 | PDF 또는 print fallback 구현 | Backend, Frontend |
| 2026-05-15 | Playwright E2E 테스트 작성 | Playwright |
| 2026-05-16 | 발표 대본, 실패 대비 샘플 결과 고정 | 발표, 기획 |
| 2026-05-17 | 통합 리허설, 버그 수정, scope freeze | 전체 |
| 2026-05-18 | 최종 발표 및 데모 | 전체 |

## 데일리 체크 질문

- 오늘 결과가 발표 화면에서 보이는가?
- API contract가 깨지지 않았는가?
- 실패했을 때 fallback이 있는가?
- 2주 MVP 범위를 벗어난 일을 하고 있지 않은가?

## Scope Freeze 규칙

2026-05-17부터는 새 기능을 추가하지 않습니다. 이 시점부터는 버그 수정, 발표 안정화, 샘플 데이터 고정만 합니다.

