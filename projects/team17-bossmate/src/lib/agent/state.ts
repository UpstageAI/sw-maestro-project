import { Annotation } from "@langchain/langgraph";
import type {
  AgentTrace,
  PromotionRequest,
  SolarCopy,
  Verification,
} from "../types";

export type ImageResult = {
  dataUrl: string;
  source: "azure" | "mock";
};

export const PromotionState = Annotation.Root({
  request: Annotation<PromotionRequest>(),
  copy: Annotation<SolarCopy | undefined>(),
  image: Annotation<ImageResult | undefined>(),
  verification: Annotation<Verification | undefined>(),
  attempt: Annotation<number>({
    reducer: (_left, right) => right,
    default: () => 0,
  }),
  agentTrace: Annotation<AgentTrace[]>({
    reducer: (left, right) => left.concat(right),
    default: () => [],
  }),
});

export type PromotionStateType = typeof PromotionState.State;
