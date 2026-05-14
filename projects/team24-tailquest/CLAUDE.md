# 24조 — 기술 면접 꼬리질문 생성기

## 하네스: 기술 면접 꼬리질문 생성기 개발팀

**목표:** 기획서(RAG 보강판 v2) 기반 MVP를 BE/FE/LangGraph/QA 4인 팀이 협업해 완료한다. 답변 분석 + 핵심 용어 추출 + RAG 검색 + 꼬리 질문 생성 + HITL 재생성 루프로 구성된 LangGraph 기반 면접 코칭 서비스.

**트리거:** 이 프로젝트의 기능 추가·수정·버그 수정·검증·재실행 요청 시 `tail-question-orchestrator` 스킬을 사용하라. 단순 코드 설명·질문은 직접 응답 가능.

**핵심 스택:**

- Backend: FastAPI + LangGraph + Solar API (Upstage)
- Frontend: Next.js 14 (App Router) + Tailwind + Airbnb 디자인 토큰
- 그래프: analyzer ∥ term_extractor → (knowledge_retriever) → question_generator → evaluator → (human_review)

# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:

- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:

- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:

- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:

- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:

```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

**변경 이력:**
| 날짜 | 변경 내용 | 대상 | 사유 |
|------|----------|------|------|
| 2026-05-03 | 초기 하네스 구성 (BE/FE/LangGraph/QA 4인 팀 + 5개 도메인 스킬 + 오케스트레이터) | 전체 | 사용자 요청: 기획서 기반 프로젝트 완료를 위한 팀 구성 |
| 2026-05-03 | RAG 인입 + knowledge_retriever 노드 + 자료관리 UI 추가 | graph + api/materials + storage/chroma + ingestion + app/materials | 기획서 MVP 4·5·10번 핵심 기능 구현 (md/pdf/GitHub 자료를 면접 컨텍스트로 활용 + 인용 표기) |
| 2026-05-04 | HITL: human_review 노드 + interrupt_before + thread_id 기반 피드백 루프 + FeedbackBar UI | workflow + nodes + api/sessions + components/chat | 기획서 MVP 8번 (Human-in-the-Loop 피드백 재생성). feedback_count 별도 카운터로 evaluator 재시도와 분리 |
| 2026-05-04 | UX 정비: 4-way 피드백→단일 "다음 질문 생성하기"(즉시 재생성), placeholder는 awaiting_feedback일 때 숨김, 같은 도메인 폴백 시 분야 전환 divider 미노출 | components/chat/{next-question-bar,conversation-turn,chat-shell} | 사용자 피드백 — 후보 선택 단계가 번거로움, 1개 도메인 케이스에서 "Spring 분야로 전환" 표기가 어색함 |
| 2026-05-04 | 답변 30자 제한 제거(BE min_length=10→1), Composer "잘 모르겠어요" 단축 버튼, score≥85 우수 답변용 PraiseBubble 추가 | schema.py + components/chat/{composer,chat-shell,conversation-turn,praise-bubble} | 사용자 피드백 — 짧은 답변 차단되는 UX 불편, "모르겠다" 입력 번거로움, 우수 답변에 긍정 피드백 부재 |
| 2026-05-05 | Seed 질문 중복 방지: SeedRequest.exclude_questions + 토픽 키워드 추출 + 자카드 유사도 재시도(3회) + mock 템플릿 폴백 | schema.py + nodes.py(generate_seed_question/\_seed_topic_terms/\_seed_too_similar/\_seed_template_fallback) + lib/api.ts + components/chat/chat-shell.tsx | 사용자 피드백 — "잘 모르겠어요" 후 도메인 1개일 때 seed가 매번 "프로세스/스레드 차이"만 반복. LLM은 표현만 바꿔 회피하므로 명사 토큰 자카드≥0.5면 재시도, 3회 실패 시 mock 템플릿 중 비-중복 후보로 결정적 폴백 |
| 2026-05-09 | 채팅 히스토리(SQLite + 사이드바 + /chat/[sid] readonly) + Tavily 웹검색 fallback(knowledge_retriever_node 내부) + Docker화(BE/FE만, 운영 nginx 무수정) | storage/{db,models}.py + services/session_store.py + api/schemas/session_history.py + api/sessions.py + graph/{nodes,schema,tools/web_search}.py + components/chat/{session-sidebar,chat-shell,analysis-rail,conversation-turn} + lib/api.ts + Dockerfile×2 + docker-compose.{yml,override.yml} + .github/workflows/deploy-* | 사용자 요청 3건 — (1) ChatGPT 식 과거 세션 다시보기 (2) tool-calling으로 RAG 보강 (3) Docker 컨테이너 기반 가동. USE_WEB_SEARCH=false 기본 + 컨테이너 127.0.0.1 바인딩으로 운영 무중단 보장. QA 8/8 PASS, 회귀 7/7 PASS |
