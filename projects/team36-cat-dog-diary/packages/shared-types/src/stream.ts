// 일기 생성/재생성 SSE 이벤트. ai-gateway → BFF → 브라우저 단일 union.
//
// transport: text/event-stream. 각 이벤트는 한 줄 `data: <json>\n\n`로 직렬화.
// gateway가 `node` / `diary_partial` / `retry` / `result` / `error` 를 emit,
// BFF가 result 받은 시점에 DB INSERT 후 `meta` 추가 emit.
// 클라이언트는 meta까지 받아야 generation 확정 (없으면 INSERT 실패).

import type { MoodTag } from './domain';

export type StreamNode = 'analyze_image' | 'write_diary' | 'safety_check';

export type StreamEvent =
  // graph 노드 시작/종료. UI 라벨 전환용 ("사진 분석 중" → "일기 쓰는 중").
  | { type: 'node'; node: StreamNode; phase: 'start' | 'end' }
  // analyze_image LLM 호출 후 산출된 사진 묘사. BFF가 가로채서 DB에 echo.
  // 클라이언트로 forward되지 않음 (graph 내부 정보).
  | { type: 'vision_done'; vision_description: string }
  // write_diary 진행 중 토큰 누적된 현재까지의 diary_text. 매번 전체를 보냄(누적 아님).
  | { type: 'diary_partial'; diary_text: string }
  // safety violation 발생 → 재시작. 클라이언트는 본문 reset.
  | { type: 'retry'; reason: string }
  // graph 최종 산출. caption/mood까지 확정.
  | { type: 'result'; diary_text: string; short_caption: string; mood_tag: MoodTag }
  // BFF가 DB INSERT 후 추가 emit. 이걸 받아야 채택/재생성 가능.
  | {
      type: 'meta';
      generation_id: string;
      session_id: string;            // generate에서는 BFF가 발급, regenerate에서는 echo
      regenerate_remaining: number;
      today_new_remaining?: number;  // generate 응답에만
    }
  // gateway 또는 BFF 측 에러. 종료 신호.
  | { type: 'error'; message: string };
