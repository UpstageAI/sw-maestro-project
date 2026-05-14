# AI13-FE

AI 기반 개인 지식 그래프 에이전트 프로젝트의 React 프론트엔드입니다.

프론트엔드는 `AI13-BE` Spring Boot 서버의 REST API를 사용합니다. 로컬 개발 시 Vite dev server가 `/api` 요청을 `http://localhost:8080`으로 프록시합니다.

## 주요 기능

- **스마트 텍스트 입력**
  - 자유 텍스트를 백엔드의 `POST /api/knowledge/extractions`로 전송합니다.
  - Solar LLM 기반 추출 결과로 생성된 지식 노드, 엣지, 추천 도메인을 표시합니다.

- **페르소나 관리**
  - 등록된 도메인 페르소나 목록을 조회합니다.
  - 새 도메인 이름을 입력해 페르소나를 생성할 수 있습니다.
  - 추천 도메인을 클릭해 바로 페르소나 생성 입력값으로 사용할 수 있습니다.

- **지식 그래프 캔버스**
  - 지식 노드 목록과 최근 추출 엣지를 그래프 형태로 표시합니다.
  - 노드를 선택하면 `GET /api/knowledge/nodes/{nodeId}/graph` 기반 1-hop 그래프와 상세 정보를 보여줍니다.

- **페르소나 채팅**
  - 선택한 페르소나로 채팅 세션을 생성합니다.
  - 사용자 메시지를 전송하고 AI 응답 및 히스토리를 표시합니다.

- **멀티 에이전트 토론**
  - 토론 주제, 선택 노드, 참여 페르소나 목록으로 3라운드 토론을 실행합니다.
  - 최종 요약, 실행 계획, 라운드별 메시지를 표시합니다.

## 기술 스택

- React 19
- TypeScript
- Vite
- React Router
- pnpm
- ESLint + Prettier

## 사전 준비

- Node.js
- pnpm
- 백엔드 서버: `http://localhost:8080`

백엔드 실행 방법은 `../AI13-BE/README.md`를 참고하세요. 백엔드는 `.env`에 `UPSTAGE_API_KEY`가 필요합니다.

## 설치

```bash
cd AI13-FE
pnpm install
```

## 프론트엔드 실행

```bash
cd AI13-FE
pnpm dev
```

브라우저에서 아래 주소로 접속합니다.

```text
http://localhost:5173/
```

## 백엔드 함께 실행

Docker가 설치되어 있다면 백엔드는 아래 방식으로 실행할 수 있습니다.

```bash
cd AI13-BE
cp .env.example .env
# .env 파일에 UPSTAGE_API_KEY 입력
docker compose --profile app up --build
```

백엔드가 정상 실행되면 Swagger UI에서 API를 확인할 수 있습니다.

```text
http://localhost:8080/swagger-ui/index.html
```

## 환경 변수

프론트엔드는 기본적으로 같은 origin의 `/api`를 호출합니다. Vite 개발 서버에서는 `/api`가 `http://localhost:8080`으로 프록시됩니다.

다른 API 서버를 직접 지정해야 하면 `.env.local`을 만들고 아래 값을 설정합니다.

```env
VITE_API_BASE_URL=http://localhost:8080
```

일반 로컬 개발에서는 설정하지 않아도 됩니다.

## 검증

```bash
pnpm lint
pnpm build
```

## 로컬 실행 체크리스트

1. `AI13-BE/.env`에 `UPSTAGE_API_KEY`를 설정합니다.
2. 백엔드를 `http://localhost:8080`에서 실행합니다.
3. 프론트엔드를 `pnpm dev`로 실행합니다.
4. `http://localhost:5173/`에 접속합니다.

백엔드가 꺼져 있으면 화면은 열리지만 페르소나, 지식 추출, 채팅, 토론 API 기능은 실패 메시지를 표시합니다.
