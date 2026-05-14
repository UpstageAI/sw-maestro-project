'use client';

import { useState, useCallback, useRef } from 'react';
import type { AnalysisNode, AnalysisResult, AnalysisStatus, NodeId, UseAnalyzeStreamReturn } from '@/types/analysis';
import { INITIAL_NODES, MOCK_RESULT } from '@/lib/mockData';

// ─────────────────────────────────────────────────────────────────────────────
// useAnalyzeStream
//
// [실제 API] POST /analyze/stream 응답을 fetch + ReadableStream으로 읽습니다.
// [Mock] 기존 목 데이터 시뮬레이션은 analyzeWithMockData()로 보존합니다.
//
// 개발 중 mock만 사용하려면 .env.local에 아래 값을 설정하세요.
//   NEXT_PUBLIC_ANALYSIS_MODE=mock
//
// API 기본 경로는 /analyze/stream 입니다.
// 백엔드가 별도 origin이면 NEXT_PUBLIC_API_BASE_URL을 설정할 수 있습니다.
//
// 백엔드 스트리밍 이벤트 형식:
//   data: {"node": "input", "status": "active"}
//   data: {"node": "input", "status": "done"}
//   data: {"node": "summary", "status": "active"}
//   data: {"node": "summary", "status": "done", "content": ["..."]}
//   data: {"node": "decision", "status": "active"}
//   data: {"node": "decision", "status": "done", "content": ["..."]}
//   data: {"node": "agenda", "status": "done", "content": ["..."], "complete": true}
//
// 이전 mock/API 호환을 위해 아래 형식도 지원합니다.
//   data: {"node": "summary", "content": "..."}
//   data: {"node": "decision", "content": "..."}
//   data: {"node": "agenda", "content": "..."}
//   data: [DONE]
// ─────────────────────────────────────────────────────────────────────────────

const EMPTY_RESULT: AnalysisResult = { summary: null, decisions: null, agenda: null };
const RESULT_NODE_IDS = ['summary', 'decision', 'agenda'] as const;
const STREAM_NODE_IDS = ['input', ...RESULT_NODE_IDS] as const;
const NODE_STATUSES = ['pending', 'active', 'done'] as const;

interface StreamApiPayload {
  node?: string;
  status?: string;
  content?: unknown;
  complete?: boolean;
}

function cloneNodes(nodes: AnalysisNode[]): AnalysisNode[] {
  return nodes.map(n => ({ ...n }));
}

function getAnalyzeStreamUrl(): string {
  const explicitUrl = process.env.NEXT_PUBLIC_ANALYZE_STREAM_URL;
  if (explicitUrl) return explicitUrl;

  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, '');
  return `${baseUrl ?? ''}/analyze/stream`;
}

function isStreamNodeId(node: string | undefined): node is (typeof STREAM_NODE_IDS)[number] {
  return !!node && STREAM_NODE_IDS.includes(node as (typeof STREAM_NODE_IDS)[number]);
}

function isResultNodeId(node: (typeof STREAM_NODE_IDS)[number]): node is (typeof RESULT_NODE_IDS)[number] {
  return RESULT_NODE_IDS.includes(node as (typeof RESULT_NODE_IDS)[number]);
}

function isNodeStatus(status: string | undefined): status is AnalysisNode['status'] {
  return !!status && NODE_STATUSES.includes(status as AnalysisNode['status']);
}

function resultKeyForNode(node: (typeof RESULT_NODE_IDS)[number]): keyof AnalysisResult {
  return node === 'decision' ? 'decisions' : node;
}

function cleanResultLine(line: string): string | null {
  let cleaned = line.trim();
  if (!cleaned) return null;

  cleaned = cleaned
    .replace(/^\s*(?:[-*•]|\d+[.)])\s+/, '')
    .replace(/^>\s*/, '')
    .trim();

  if (!cleaned || cleaned.startsWith('#')) return null;

  cleaned = cleaned
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/__([^_]+)__/g, '$1')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/\s{2,}/g, ' ')
    .trim();

  return cleaned || null;
}

function normalizeContent(content: unknown): string[] {
  if (Array.isArray(content)) {
    return content
      .filter((item): item is string => typeof item === 'string')
      .flatMap(item => item.split(/\r?\n/))
      .map(cleanResultLine)
      .filter((item): item is string => item !== null);
  }

  if (typeof content !== 'string') return [];

  const normalized = content.trim();
  if (!normalized) return [];

  const lines = normalized
    .split(/\r?\n/)
    .map(cleanResultLine)
    .filter((line): line is string => line !== null);

  return lines.length > 0 ? lines : [normalized];
}

