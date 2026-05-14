export type Persona = {
  id: number;
  domainName: string;
  name: string;
  systemPrompt: string;
  builtIn: boolean;
  enabled: boolean;
  createdAt: string;
  updatedAt: string;
};

export type KnowledgeNode = {
  id: number;
  title: string;
  content: string;
  domainName: string;
  nodeType: string;
  analyzed: boolean;
  createdAt: string;
  updatedAt: string;
};

export type KnowledgeEdge = {
  id: number;
  sourceNodeId: number;
  targetNodeId: number;
  relationType: string;
  confidence: number;
  evidenceText: string;
  createdAt: string;
  updatedAt: string;
};

export type KnowledgeExtraction = {
  nodes: KnowledgeNode[];
  edges: KnowledgeEdge[];
  suggestedDomains: string[];
};

export type KnowledgeGraph = {
  centerNode: KnowledgeNode;
  nodes: KnowledgeNode[];
  edges: KnowledgeEdge[];
};

export type ChatSession = {
  id: number;
  personaId: number | null;
  personaDomain: string | null;
  title: string;
  createdAt: string;
};

export type ChatMessage = {
  id: number;
  sequence: number;
  role: 'USER' | 'ASSISTANT' | 'SYSTEM';
  content: string;
  createdAt: string;
};

export type DiscussionMessage = {
  id: number;
  personaId: number | null;
  personaName: string | null;
  round: 'ANALYSIS' | 'REBUTTAL' | 'SYNTHESIS';
  content: string;
  createdAt: string;
};

export type Discussion = {
  id: number;
  triggerNodeId: number | null;
  status: string;
  title: string;
  summary: string;
  actionPlan: string;
  createdAt: string;
  messages: DiscussionMessage[];
};

type RequestOptions = {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
  body?: unknown;
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '';

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: options.method ?? 'GET',
    headers: options.body ? { 'Content-Type': 'application/json' } : undefined,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });

  if (!response.ok) {
    const message = await readErrorMessage(response);
    throw new Error(message);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

async function readErrorMessage(response: Response) {
  try {
    const payload = (await response.json()) as { message?: string; error?: string };
    return payload.message ?? payload.error ?? `${response.status} ${response.statusText}`;
  } catch {
    return `${response.status} ${response.statusText}`;
  }
}

export const api = {
  getPersonas: () => request<Persona[]>('/api/personas'),
  createPersona: (domainName: string) =>
    request<Persona>('/api/personas', { method: 'POST', body: { domainName } }),
  extractKnowledge: (text: string) =>
    request<KnowledgeExtraction>('/api/knowledge/extractions', {
      method: 'POST',
      body: { text },
    }),
  getNodes: (domainName?: string) => {
    const query = domainName ? `?domainName=${encodeURIComponent(domainName)}` : '';
    return request<KnowledgeNode[]>(`/api/knowledge/nodes${query}`);
  },
  getNodeGraph: (nodeId: number) => request<KnowledgeGraph>(`/api/knowledge/nodes/${nodeId}/graph`),
  createChatSession: (personaId: number, title: string) =>
    request<ChatSession>('/api/chats', { method: 'POST', body: { personaId, title } }),
  sendChatMessage: (sessionId: number, content: string) =>
    request<ChatMessage>(`/api/chats/${sessionId}/messages`, {
      method: 'POST',
      body: { content },
    }),
  getChatMessages: (sessionId: number) => request<ChatMessage[]>(`/api/chats/${sessionId}/messages`),
  createDiscussion: (topic: string, knowledgeNodeId: number | null, personaIds: number[]) =>
    request<Discussion>('/api/discussions', {
      method: 'POST',
      body: { topic, knowledgeNodeId, personaIds },
    }),
};
