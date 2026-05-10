import { ClosingCTA } from "@/components/landing/closing-cta";
import { EvaluationAxes } from "@/components/landing/evaluation-axes";
import { Hero } from "@/components/landing/hero";
import { PainPoints } from "@/components/landing/pain-points";
import { Steps } from "@/components/landing/steps";

export default function Home() {
  return (
    <>
      <Hero />
      <PainPoints />
      <Steps />
      <EvaluationAxes />
      <ClosingCTA />
    </>
  );
}