export function useAnalyzeStream(): UseAnalyzeStreamReturn {
  const [status, setStatus] = useState<AnalysisStatus>('idle');
  const [nodes, setNodes] = useState<AnalysisNode[]>(cloneNodes(INITIAL_NODES));
  const [result, setResult] = useState<AnalysisResult>(EMPTY_RESULT);
  const [error, setError] = useState<string | null>(null);
  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([]);
  const abortControllerRef = useRef<AbortController | null>(null);

  const clearTimers = useCallback(() => {
    timersRef.current.forEach(clearTimeout);
    timersRef.current = [];
  }, []);

  const setNodeStatus = useCallback((id: NodeId, nodeStatus: AnalysisNode['status']) => {
    setNodes(prev => prev.map(n => n.id === id ? { ...n, status: nodeStatus } : n));
  }, []);

  // ── 목 시뮬레이션 ──────────────────────────────────────────────────────────
  // 실제 API와 구분되는 개발/테스트용 mock 경로입니다.
  const analyzeWithMockData = useCallback(() => {
    const schedule = (fn: () => void, ms: number) => {
      const t = setTimeout(fn, ms);
      timersRef.current.push(t);
    };

    // input: 0ms active → 600ms done
    schedule(() => setNodeStatus('input', 'active'), 0);
    schedule(() => setNodeStatus('input', 'done'), 600);

    // summary: 700ms active → 1600ms done + result populated
    schedule(() => setNodeStatus('summary', 'active'), 700);
    schedule(() => {
      setNodeStatus('summary', 'done');
      setResult(prev => ({ ...prev, summary: MOCK_RESULT.summary }));
    }, 1600);

    // decision: 1700ms active → 2600ms done
    schedule(() => setNodeStatus('decision', 'active'), 1700);
    schedule(() => {
      setNodeStatus('decision', 'done');
      setResult(prev => ({ ...prev, decisions: MOCK_RESULT.decisions }));
    }, 2600);

    // agenda: 2700ms active → 3600ms done → complete
    schedule(() => setNodeStatus('agenda', 'active'), 2700);
    schedule(() => {
      setNodeStatus('agenda', 'done');
      setResult(prev => ({ ...prev, agenda: MOCK_RESULT.agenda }));
    }, 3600);

    schedule(() => setStatus('complete'), 3700);
  }, [setNodeStatus]);
  // ── 목 시뮬레이션 끝 ────────────────────────────────────────────────────────

  // ── 실제 스트리밍 API 연동 ────────────────────────────────────────────────
  const analyzeWithStreamApi = useCallback(async (transcript: string, signal: AbortSignal) => {
    setNodeStatus('input', 'active');

    const response = await fetch(getAnalyzeStreamUrl(), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
      },
      body: JSON.stringify({ transcript }),
      signal,
    });

    if (!response.ok) {
      throw new Error(`분석 API 요청 실패 (${response.status})`);
    }

    if (!response.body) {
      throw new Error('분석 API 응답 스트림을 읽을 수 없습니다.');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let doneReceived = false;

    const handleDataLine = (rawLine: string) => {
      const line = rawLine.trim();
      if (!line || line.startsWith(':') || !line.startsWith('data:')) return;

      const data = line.slice('data:'.length).trim();
      if (!data) return;

      if (data === '[DONE]') {
        doneReceived = true;
        setNodes(prev => prev.map(node => node.status === 'active' ? { ...node, status: 'done' } : node));
        setStatus('complete');
        return;
      }

      let payload: StreamApiPayload;
      try {
        payload = JSON.parse(data) as StreamApiPayload;
      } catch {
        throw new Error('스트리밍 응답 JSON 파싱에 실패했습니다.');
      }

      if (!isStreamNodeId(payload.node)) {
        throw new Error(`알 수 없는 분석 노드가 도착했습니다: ${payload.node ?? 'unknown'}`);
      }

      const nodeId = payload.node;

      if (nodeId !== 'input') {
        setNodeStatus('input', 'done');
      }

      if (isNodeStatus(payload.status)) {
        setNodeStatus(nodeId, payload.status);
      } else if (isResultNodeId(nodeId)) {
        setNodeStatus(nodeId, 'active');
      }

      if (isResultNodeId(nodeId) && payload.content !== undefined) {
        const items = normalizeContent(payload.content);
        const resultKey = resultKeyForNode(nodeId);
        setResult(prev => ({ ...prev, [resultKey]: items }));

        if (!isNodeStatus(payload.status)) {
          setNodeStatus(nodeId, 'done');
        }
      }

      if (payload.complete === true) {
        doneReceived = true;
        setNodes(prev => prev.map(node => node.status === 'active' ? { ...node, status: 'done' } : node));
        setStatus('complete');
      }
    };

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split(/\r?\n/);
      buffer = lines.pop() ?? '';

      for (const line of lines) {
        handleDataLine(line);
      }
    }

    buffer += decoder.decode();
    if (buffer.trim()) {
      handleDataLine(buffer);
    }

    if (!doneReceived) {
      throw new Error('분석 완료 신호를 받지 못했습니다.');
    }
  }, [setNodeStatus]);
  // ── 실제 스트리밍 API 연동 끝 ─────────────────────────────────────────────

  const startAnalysis = useCallback((transcript: string) => {
    if (status === 'streaming') return;

    clearTimers();
    abortControllerRef.current?.abort();
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    setStatus('streaming');
    setNodes(cloneNodes(INITIAL_NODES));
    setResult(EMPTY_RESULT);
    setError(null);

    if (process.env.NEXT_PUBLIC_ANALYSIS_MODE === 'mock') {
      analyzeWithMockData();
      return;
    }

    void analyzeWithStreamApi(transcript, abortController.signal).catch(apiError => {
      if (abortController.signal.aborted) return;

      const message = apiError instanceof Error
        ? apiError.message
        : '분석 중 알 수 없는 오류가 발생했습니다.';

      if (process.env.NEXT_PUBLIC_ANALYSIS_FALLBACK_TO_MOCK === 'true') {
        setError(`${message} Mock 데이터로 대체합니다.`);
        setStatus('streaming');
        setNodes(cloneNodes(INITIAL_NODES));
        setResult(EMPTY_RESULT);
        analyzeWithMockData();
        return;
      }

      setStatus('error');
      setError(message);
    });
  }, [status, clearTimers, analyzeWithMockData, analyzeWithStreamApi]);

  const reset = useCallback(() => {
    clearTimers();
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    setStatus('idle');
    setNodes(cloneNodes(INITIAL_NODES));
    setResult(EMPTY_RESULT);
    setError(null);
  }, [clearTimers]);

  return { status, nodes, result, startAnalysis, reset, error };
}
