# AI-nouncer

한국어 발음 교정 데모. 사용자가 한국어 문장을 읽으면 음성을 STT로 받아 원문과 음절 단위로 비교하고, 불명확한 발음 후보를 추출해 LLM이 다음 연습 방향을 제안합니다.

## 구성

이 워크스페이스는 두 개의 별도 레포로 이루어져 있습니다.

| 폴더 | 레포 | 스택 |
|---|---|---|
| [`AI-nouncer-frontend/`](./AI-nouncer-frontend) | [soma17th-ai12/AI-nouncer-frontend](https://github.com/soma17th-ai12/AI-nouncer-frontend) | Next.js 16, React 19, TypeScript, Tailwind CSS |
| [`AI-nouncer-backend/`](./AI-nouncer-backend) | [soma17th-ai12/AI-nouncer-backend](https://github.com/soma17th-ai12/AI-nouncer-backend) | FastAPI, OpenAI Whisper, Upstage Solar Pro, pydub |

## 동작 흐름

1. 프론트엔드에서 사용자가 제시된 문장을 녹음
2. 백엔드 `/api/v1/analyze` 로 오디오 전송
3. Whisper STT(`whisper-1`, `language="ko"`)로 음성 → 텍스트 변환
4. 원문과 음절 단위 정렬(alignment) 후 불명확 후보 추출
5. Upstage Solar Pro(`solar-pro`)가 교정 포커스와 연습 드릴 생성
6. 결과를 프론트엔드에서 시각화

## 빠른 시작

### 백엔드

```bash
cd AI-nouncer-backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# .env 에 OPENAI_API_KEY, UPSTAGE_API_KEY 입력

uvicorn app.main:app --reload --port 8000
```

### 프론트엔드

```bash
cd AI-nouncer-frontend
npm install
npm run dev
# http://localhost:3000
```

## 환경 변수 (백엔드)

| 키 | 용도 |
|---|---|
| `OPENAI_API_KEY` | Whisper STT |
| `UPSTAGE_API_KEY` | Upstage Solar Pro 코칭 |

## 주요 API

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/healthz` | 헬스체크 |
| GET | `/api/v1/sentences` | 미리 정의된 문장 풀 조회 |
| POST | `/api/v1/analyze` | 미리 정의된 문장(`sentence_id`)으로 분석 |
| POST | `/api/v1/analyze/free` | 임의 한국어 문장(`sentence_text`)으로 분석 |
| POST | `/api/v1/analyze/{full\|preprocess\|prompt\|silence-only}` | STT 전처리 옵션 조합별 비교 |

상세 스펙과 응답 예시는 [`AI-nouncer-backend/README.md`](./AI-nouncer-backend/README.md) 참고.

## 참고

- 백엔드는 `imageio-ffmpeg` 번들 바이너리를 사용하므로 시스템 ffmpeg 설치가 필요 없습니다.
- 노이즈 컷·무음 제거는 `pydub`으로 메모리에서 수행됩니다.
- 두 레포는 각자 독립적으로 버전 관리되며, 본 폴더는 로컬 개발 편의를 위한 워크스페이스입니다.
