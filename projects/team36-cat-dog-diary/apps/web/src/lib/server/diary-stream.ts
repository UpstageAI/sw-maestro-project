// BFF가 ai-gateway SSE를 받아 그대로 client로 forward하면서, `result` 이벤트
// 시점에 DB INSERT/quota를 처리한 뒤 추가 `meta` 이벤트를 emit하는 mediator.
//
// 검증 실패는 stream 시작 전 JSON으로 응답 (errorResponse). 일단 stream이
// 시작되면 모든 에러는 SSE `error` 이벤트로 흘러간다.

import type { StreamEvent } from "@cat-dog-diary/shared-types";

type ResultEvent = Extract<StreamEvent, { type: "result" }>;
type ResultPayload = Pick<
  ResultEvent,
  "diary_text" | "short_caption" | "mood_tag"
>;

export type ResultEventHandler = (
  result: ResultPayload,
  visionDescription: string | null,
) => Promise<StreamEvent>; // meta 또는 error

export function mediateStream(
  upstream: ReadableStream<Uint8Array>,
  onResult: ResultEventHandler,
): ReadableStream<Uint8Array> {
  return new ReadableStream<Uint8Array>({
    async start(controller) {
      const encoder = new TextEncoder();
      const decoder = new TextDecoder();
      const reader = upstream.getReader();
      let buffer = "";
      let resultPayload: ResultPayload | null = null;
      let visionDescription: string | null = null;

      function emit(event: StreamEvent) {
        controller.enqueue(
          encoder.encode(`data: ${JSON.stringify(event)}\n\n`),
        );
      }

      try {
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });

          // SSE event boundary는 빈 줄(\n\n).
          let sep: number;
          while ((sep = buffer.indexOf("\n\n")) !== -1) {
            const block = buffer.slice(0, sep);
            buffer = buffer.slice(sep + 2);

            const dataLine = block
              .split("\n")
              .find((l) => l.startsWith("data: "));
            if (!dataLine) continue;

            let event: StreamEvent;
            try {
              event = JSON.parse(dataLine.slice(6)) as StreamEvent;
            } catch {
              continue; // malformed line은 drop
            }

            // vision_done은 graph 내부 정보 — BFF가 가로채고 forward 안 함.
            if (event.type === "vision_done") {
              visionDescription = event.vision_description;
              continue;
            }

            // 그 외 모든 event는 클라이언트로 forward.
            emit(event);

            if (event.type === "result") {
              resultPayload = {
                diary_text: event.diary_text,
                short_caption: event.short_caption,
                mood_tag: event.mood_tag,
              };
            }
          }
        }

        if (resultPayload) {
          const meta = await onResult(resultPayload, visionDescription);
          emit(meta);
        }
      } catch (e) {
        emit({
          type: "error",
          message: e instanceof Error ? e.message : "stream mediator 실패",
        });
      } finally {
        controller.close();
      }
    },
  });
}

export function sseResponse(stream: ReadableStream<Uint8Array>): Response {
  return new Response(stream, {
    status: 200,
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      "X-Accel-Buffering": "no",
    },
  });
}
