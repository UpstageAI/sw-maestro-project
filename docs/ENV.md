# autocoin-ai 환경 변수 설정

## 목적

이 문서는 AI Agent 단독 테스트에서 Gemini 실연동을 사용할 때 필요한 로컬 환경 변수 기준을 정의한다. 실제 키는 저장소에 커밋하지 않고, 로컬 `.env`에만 둔다.

## 기본 원칙

- AI Agent 단독 테스트의 기본 외부 LLM provider는 `gemini`로 둔다.
- 실제 API key는 `.env.example`에 넣지 않는다.
- `.env`와 `.env.*`는 git ignore 대상이다.
- Binance 실행은 AI Agent 단독 테스트 범위가 아니므로 기본값은 `BINANCE_MODE=disabled`다.
- Binance Spot Testnet 키가 생기더라도 FE나 AI Agent가 직접 처리하면 안 되고, BE boundary 안에서만 다뤄야 한다.

## 로컬 셋업

1. `.env.example`을 `.env`로 복사한다.
2. `GEMINI_API_KEY`에 로컬 Gemini API key를 넣는다.
3. 기본 모델은 `GEMINI_MODEL=gemini-2.5-flash`를 사용한다.
4. AI Agent 단독 테스트에서는 `BINANCE_MODE=disabled`를 유지한다.

```bash
cp .env.example .env
```

## 변수 목록

| 변수 | 기본값 | 설명 |
|---|---|---|
| `AI_LLM_PROVIDER` | `gemini` | AI Agent 단독 테스트에서 사용할 LLM provider |
| `GEMINI_API_KEY` | empty | 로컬 Gemini API key. 실제 값은 `.env`에만 저장 |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini 테스트 기본 모델 |
| `BINANCE_MODE` | `disabled` | AI Agent 단독 테스트에서 Binance 실행 비활성화 |
| `LANGSMITH_API_KEY` | empty | LangSmith 트레이싱 API key (선택) |
| `LANGSMITH_TRACING` | `true` | LangSmith 트레이싱 활성화 여부 |
| `LANGSMITH_PROJECT` | `autocoin-ai` | LangSmith 프로젝트 이름 |
| `LANGSMITH_ENDPOINT` | `https://api.smith.langchain.com` | LangSmith 엔드포인트 |

LangSmith 변수는 모두 선택 사항이다. 설정하지 않으면 트레이싱 없이 실행된다.

## 금지 사항

- 실제 Gemini API key를 문서, 코드, 커밋 메시지, PR 본문에 쓰지 않는다.
- 실거래 Binance API Key / Secret을 사용하지 않는다.
- AI Agent 단독 테스트에서 Binance 서명, timestamp 처리, 주문 제출을 수행하지 않는다.
