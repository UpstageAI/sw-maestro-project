import { END, START, StateGraph } from "@langchain/langgraph";
import { copyWriter } from "./nodes/copy-writer";
import { imageGenerator } from "./nodes/image-generator";
import { mockFallback } from "./nodes/mock-fallback";
import { verifier } from "./nodes/verifier";
import { PromotionState, type PromotionStateType } from "./state";

const MAX_VERIFY_ATTEMPTS = 2;

function routeAfterImage(state: PromotionStateType): "success" | "fallback" {
  return state.image ? "success" : "fallback";
}

function routeAfterVerify(state: PromotionStateType): "end" | "retry" {
  const verification = state.verification;
  if (!verification) return "end";
  if (verification.ok || verification.skipped) return "end";
  if ((state.attempt ?? 0) >= MAX_VERIFY_ATTEMPTS) return "end";
  return "retry";
}

export const promotionGraph = new StateGraph(PromotionState)
  .addNode("copyWriter", copyWriter)
  .addNode("imageGenerator", imageGenerator)
  .addNode("mockFallback", mockFallback)
  .addNode("verifier", verifier)
  .addEdge(START, "copyWriter")
  .addEdge("copyWriter", "imageGenerator")
  .addConditionalEdges("imageGenerator", routeAfterImage, {
    success: "verifier",
    fallback: "mockFallback",
  })
  .addEdge("mockFallback", END)
  .addConditionalEdges("verifier", routeAfterVerify, {
    end: END,
    retry: "copyWriter",
  })
  .compile();
