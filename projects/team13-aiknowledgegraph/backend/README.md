# AI13-BE

AI 지식 그래프 기반 페르소나 채팅 서버입니다.

프로젝트 기획서: [docs/plan.md](docs/plan.md)

## API 명세

서버 실행 후 Swagger UI에서 확인하세요.

```
http://localhost:8080/swagger-ui/index.html
```

---

## 로컬 실행

### 공통 사전 준비

`.env` 파일을 프로젝트 루트에 생성합니다.

```bash
cp .env.example .env
```

`.env` 파일에 Upstage API 키를 입력합니다.

```env
UPSTAGE_API_KEY=your_api_key_here
```

---

### 프론트엔드 개발자 — Docker로 전체 실행

DB와 서버를 한 번에 컨테이너로 띄웁니다. **Java 설치 불필요.**

**필요한 것**: Docker Desktop

```bash
# 첫 실행 또는 서버 코드가 변경된 경우
docker compose --profile app up --build

# 이후 실행
docker compose --profile app up
```

서버가 올라오면 `http://localhost:8080`으로 접근할 수 있습니다.

```bash
# 종료
docker compose --profile app down
```

---

### 백엔드 개발자 — bootRun으로 바로 실행

`spring-boot-docker-compose` 덕분에 `bootRun` 실행 시 DB 컨테이너가 자동으로 함께 실행됩니다. 별도로 `docker compose up`을 실행할 필요가 없습니다.

**필요한 것**: Docker Desktop, Java 21

**서버 실행**

IDE(IntelliJ 등)의 EnvFile 플러그인을 활용하거나, 터미널에서 아래와 같이 실행합니다.

```bash
export $(grep -v '^#' .env | xargs) && ./gradlew bootRun
```

> 기본 Spring Boot는 `.env`를 자동으로 로드하지 않으므로 위와 같이 직접 주입해야 합니다.

> DB 컨테이너는 서버 종료 시 함께 내려갑니다. 수동으로 종료하려면 `docker compose down`을 사용하세요.

---

## 환경변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `UPSTAGE_API_KEY` | (필수) | Upstage Solar API 키 |
| `DB_URL` | `jdbc:postgresql://localhost:5433/ai13` | DB 접속 URL |
| `DB_USERNAME` | `ai13` | DB 사용자 |
| `DB_PASSWORD` | `ai13` | DB 비밀번호 |
