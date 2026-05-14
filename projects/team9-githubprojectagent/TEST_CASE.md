# 테스트 케이스 문서 — GitHub Portfolio Agent

> 최종 업데이트: 2026-05-09 | 담당: QA Engineer  
> 전체 **361개** 테스트 · 통과율 **100%** · 커버리지 **80%**

---

## 빠른 실행

```bash
# 의존성 설치
pip install -r requirements-test.txt

# 전체 테스트 (단위 + 통합 + 성능)
pytest tests/ -q

# 커버리지 포함
pytest tests/ --cov=src --cov-report=term-missing --cov-fail-under=80

# E2E (실제 API 키 필요, 비용 발생)
pytest tests/e2e/ -m e2e -v -s
```

---

## 테스트 구조

```
tests/
├── unit/               # 외부 의존 없는 순수 함수 검증
├── integration/        # API + 오케스트레이터 (LLM 모킹)
├── performance/        # API 응답시간 SLA 검증
└── e2e/                # 실제 API 호출 (CI 제외)
```

---

## 1. 단위 테스트 (Unit)

### 1-1. Session Manager
| TC | 검증 내용 | 기대 결과 |
|----|----------|---------|
| 세션 생성 | `create()` 호출 | ID 12자, 고유값 보장 |
| 세션 조회 | `get(sid)` | 생성한 객체 반환 |
| 없는 세션 조회 | `get("없는ID")` | `None` 반환 |
| 상태 전이 | `set_state(FETCHING)` | state 변경, log 기록 |
| Abort | `request_abort()` | ABORTED 상태, event set |
| Abort 체크 | `check_abort()` 호출 | `RuntimeError` 발생 |
| 스레드 안전 | 10개 스레드 동시 `set_state` | 예외 없이 완료 |
| 상태 상수 | State 클래스 | 14개 상태 전부 정의 확인 |

### 1-2. 설정값 (Config)
| TC | 검증 내용 | 기대 결과 |
|----|----------|---------|
| `MAX_REFINE_ITER` | 타입 및 값 | `int`, 1 이상 |
| `SCORE_THRESHOLD` | 범위 | 0 ~ 100 |
| 디렉터리 생성 | `OUTPUT_DIR`, `CACHE_DIR` | 시작 시 자동 생성 |
| 코어 파일 목록 | `CORE_FILES` | `README.md`, `Dockerfile` 포함 |

### 1-3. 비용 추적 (CostTracker)
| TC | 검증 내용 | 기대 결과 |
|----|----------|---------|
| 토큰 누적 | `record()` 여러 번 | 합산 정확 |
| USD 계산 | 100만 토큰 입력 | solar-pro3 단가 기준 정확 |
| 스레드 안전 | 5개 스레드 동시 `record` | 합계 정확 |
| `fresh_tracker()` | 컨텍스트 매니저 | 전역 트래커와 독립 |

### 1-4. 시크릿 스캐너 (SecretScanner)
| TC | 검증 내용 | 기대 결과 |
|----|----------|---------|
| API 키 감지 | `api_key = "ABC..."`  | `REDACTED` 처리 |
| `@` 포함 패스워드 감지 | `password = "MyP@ss..."` | `REDACTED` 처리 ✓ 수정됨 |
| Bearer 토큰 감지 | `Bearer abc123...` | `REDACTED` 처리 ✓ 신규 |
| GitHub PAT 감지 | `ghp_` 접두어 | `REDACTED` 처리 |
| AWS 키 감지 | `AKIA` 접두어 | `REDACTED` 처리 |
| Private Key 감지 | `-----BEGIN RSA KEY-----` | `REDACTED` 처리 |
| 일반 텍스트 | 비밀 없는 문자열 | 변경 없이 통과 |
| 짧은 값(16자 미만) | 오탐 방지 | 변경 없이 통과 |

### 1-5. 데이터 모델 (Models)
| TC | 검증 내용 | 기대 결과 |
|----|----------|---------|
| `Section` 유효한 name | problem/status/cause/result | 생성 성공 |
| `Section` 잘못된 name | `"invalid"` | `ValidationError` 발생 |
| `SectionScore` 범위 | 0 ~ 100 | 경계값 통과 |
| `SectionScore` 범위 초과 | -1, 101 | `ValidationError` 발생 |
| `StoryDraft.set/get` | 섹션 설정 후 조회 | 동일 객체 반환 |
| `RepoContext.full_name` | owner + name | `"owner/name"` 형식 |

