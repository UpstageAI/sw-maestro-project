"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { TopNav } from "@/components/ui";

import { ConversationView } from "./ConversationView";
import { MatchingPhase } from "./MatchingPhase";
import { ResultView } from "./ResultView";

type Phase = "matching" | "conversation" | "result";

/**
 * 매칭 → 대화 → 결과를 한 페이지의 상태 머신으로 연결.
 * 4단계(백엔드 결합)에서 phase 전환을 실제 status 기반으로 교체한다.
 */
export const ConversationFlow = ({ conversationId: _id }: { conversationId: string }) => {
  const router = useRouter();
  const [phase, setPhase] = useState<Phase>("matching");

  const stepIndex = phase === "matching" ? 1 : phase === "conversation" ? 2 : 3;

  return (
    <>
      <TopNav
        onLogo={() => router.push("/")}
        step={stepIndex}
        totalSteps={4}
        onRestart={() => router.push("/")}
      />
      {phase === "matching" && <MatchingPhase onMatched={() => setPhase("conversation")} />}
      {phase === "conversation" && (
        <ConversationView onComplete={() => setPhase("result")} />
      )}
      {phase === "result" && (
        <ResultView
          onRestart={() => router.push("/")}
          onConnect={() => alert("매칭 요청을 보냈습니다 ✨")}
        />
      )}
    </>
  );
};
