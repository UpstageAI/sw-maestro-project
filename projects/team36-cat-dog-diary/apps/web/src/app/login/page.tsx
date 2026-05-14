"use client";

import { useState } from "react";
import { BrandLogo } from "@/components/brand-logo";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { createSupabaseBrowserClient } from "@/lib/supabase/client";

export default function LoginPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function signInWithGoogle() {
    setLoading(true);
    setError(null);
    const supabase = createSupabaseBrowserClient();
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: `${window.location.origin}/auth/callback`,
      },
    });
    if (error) {
      setError(error.message);
      setLoading(false);
    }
  }

  return (
    <main className="flex flex-1 items-center justify-center p-8">
      <Card className="w-full max-w-md">
        <CardHeader>
          <div className="flex flex-col items-center gap-3 pt-4 text-center">
            <BrandLogo className="size-20 text-primary" />
            <CardTitle className="text-3xl">냥멍일기</CardTitle>
            <CardDescription className="text-base">
              사진 한 장에서 시작하는 반려동물 1인칭 일기
            </CardDescription>
          </div>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 pb-6">
          <Button
            onClick={signInWithGoogle}
            disabled={loading}
            size="lg"
            className="w-full"
          >
            {loading ? "이동 중..." : "Google로 시작하기"}
          </Button>
          {error && (
            <p className="text-sm text-destructive text-center">{error}</p>
          )}
        </CardContent>
      </Card>
    </main>
  );
}
