## 하네스: Mise (소설 이미지 생성 서비스)

**목표:** 소설 텍스트를 입력하면 LLM이 장면을 분석하고 이미지 생성 AI용 프롬프트를 만들어 장면 이미지를 생성하는 서비스 구현

**트리거:** Mise, 소설 이미지, 장면 분석, 이미지 생성, Streamlit, LangChain 관련 개발 작업 요청 시 `mise-orchestrator` 스킬을 사용하라. 단순 질문은 직접 응답 가능.

**Git 규칙:** 커밋, 푸시, 브랜치 생성 시 `git-workflow` 스킬을 따르라. main 직접 커밋 금지.

**아키텍처 문서:** `docs/pipeline-architecture.md` — 파이프라인 구조, 노드 상세, 데이터 모델 전체 설명

**현재 구현 상태:**
- 백엔드 파이프라인: LangGraph 기반 5단계 (extract → check_missing → [fill → verify] → prompt)
- 프롬프트 생성까지 구현 완료, 이미지 생성 모듈은 미구현
- 테스트: 38개 단위 테스트 + 5개 통합 테스트 (mock 없이 실제 API 호출)

**파이프라인 핵심 파일:**
| 파일 | 역할 |
|------|------|
| `mise/chains/scene_extractor.py` | LangGraph StateGraph — 노드 5개 + 조건부 엣지 |
| `mise/models/scene_schema.py` | Pydantic 모델 6개 (SceneElements, ExtractionResult, FillResult, VerifyResult, PromptResult, SceneSchema) |
| `mise/prompts/extraction_prompt.py` | 장면 추출용 프롬프트 |
| `mise/prompts/fill_prompt.py` | 누락 보완용 프롬프트 |
| `mise/prompts/verify_prompt.py` | 일관성 검증용 프롬프트 |
| `mise/prompts/prompt_generator.py` | 이미지 프롬프트 생성용 프롬프트 |

**변경 이력:**
| 날짜 | 변경 내용 | 대상 | 사유 |
|------|----------|------|------|
| 2026-05-04 | 초기 구성 | 전체 | - |
| 2026-05-04 | 이미지 생성 API 변경: NVIDIA Sana → Gemini | backend-engineer, mise-backend, mise-orchestrator | 기획 변경 |
| 2026-05-09 | 파이프라인 2단계 → 5단계 확장 (누락 검사, 보완, 검증 추가) | scene_extractor.py, scene_schema.py, prompts/ | 누락 요소 자동 보완 |
| 2026-05-09 | 순차 함수 호출 → LangGraph StateGraph 마이그레이션 | scene_extractor.py | Agentic Workflow 구조화 |
| 2026-05-09 | 조건부 엣지 추가 (누락 시에만 fill/verify 경로) | scene_extractor.py | 불필요한 API 호출 제거 |
