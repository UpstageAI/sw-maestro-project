import { getOrCreateSessionId } from "./session";

export type GenerateResponse = {
  id: string;
  status: "completed" | "error";
  input: {
    idea: string;
    tone: string;
    use_search: boolean;
  };
  document: {
    title: string;
    technical_field: string;
    background: string;
    problem: string;
    configuration: string;
    claims: string[];
    summary: string;
  };
  sources: Array<{
    title: string;
    url: string;
    snippet: string;
  }>;
  warnings: string[];
};

type GenerateRequest = {
  idea: string;
  tone: string;
  use_search: boolean;
};

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";

export async function generatePatent(
  request: GenerateRequest,
): Promise<GenerateResponse> {
  const response = await fetch(`${BACKEND_URL}/api/generate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      ...request,
      session_id: getOrCreateSessionId(),
    }),
  });

  if (!response.ok) {
    throw new Error(`Generate request failed: ${response.status}`);
  }

  return response.json();
}

export type RevisionResponse = {
  session_id: string;
  assistant_message: string;
  document: GenerateResponse["document"];
  warnings: string[];
};

export async function sendRevisionMessage(
  message: string,
): Promise<RevisionResponse> {
  const sessionId = getOrCreateSessionId();
  const response = await fetch(
    `${BACKEND_URL}/api/sessions/${sessionId}/messages`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ message }),
    },
  );

  if (!response.ok) {
    throw new Error(`Revision request failed: ${response.status}`);
  }

  return response.json();
}
