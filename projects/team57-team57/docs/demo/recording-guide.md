# 녹화 가이드

> SOMA 발표 영상 녹화 절차. Windows 11 + OBS Studio 기준. 약 60~90분 소요 (편집 포함).

---

## 0. 사전 체크 (5분)

```powershell
# 1. .env 의 UPSTAGE_API_KEY 확인 (https://console.upstage.ai 에서 발급)
cd C:\Users\sungm\Desktop\project\review-ops-agent
cat .env | grep UPSTAGE_API_KEY
# → up_... 형태 키가 있어야 함. 없으면 cp .env.example .env 후 입력.

# 2. uv 환경
uv sync

# 3. 깨끗한 시드
make reset
make seed

# 4. 1회 동작 확인 (필수)
make smoke
# → "Smoke test 완료. `make run` 으로 Streamlit UI 확인하세요." 까지 가야 함
# 실패 시: UPSTAGE_API_KEY 재확인, 로컬 mock_reviews_*.json 무결성 확인

# 5. 다시 깨끗한 상태로 재시드 (smoke 가 1건 처리해버림)
make reset
make seed

# 6. UI 시작
make run
# → 브라우저가 localhost:8501 자동 오픈. 안 뜨면 수동 접속.
```

또는 Docker 로:

```powershell
make docker-build
make docker-up        # → http://localhost:8501
make docker-seed
```

브라우저에서:
- 줌 100% 로 (`Ctrl+0`).
- 사이드바가 펼쳐진 상태인지 확인 (좌상단 햄버거 토글).
- 사이드바 expander 4개(`🍽️ 메뉴`, `🎭 톤 샘플`, `💡 톤 hint`, `➕ 사장님 답글 직접 추가`) 한 번씩 클릭해서 첫-클릭 지연 워밍업 후 모두 닫기.
- PLACE_001 (예시 카페 A) 가 선택된 상태로 시작.

---

## 1. OBS Studio 설치 + 셋업 (10분)

### 설치
- https://obsproject.com/ 에서 Windows 64-bit 다운로드 → 설치.
- 첫 실행 시 자동 구성 마법사: 녹화 최적화 선택.

### Scene 셋업

1. **Scene 1**: `데모-streamlit`
2. Source 추가:
   - **Window Capture** — 브라우저 (Streamlit 떠 있는 창) 선택.
   - 캡처 영역을 1920×1080 으로 맞춤 (브라우저 창 크기 조절).

### 녹화 출력 설정

`설정 → 출력` (또는 `Settings → Output`):
- 출력 모드: **고급(Advanced)**
- 녹화:
  - 형식: **mp4**
  - 인코더: **x264** (GPU 가속 가능하면 NVENC/QuickSync)
  - Rate Control: **CBR**, 비트레이트 **8000 Kbps**
  - Keyframe interval: **2s**

`설정 → 비디오`:
- 기본/출력 해상도: **1920×1080**
- FPS: **30**

`설정 → 오디오`:
- 마이크 활성 (narration 직접 녹음할 경우). 발표자 음성 없이 자막만 쓸 거면 비활성 OK.

### 단축키
`설정 → 단축키`:
- 녹화 시작/정지: `F9`
- 일시정지: `F10` (LLM 응답 대기 시간 cut 용)

---

## 2. 녹화 (15~25분 raw)

### 흐름

1. OBS 녹화 시작 (`F9`).
2. [`docs/demo/script.md`](./script.md) 의 5막 따라 화면 조작.
   - 세부 액션은 [`scenarios.md`](./scenarios.md) 의 표 참고.
3. 마우스 움직임은 *천천히*. 클릭 직전 1초 hover 정지.
4. LLM 응답 대기 (Solar 기준 ~1-2s/call) 동안:
   - **컷 불필요** — Solar API 라 진행률이 실시간으로 차오름. 자연스럽게 narration 으로 채울 수 있음.
   - 시나리오 1 의 5건 처리는 ~25초로 narration 과 동기화 잘 됨.
5. 시나리오 1·2·3 + 회고까지 끝나면 녹화 정지 (`F9`).

