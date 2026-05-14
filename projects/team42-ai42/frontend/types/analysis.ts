export type NodeId = 'input' | 'summary' | 'decision' | 'agenda';
export type NodeStatus = 'pending' | 'active' | 'done';
export type AnalysisStatus = 'idle' | 'streaming' | 'complete' | 'error';

export interface AnalysisNode {
  id: NodeId;
  label: string;
  status: NodeStatus;
}

export interface AnalysisResult {
  summary: string[] | null;
  decisions: string[] | null;
  agenda: string[] | null;
}

// This is the contract between the hook and the UI.
// The mock hook fulfills this interface; the real SSE-based hook must too.
export interface UseAnalyzeStreamReturn {
  status: AnalysisStatus;
  nodes: AnalysisNode[];
  result: AnalysisResult;
  startAnalysis: (transcript: string) => void;
  reset: () => void;
  error: string | null;
}
