# Model Comparison Note

## Provider 전략

- `ANTHROPIC_API_KEY`가 있으면 Claude 계열 provider 사용 예정
- `OPENAI_API_KEY`가 있으면 OpenAI provider 사용 예정
- 키가 없으면 `MockProvider`로 전체 데모가 가능해야 함

## 1단계 상태

현재는 `MockProvider`가 기본이며, 실제 provider 클래스는 인터페이스만 맞춰둔 상태입니다.

## 설계 의도

- UI와 Agent 흐름이 실제 API 키 유무에 종속되지 않도록 분리
- 발표 시 provider adapter 패턴을 명확히 설명 가능