### 녹화 파일 위치
기본: `C:\Users\<USER>\Videos\` (OBS 설정에서 변경 가능).

---

## 3. 편집 (30~45분)

### 권장 도구
- **DaVinci Resolve** (무료, https://blackmagicdesign.com/products/davinciresolve) — 한글 자막 burn-in 친화.
- 또는 **Adobe Premiere Pro** / **Final Cut Pro** (라이센스 필요).

### 편집 단계

1. **컷** (Solar 기준 거의 필요 없음):
   - 마우스 망설임·실수 컷만.
   - 목표 길이 4:00 (script.md 와 일치).
   - LLM 응답 대기는 컷 불필요 — 자연스러운 흐름.

2. **자막 burn-in**:
   - DaVinci Resolve: `Edit` 페이지 → `Subtitles` 트랙 → import [`subtitles.srt`](./subtitles.srt).
   - 자막 스타일:
     - 폰트: **Pretendard** 또는 **Noto Sans KR** (Windows 미설치 시 다운로드).
     - 크기: 36pt (1080p 기준).
     - 색: 흰색 + 검은 외곽선 2px.
     - 위치: 영상 하단 중앙, bottom 80px 안쪽.
   - SRT 시간이 영상과 안 맞으면 자막 트랙 시작점만 조정 (offset).

3. **인트로 추가** (옵션):
   - 1막 (0:00-0:30) 에 Mermaid 다이어그램 PNG 띄우기.
   - 생성: `make graph-diagram` 으로 `docs/spec/diagrams/main_graph.mmd` 생성됨 → https://mermaid.live 에 붙여넣어 PNG export → 인트로에 풀스크린 4-5초.

4. **Export**:
   - 해상도: 1920×1080 30fps
   - 포맷: MP4 (H.264)
   - 비트레이트: 6000~8000 Kbps
   - 파일명: `review-ops-agent-demo-v1.mp4`

---

## 4. 사전 리허설 (필수, 30분)

영상 녹화 전 1~2회 시나리오 풀 시연 권장:

1. `make reset && make seed && make run`.
2. [`docs/demo/scenarios.md`](./scenarios.md) 의 액션 시퀀스 끝까지 손으로 돌려보기.
3. 각 시나리오에서:
   - 진행 패널이 정상 동작하는지
   - graph trace 표가 6행 모두 채워지는지
   - LLM 미리보기 toggle 이 제대로 펼쳐지는지
   - 톤 샘플 form 추가가 사이드바에 즉시 반영되는지
4. 깨지는 부분 있으면 영상 녹화 전에 fix (코드 바꾸면 다시 시드 + smoke).

---

## 5. Fallback — 라이브 시연 실패 대비

- 같은 시나리오로 *2회 녹화* 하고 좋은 쪽을 채택.
- LLM 응답이 평소보다 느릴 때(>5s/call) 컷 편집으로 보완.
- UPSTAGE_API_KEY 가 만료/오타 인 경우: `.env` 갱신 후 `make smoke` 로 동작 확인 후 재시작.
- mock data 가 손상된 경우: `make reset && make seed` 로 복구.

### 데모 환경 사고 체크리스트

| 증상 | 원인 | 복구 |
|---|---|---|
| `make seed` 시 한글 깨짐 | 콘솔 cp949 | 무시 (DB는 정상) |
| Streamlit 부팅 실패 | port 8501 점유 | `make run` 종료 후 다른 process 정리 |
| graph 실행 시 `Solar API 호출 실패` | UPSTAGE_API_KEY 만료/오타 | `.env` 의 키 재확인, https://console.upstage.ai 에서 새로 발급 |
| 진행 패널 멈춤 | LLM rate limit | ~30초 대기 후 재시도 |
| `key=...` Streamlit 에러 | 위젯 key 충돌 | `Ctrl+Shift+R` 페이지 새로고침 |

---

## 6. 제출 패키지 (최종)

압축 zip 안에 다음 파일:
- `review-ops-agent-demo-v1.mp4` — 자막 burn-in 된 최종 영상
- `docs/demo/subtitles.srt` — 별도 자막 파일 (필요 시 외부 burn-in)
- `docs/demo/script.md` — 대본
- `README.md`, `docs/spec/` 전체 — 사양 문서
- (선택) `docs/spec/diagrams/main_graph.mmd` 와 PNG 변환본
