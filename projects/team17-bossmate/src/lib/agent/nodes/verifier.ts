import { verifyImage } from "../../verify";
import type { PromotionStateType } from "../state";

export async function verifier(state: PromotionStateType) {
  const attempt = (state.attempt ?? 0) + 1;

  if (!state.image || state.image.source !== "azure") {
    return {
      attempt,
      verification: {
        ok: true,
        missing: [],
        extracted: {},
        attempted: attempt,
        skipped: true,
        notes: "임시 이미지라 확인을 건너뛰었어요.",
      },
      agentTrace: [
        {
          step: "Verifier",
          summary: "임시 이미지라 확인을 건너뛰었어요.",
        },
      ],
    };
  }

  const verification = await verifyImage(state.image.dataUrl, state.request, attempt);

  let summary: string;
  if (verification.skipped) {
    summary = `확인을 건너뛰었어요: ${verification.notes ?? "사유 미상"}`;
  } else if (verification.ok) {
    summary = `핵심 내용이 잘 들어갔는지 확인 완료 (${attempt}회차).`;
  } else {
    summary = `누락된 항목이 있어 다시 만들어요: ${verification.missing.join(", ")} (${attempt}회차).`;
  }

  return {
    attempt,
    verification,
    agentTrace: [{ step: "Verifier", summary }],
  };
}
