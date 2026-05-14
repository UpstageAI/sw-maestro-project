"use client";

import { useRouter } from "next/navigation";

import { PersonaForm } from "@/components/screens/PersonaForm";
import { TopNav } from "@/components/ui";

export default function PersonaNewPage() {
  const router = useRouter();

  // 4단계에서 useCreateAgent + useMatch 로 교체. 지금은 mock 흐름.
  const handleNext = () => {
    router.push("/conversations/demo");
  };

  return (
    <>
      <TopNav
        onLogo={() => router.push("/")}
        step={0}
        totalSteps={4}
        onRestart={() => router.push("/")}
      />
      <PersonaForm onNext={handleNext} onBack={() => router.push("/")} />
    </>
  );
}