### 1-6. Section Helpers (순수 함수)
| TC | 검증 내용 | 기대 결과 |
|----|----------|---------|
| `extract_repo_metadata` | 레포 메타 텍스트화 | 이름/설명/토픽/언어 포함 |
| `detect_tech_stack` | requirements.txt 파싱 | Python + 의존성 목록 |
| `detect_tech_stack` | package.json 파싱 | JS 의존성 목록 |
| `detect_tech_stack` | 없는 manifest | "감지된 manifest 없음" |
| `_classify` | `feat:` 접두어 | `"feat"` 반환 |
| `_classify` | `bugfix:` 접두어 | `"fix"` 반환 (매핑) |
| `_classify` | 한국어 "버그 수정" | `"fix"` 반환 |
| `find_bugfix_commits` | fix 커밋 필터 | SHA 목록 반환 |
| `search_code` | 정규식 패턴 검색 | `path:line: content` 형식 |
| `make_tools` | StructuredTool 생성 | 9개 도구, 이름 고유 |

### 1-7. Notion 블록 변환 (_blocks.py)
| TC | 검증 내용 | 기대 결과 |
|----|----------|---------|
| `_rt("**굵게**")` | bold 인라인 | annotations.bold = true |
| `_rt("*기울임*")` | italic 인라인 | annotations.italic = true |
| `_rt("`코드`")` | code 인라인 | annotations.code = true |
| `heading(level)` | 레벨 1~3 | `heading_1/2/3` 타입 |
| `heading(0)` / `heading(5)` | 범위 초과 | 1 / 3으로 클램핑 |
| `md_to_blocks` | `# 제목` | heading_1 블록 |
| `md_to_blocks` | `- 항목` | bulleted_list_item |
| `md_to_blocks` | ` ```python ` | code 블록, language 설정 |
| `md_to_blocks` | `---` | divider 블록 |
| `table(rows)` | 짧은 행 | 빈 셀로 패딩 |

### 1-8. Context Builder
| TC | 검증 내용 | 기대 결과 |
|----|----------|---------|
| `compress_context` | 커밋/README 없음 | `"(커밋/README 없음)"` |
| `compress_context` | LLM invoke 모킹 | 반환값이 `commit_summary`에 저장 |
| `compress_context` | README 시크릿 포함 | invoke 전 redact 적용 |
| `sanitize_files` | core_files 시크릿 | REDACTED 처리 |
| `sanitize_files` | readme 시크릿 | REDACTED 처리 |

### 1-9. GitHub Loader
| TC | 검증 내용 | 기대 결과 |
|----|----------|---------|
| `parse_repo_url` | HTTPS URL | owner/name 파싱 |
| `parse_repo_url` | SSH URL | owner/name 파싱 |
| `parse_repo_url` | 잘못된 URL | `ValueError` |
| `_is_core_path` | `README.md` | `True` |
| `_is_core_path` | `src/main.py` | `True` |
| `_is_core_path` | `tests/test.py` | `False` |
| `_fetch_tarball` | 정상 응답 | core/docs 파일 추출 |
| `_fetch_tarball` | 403 응답 | `ValueError` |
| `_fetch_tarball` | 50MB 초과 | `ValueError` ("너무 큼") |
| `fetch_repo` | tarball 실패 | 빈 파일 세트로 진행 (예외 미전파) |

### 1-10. Notion Publisher
| TC | 검증 내용 | 기대 결과 |
|----|----------|---------|
| `_backup_local` | 로컬 파일 생성 | repo명 포함 파일명 |
| `publish` 토큰 없음 | 자격증명 미설정 | `success: False` |
| `publish` 성공 | Notion Client 모킹 | `success: True`, page_url 반환 |
| `publish` API 오류 | `APIResponseError` | `success: False`, error 반환 |

### 1-11. 템플릿 (6종)
| TC | 검증 내용 | 기대 결과 |
|----|----------|---------|
| `get("star")` | 템플릿 조회 | STAR 템플릿 반환 |
| `get("없음")` | 잘못된 ID | `ValueError` |
| `list_all()` | 전체 목록 | 6개, ID 고유 |
| 각 템플릿 `preview_md` | 전체 draft | 문자열 반환, repo명 포함 |
| 각 템플릿 `render` | 전체 draft | list[dict] 반환 |
| STAR 템플릿 | STAR 레이블 | [S]/[T]/[A]/[R] 포함 |
| 일부 섹션만 있는 draft | 누락 섹션 있음 | 오류 없이 렌더링 |

---

## 2. 통합 테스트 (Integration)

### 2-1. 세션 API 엔드포인트
| TC | 엔드포인트 | 입력 | 기대 응답 |
|----|-----------|------|---------|
| 세션 생성 성공 | `POST /api/session` | 유효한 repo_url | 200, session_id 12자 |
| 빈 URL 거부 | `POST /api/session` | `repo_url: "  "` | 400 |
| URL 필드 누락 | `POST /api/session` | body 없음 | 422 |
| 세션 상태 조회 | `GET /api/session/{sid}` | 유효한 sid | 200, 필수 필드 전체 포함 |
| 없는 세션 조회 | `GET /api/session/{sid}` | 없는 sid | 404 |
| Abort 성공 | `POST /api/session/{sid}/abort` | 유효한 sid | 200, ok: true |
| Abort 후 상태 | 세션 조회 | Abort 이후 | state: ABORTED |
| 잘못된 state 답변 | `POST /answers` | INIT 상태 | 400 |
| 답변 개수 불일치 | `POST /answers` | 질문 2개, 답변 1개 | 400 |
| 올바른 답변 제출 | `POST /answers` | INTERVIEWING, 개수 일치 | 200 |
| 템플릿 잘못된 state | `GET /templates` | INIT 상태 | 400 |
| 템플릿 조회 성공 | `GET /templates` | READY_FOR_TEMPLATE | 200, templates 배열 |
| Path traversal 차단 | `GET /download/../../etc` | 악의적 경로 | 404 |
| Health check | `GET /health` | — | 200, ok: true, 설정값 포함 |
| Publish 잘못된 state | `POST /publish` | INIT 상태 | 400 |
| Publish 성공 | `POST /publish` | READY_FOR_TEMPLATE | 200 |
| PDF 내보내기 성공 | `POST /export-pdf` | READY_FOR_TEMPLATE | 200, success: true |
| PDF 렌더링 실패 | `POST /export-pdf` | 렌더러 오류 | 200, success: false (예외 미전파) |
| PDF 잘못된 template | `POST /export-pdf` | 없는 template_id | 400 |

### 2-2. 오케스트레이터 노드
| TC | 노드 | 검증 내용 | 기대 결과 |
|----|------|----------|---------|
| Abort 감지 | `fetch_node` | Abort 상태에서 진입 | `RuntimeError` 발생 |
| Fetch 성공 | `fetch_node` | GitHub 모킹 | state: FETCHING, repo_ctx 반환 |
| Fetch 사용자 정보 첨부 | `fetch_node` | user_attached_info | ctx에 병합 |
| Compress 성공 | `compress_node` | invoke 모킹 | state: COMPRESSING |
| Interview 성공 | `interview_node` | 질문 2개 반환 | session.questions 저장 |
| Interview 질문 없음 | `interview_node` | 빈 리스트 | questions: [] |
| Wait 질문 없음 | `wait_for_answers_node` | questions 없음 | answers: [] 즉시 반환 |
| Merge answers | `merge_answers_node` | 실제 답변 있음 | ctx.user_attached_info에 병합 |
| 기존 user_info 보존 | `merge_answers_node` | 기존 정보 있음 | 기존 + 새 답변 모두 포함 |
| Generate 4섹션 | `generate_node` | SECTION_AGENTS 모킹 | 4개 섹션 반환 |
| Validate pass | `validate_node` | score ≥ threshold | overall_pass: True |
| Validate iter 누적 | `validate_node` | 2회 실행 | history 2개 |
| should_refine → diagram | `should_refine` | overall_pass: True | `"diagram"` |
| should_refine → refine | `should_refine` | fail, iter < max | `"refine"` |
| should_refine → diagram (max) | `should_refine` | fail, iter == max | `"diagram"` |
| Refine 약한 섹션부터 | `refine_node` | weakest: cause | cause 이후 재생성 |
| Diagram 생성 | `diagram_node` | 에이전트 모킹 | architecture/dataflow 반환 |
| Merge 완료 | `merge_node` | merge_agent 모킹 | state: READY_FOR_TEMPLATE |

### 2-3. Rate Limit 방어
| TC | 검증 내용 | 기대 결과 |
|----|----------|---------|
| 429 재시도 | 2번 실패 후 성공 | 3번째 호출에서 반환 |
| 429 지속 | 5회 모두 실패 | `RuntimeError` 발생 |

---

## 3. 성능 테스트 (Performance SLA)

| 엔드포인트 | SLA (p95) | 실측 p95 | 결과 |
|-----------|----------|---------|------|
| `GET /health` | < 50ms | 5.35ms | ✅ |
| `POST /api/session` | < 200ms | 5.59ms | ✅ |
| `GET /api/session/{sid}` | < 100ms | 5.96ms | ✅ |
| `GET /api/session` (404) | < 100ms | 13.96ms | ✅ |
| `POST /abort` | < 100ms | 5.47ms | ✅ |
| 동시 10세션 폴링 | < 200ms | 51.65ms | ✅ |
| `CostTracker` x10,000 | < 500ms | 2.6ms | ✅ |

---

## 4. 발견된 이슈

| # | 심각도 | 컴포넌트 | 제목 | 상태 |
|---|--------|---------|------|------|
| 1 | LOW | `secret_scanner.py` | `@` 포함 패스워드 미감지 | ✅ RESOLVED |
| 2 | INFO | `github_loader.py` | 외부 의존 커버리지 낮음 (15%) | ✅ RESOLVED |
| 3 | INFO | `orchestrator.py` | generate/refine 노드 테스트 누락 | ✅ RESOLVED |

