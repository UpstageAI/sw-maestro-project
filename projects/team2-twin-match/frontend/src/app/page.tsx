"use client";

import { useRouter } from "next/navigation";

import { Landing } from "@/components/screens/Landing";
import { TopNav } from "@/components/ui";

export default function HomePage() {
  const router = useRouter();
  return (
    <>
      <TopNav onLogo={() => router.push("/")} />
      <Landing onStart={() => router.push("/agents/new")} />
    </>
  );
}
