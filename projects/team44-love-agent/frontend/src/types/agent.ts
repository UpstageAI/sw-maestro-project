// 에이전트 식별자 및 기본 타입 정의
export type AgentId =
  | 'playboy'
  | 'ice'
  | 'confessor'
  | 'bestie';

export interface Agent {
  id: AgentId;
  name: string;
  persona: string;
  tone: string;
  colorKey: string;
  // public/agents/{id}.png 경로. Sidebar·ChatPhase·아바타에서 사용.
  image: string;
}
