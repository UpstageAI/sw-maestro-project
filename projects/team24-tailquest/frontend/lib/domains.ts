// Domain catalog used by the onboarding flow and the practice page.
// `seedQuestion` is the easy first-question shown to the user before they answer.
// Backend will eventually generate this with Solar; for now it's curated.

export type Track = "cs" | "stack";

export interface Domain {
  id: string;
  label: string;
  icon: string;        // material-symbols-outlined name
  topics: string[];    // shown as sub-bullets on the card
  seedQuestion: string;
}

export const CS_FOUNDATIONS: Domain[] = [
  {
    id: "os",
    label: "운영체제",
    icon: "memory",
    topics: ["프로세스/스레드", "동시성", "메모리 관리", "스케줄링"],
    seedQuestion: "프로세스와 스레드의 차이를 설명해주세요.",
  },
  {
    id: "db",
    label: "데이터베이스",
    icon: "database",
    topics: ["인덱스", "트랜잭션", "정규화", "쿼리 최적화"],
    seedQuestion: "데이터베이스 인덱스가 검색 속도를 빠르게 하는 원리를 설명해주세요.",
  },
  {
    id: "network",
    label: "네트워크",
    icon: "lan",
    topics: ["TCP/IP", "HTTP", "로드 밸런싱", "DNS"],
    seedQuestion: "TCP 와 UDP 의 차이를 설명해주세요.",
  },
  {
    id: "ds",
    label: "자료구조",
    icon: "account_tree",
    topics: ["트리", "그래프", "해시", "힙"],
    seedQuestion: "해시 테이블의 충돌이 발생하는 이유와 해결 방법을 설명해주세요.",
  },
  {
    id: "algo",
    label: "알고리즘",
    icon: "psychology_alt",
    topics: ["정렬", "탐색", "동적계획법", "그리디"],
    seedQuestion: "동적 계획법(DP)이 분할 정복과 어떻게 다른지 설명해주세요.",
  },
  {
    id: "arch",
    label: "컴퓨터구조",
    icon: "developer_board",
    topics: ["파이프라이닝", "캐시", "가상메모리"],
    seedQuestion: "CPU 캐시가 성능에 어떻게 영향을 주는지 설명해주세요.",
  },
];

export const TECH_STACKS: Domain[] = [
  {
    id: "spring",
    label: "Spring",
    icon: "eco",
    topics: ["DI", "AOP", "Spring Security", "JPA"],
    seedQuestion:
      "Spring 의 Dependency Injection 이 왜 필요한지, 일반적인 객체 생성과 비교해서 설명해주세요.",
  },
  {
    id: "react",
    label: "React",
    icon: "code",
    topics: ["Hooks", "상태관리", "렌더링 최적화"],
    seedQuestion:
      "React 의 useState 와 useReducer 는 언제 어떻게 다르게 사용하시나요?",
  },
  {
    id: "node",
    label: "Node.js",
    icon: "javascript",
    topics: ["이벤트 루프", "Express", "스트림"],
    seedQuestion:
      "Node.js 의 이벤트 루프가 동시 요청을 처리하는 방식을 설명해주세요.",
  },
  {
    id: "django",
    label: "Django",
    icon: "web",
    topics: ["ORM", "미들웨어", "DRF"],
    seedQuestion: "Django ORM 의 N+1 문제와 해결 방법을 설명해주세요.",
  },
  {
    id: "vue",
    label: "Vue",
    icon: "view_quilt",
    topics: ["Composition API", "상태관리", "라우터"],
    seedQuestion:
      "Vue 3 의 Composition API 가 Options API 와 어떻게 다르고 왜 도입되었는지 설명해주세요.",
  },
  {
    id: "fastapi",
    label: "FastAPI",
    icon: "api",
    topics: ["Async", "Pydantic", "Dependency Injection"],
    seedQuestion:
      "FastAPI 의 Dependency Injection 시스템을 어떻게 활용하시나요?",
  },
  {
    id: "kotlin",
    label: "Kotlin",
    icon: "android",
    topics: ["코루틴", "Sealed Class", "DSL"],
    seedQuestion:
      "Kotlin 코루틴이 일반 스레드 모델과 비교해 갖는 장점을 설명해주세요.",
  },
  {
    id: "swift",
    label: "iOS Swift",
    icon: "phone_iphone",
    topics: ["MVVM", "Combine", "SwiftUI"],
    seedQuestion:
      "Swift 의 ARC(Automatic Reference Counting) 가 메모리를 어떻게 관리하는지 설명해주세요.",
  },
  {
    id: "flutter",
    label: "Flutter",
    icon: "flutter_dash",
    topics: ["Widget", "Riverpod", "Build context"],
    seedQuestion:
      "Flutter 의 StatefulWidget 과 StatelessWidget 의 차이와 선택 기준을 설명해주세요.",
  },
];

export const TRACKS: Record<
  Track,
  { label: string; description: string; icon: string; domains: Domain[] }
> = {
  cs: {
    label: "CS 기초",
    description:
      "운영체제·DB·네트워크·자료구조·알고리즘 등 모든 SW 직군이 공통으로 검증받는 기초 지식.",
    icon: "school",
    domains: CS_FOUNDATIONS,
  },
  stack: {
    label: "기술 스택",
    description:
      "Spring·React·Node.js 등 실제로 사용한 프레임워크에 대한 실무 깊이.",
    icon: "build",
    domains: TECH_STACKS,
  },
};

export function findDomain(id: string): Domain | undefined {
  return [...CS_FOUNDATIONS, ...TECH_STACKS].find((d) => d.id === id);
}
