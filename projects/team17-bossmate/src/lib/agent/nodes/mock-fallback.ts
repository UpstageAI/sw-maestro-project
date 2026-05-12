import { createMockImage } from "../../mock-image";
import type { PromotionStateType } from "../state";

export async function mockFallback(state: PromotionStateType) {
  const prompt = state.copy?.imagePrompt ?? "Promotion image placeholder";
  const mock = createMockImage(state.request, prompt);
  return {
    image: { dataUrl: mock.dataUrl, source: "mock" as const },
    agentTrace: [
      {
        step: "MockFallback",
        summary: "임시 디자인으로 대체했어요.",
      },
    ],
  };
}
