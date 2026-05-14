import { Hero } from "@/components/landing/hero";
import { SimpleSteps } from "@/components/landing/simple-steps";
import { LandingCTA } from "@/components/landing/cta";

export default function Home() {
  return (
    <>
      <Hero />
      <SimpleSteps />
      <LandingCTA />
    </>
  );
}
