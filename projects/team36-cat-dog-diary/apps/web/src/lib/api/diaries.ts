import type {
  AdoptDiaryRequest,
  AdoptDiaryResponse,
  GenerateRequest,
  GenerateResponse,
  ListDiariesResponse,
  RegenerateRequest,
  RegenerateResponse,
  StreamEvent,
  StreamNode,
} from "@cat-dog-diary/shared-types";

async function unwrap<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.error?.message ?? `HTTP ${res.status}`);
  }
  return res.json();
}

// ----- diary streaming consumer -----

export interface DiaryStreamCallbacks {
  onNode?: (node: StreamNode, phase: "start" | "end") => void;
  onPartial?: (diary_text: string) => void;
  onRetry?: (reason: string) => void;
}

type ResultEvent = Extract<StreamEvent, { type: "result" }>;
type MetaEvent = Extract<StreamEvent, { type: "meta" }>;

async function consumeDiaryStream(
  res: Response,
  callbacks: DiaryStreamCallbacks,
): Promise<{ result: ResultEvent; meta: MetaEvent }> {
  // 검증 실패 등 stream 시작 전 에러는 JSON.
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.error?.message ?? `HTTP ${res.status}`);
  }
  if (!res.body) throw new Error("응답 body가 비어있어요");

  const decoder = new TextDecoder();
  const reader = res.body.getReader();
  let buffer = "";
  let resultEvent: ResultEvent | null = null;
  let metaEvent: MetaEvent | null = null;
  let streamError: string | null = null;

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

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
        continue;
      }

      switch (event.type) {
        case "node":
          callbacks.onNode?.(event.node, event.phase);
          break;
        case "diary_partial":
          callbacks.onPartial?.(event.diary_text);
          break;
        case "retry":
          callbacks.onRetry?.(event.reason);
          break;
        case "result":
          resultEvent = event;
          break;
        case "meta":
          metaEvent = event;
          break;
        case "error":
          streamError = event.message;
          break;
        case "vision_done":
          // BFF mediator가 가로채므로 클라이언트엔 도달 안 함. type-exhaustive용.
          break;
      }
    }
  }

  if (streamError) throw new Error(streamError);
  if (!resultEvent || !metaEvent) {
    throw new Error("스트림이 결과/메타를 모두 보내지 못했어요");
  }
  return { result: resultEvent, meta: metaEvent };
}

export async function generateDiary(
  input: GenerateRequest,
  callbacks: DiaryStreamCallbacks = {},
): Promise<GenerateResponse> {
  const res = await fetch("/api/diaries/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  const { result, meta } = await consumeDiaryStream(res, callbacks);
  return {
    session_id: meta.session_id,
    generation_id: meta.generation_id,
    diary_text: result.diary_text,
    short_caption: result.short_caption,
    mood_tag: result.mood_tag,
    regenerate_remaining: meta.regenerate_remaining,
    today_new_remaining: meta.today_new_remaining ?? 0,
  };
}

export async function regenerateDiary(
  input: RegenerateRequest,
  callbacks: DiaryStreamCallbacks = {},
): Promise<RegenerateResponse> {
  const res = await fetch("/api/diaries/regenerate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  const { result, meta } = await consumeDiaryStream(res, callbacks);
  return {
    generation_id: meta.generation_id,
    diary_text: result.diary_text,
    short_caption: result.short_caption,
    mood_tag: result.mood_tag,
    regenerate_remaining: meta.regenerate_remaining,
  };
}

export async function adoptDiary(
  input: AdoptDiaryRequest,
): Promise<AdoptDiaryResponse> {
  const res = await fetch("/api/diaries", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return unwrap<AdoptDiaryResponse>(res);
}

export async function deleteDiary(id: string): Promise<void> {
  const res = await fetch(`/api/diaries/${id}`, { method: "DELETE" });
  if (!res.ok && res.status !== 204) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.error?.message ?? `HTTP ${res.status}`);
  }
}

export async function listDiaries(
  petId: string,
  cursor?: string,
  limit?: number,
): Promise<ListDiariesResponse> {
  const params = new URLSearchParams({ petId });
  if (cursor) params.set("cursor", cursor);
  if (limit !== undefined) params.set("limit", String(limit));
  const res = await fetch(`/api/diaries?${params.toString()}`);
  return unwrap<ListDiariesResponse>(res);
}
