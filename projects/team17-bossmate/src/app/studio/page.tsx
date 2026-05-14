import type { Metadata } from "next";
import { WizardShell } from "@/components/studio/wizard-shell";

export const metadata: Metadata = {
  title: "스튜디오",
  description:
    "가게 정보만 입력하면 AI 에이전트가 카드 한 장과 SNS 캡션을 만들어 드려요.",
};

export default function StudioPage() {
  return <WizardShell />;
}
