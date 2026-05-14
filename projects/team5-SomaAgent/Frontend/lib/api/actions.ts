import { apiFetch } from "@/lib/api";
import type { ActionResult, ActionType } from "@/lib/types/action";

export type ExecuteActionArgs = {
  actionType: ActionType;
  payload: {
    mentoringId: string;
    applySn?: number;
    qustnrSn?: number;
  };
};

// docs/spec/API.md §3.1 POST /api/v1/actions/execute
// 응답이 ActionExecutionResponse(=ActionResult) 형태로 그대로 반환된다.
export async function executeAction(
  args: ExecuteActionArgs,
  options: { signal?: AbortSignal; sessionId?: string } = {},
): Promise<ActionResult> {
  return apiFetch<ActionResult>("/api/v1/actions/execute", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(options.sessionId
        ? { "X-Soma-Session": options.sessionId }
        : {}),
    },
    body: JSON.stringify(args),
    signal: options.signal,
  });
}
