import { promotionGraph } from "./agent/graph";
import { createMockImage } from "./mock-image";
import { patchJob } from "./store";
import type { GeneratedContent, PromotionRequest } from "./types";
import type { PromotionStateType } from "./agent/state";

export async function runPromotionJob(
  jobId: string,
  request: PromotionRequest,
): Promise<void> {
  await patchJob(jobId, { status: "processing", agentTrace: [] });

  try {
    let lastState: PromotionStateType | undefined;

    for await (const chunk of await promotionGraph.stream(
      { request },
      { streamMode: "values" },
    )) {
      lastState = chunk as PromotionStateType;
      await patchJob(jobId, {
        agentTrace: lastState.agentTrace ?? [],
      });
    }

    if (!lastState?.copy) {
      throw new Error("Promotion graph produced no copy output.");
    }

    const mockMeta = createMockImage(request, lastState.copy.imagePrompt);
    const imageDataUrl = lastState.image?.dataUrl ?? mockMeta.dataUrl;
    const imageSource = lastState.image?.source ?? "mock";

    const result: GeneratedContent = {
      id: jobId,
      request,
      copyText: lastState.copy.copyText,
      hashtags: lastState.copy.hashtags,
      imagePrompt: lastState.copy.imagePrompt,
      mockImage: { ...mockMeta, dataUrl: imageDataUrl },
      source: lastState.copy.source,
      verification: lastState.verification,
      imageSource,
      createdAt: new Date().toISOString(),
      agentTrace: lastState.agentTrace ?? [],
    };

    await patchJob(jobId, {
      status: "done",
      result,
      agentTrace: result.agentTrace,
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    await patchJob(jobId, { status: "error", error: message });
  }
}
