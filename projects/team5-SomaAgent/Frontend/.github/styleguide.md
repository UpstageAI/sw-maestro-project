# Front-End Code Review Style Guide for Gemini

이 문서는 프로젝트의 코드 품질을 유지하기 위한 핵심 규칙입니다. 리뷰 시 이 원칙에 어긋나는 코드를 발견하면 반드시 지적하고 대안을 제시하세요.

## 1. Core Principles (핵심 원칙)

- **UX First:** 사용자 경험을 최우선으로 합니다. 로딩 상태(Loading), 에러 상태(Error), 빈 화면(Empty state) 처리가 누락되었는지 항상 확인하세요.
- **Logical Grounding:** 모든 기술적 결정과 상태 관리는 명확한 논리에 기반해야 합니다. 불필요한 전역 상태나 파생 상태(Derived State) 사용을 경계하세요.
- **Declarative Code:** 코드는 '어떻게(How)'가 아니라 '무엇을(What)' 하는지 명확히 보여야 합니다.

## 2. React & Next.js Best Practices

### 2.1. State Management

- **Rule:** 서버 상태(Server State)와 클라이언트 상태(Client State)를 명확히 분리하세요.
- **Action:** 외부 API 데이터를 다룰 때 단순히 `useState`와 `useEffect`를 조합했다면, React Query(또는 SWR) 도입을 권장하거나 에러/로딩 처리가 완벽한지 검토하세요.

### 2.2. Rendering Optimization

- **Rule:** 불필요한 리렌더링을 방지하세요.
- **Action:** 객체나 배열을 의존성 배열(Dependency Array)에 직접 넣은 경우, 컴포넌트 내부에서 함수를 매번 재생성하는 경우를 찾아내고 `useMemo`, `useCallback` 적용을 제안하세요.

### 2.3. Component Structure

- **Rule:** 컴포넌트는 단일 책임 원칙(SRP)을 따릅니다.
- **Action:** 하나의 파일이 300줄을 넘어가거나 비즈니스 로직과 UI 렌더링이 강하게 결합되어 있다면, Custom Hook이나 하위 UI 컴포넌트로 분리하도록 리뷰하세요.

## 3. Naming Conventions (명명 규칙)

- **Variables & Functions:** `camelCase` 사용 (예: `getUserData`)
- **Components:** `PascalCase` 사용 (예: `UserProfile`)
- **Event Handlers:** `handle` + 이벤트명 형태 사용 (예: `handleClick`, `handleSubmit`)
- **Action:** 이름만으로 역할을 유추할 수 없는 변수명(`data`, `temp`, `flag`)을 발견하면 구체적인 이름으로 변경을 요청하세요.

## 4. Error Handling (예외 처리)

- **Rule:** 조용히 넘어가는 에러(Silent Catch)는 허용하지 않습니다.
- **Action:** `try...catch` 블록에서 `catch (e) { console.log(e) }` 처럼 에러를 삼키는 코드가 있다면, 사용자에게 적절한 UI 피드백(Toast, Error Boundary)을 주도록 가이드하세요.

## 5. Review Format Checklist

리뷰 코멘트를 남길 때는 다음 형식을 지켜주세요:

1. **[문제점]** 현재 코드의 문제점을 간결하게 설명 (UX나 성능 관점 포함)
2. **[개선안]** 수정된 코드 스니펫 제공
3. **[이유]** 왜 이렇게 수정하는 것이 더 나은지 논리적 근거 제시
