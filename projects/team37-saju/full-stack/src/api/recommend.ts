import type {
  AgentEvent,
  PipelineResultDto,
  UserInput,
} from '../types';

export interface StreamHandlers {
  onEvent?: (event: AgentEvent) => void;
  signal?: AbortSignal;
}

/**
 * Streams the multi-agent pipeline via SSE. Resolves with the final
 * PipelineResultDto. Throws if the server emits an `error` event or the
 * stream ends without a `pipeline_done` event.
 */
export async function streamRecommendation(
  args: { apiKey: string; userInput: UserInput; model?: string },
  handlers: StreamHandlers = {},
): Promise<PipelineResultDto> {
  const res = await fetch('/api/recommend/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
    },
    body: JSON.stringify(args),
    signal: handlers.signal,
  });

  if (!res.ok) {
    const detail = await safeReadJson(res);
    throw new Error(detail?.error ?? `요청이 실패했어요 (${res.status})`);
  }
  if (!res.body) {
    throw new Error('스트림 응답을 열 수 없어요.');
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let finalResult: PipelineResultDto | null = null;
  let lastError: string | null = null;

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let sep = buffer.indexOf('\n\n');
    while (sep !== -1) {
      const rawEvent = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);
      sep = buffer.indexOf('\n\n');
      const parsed = parseSseEvent(rawEvent);
      if (!parsed) continue;
      handlers.onEvent?.(parsed);
      if (parsed.type === 'pipeline_done') {
        finalResult = parsed.payload as PipelineResultDto;
      } else if (parsed.type === 'error') {
        lastError = parsed.message ?? '알 수 없는 오류가 발생했어요.';
      }
    }
  }

  if (lastError) throw new Error(lastError);
  if (!finalResult) throw new Error('파이프라인이 결과 없이 종료되었어요.');
  return finalResult;
}

function parseSseEvent(block: string): AgentEvent | null {
  const dataLines: string[] = [];
  for (const line of block.split('\n')) {
    if (line.startsWith(':')) continue; // comment / heartbeat
    if (line.startsWith('data:')) {
      dataLines.push(line.slice(5).trimStart());
    }
  }
  if (dataLines.length === 0) return null;
  try {
    return JSON.parse(dataLines.join('\n')) as AgentEvent;
  } catch {
    return null;
  }
}

async function safeReadJson(res: Response): Promise<{ error?: string } | null> {
  try {
    return (await res.json()) as { error?: string };
  } catch {
    return null;
  }
}
