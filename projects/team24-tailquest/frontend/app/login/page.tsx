"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { login, register } from "@/lib/api-auth";
import { getToken, syncWithServerBoot } from "@/lib/auth";

type Mode = "login" | "register";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    syncWithServerBoot().then(() => {
      if (getToken()) router.replace("/chat");
    });
  }, [router]);

  // BE는 register에서 password min_length=8을 요구. login은 길이 무관(가입 시점에
  // 길이 검증된 비밀번호이므로 로그인에서 길이 다시 막을 필요 없음).
  const minPwLen = mode === "register" ? 8 : 1;
  const canSubmit =
    email.trim().length > 0 && password.length >= minPwLen && !loading;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    setError(null);
    setLoading(true);
    try {
      if (mode === "login") {
        await login({ email: email.trim(), password });
      } else {
        await register({
          email: email.trim(),
          password,
          displayName: displayName.trim() || undefined,
        });
      }
      router.replace("/chat");
    } catch (err) {
      setError(err instanceof Error ? err.message : "요청에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  };

  const inputClass =
    "bg-canvas border border-hairline rounded-md px-md py-sm text-body-md text-ink placeholder:text-subtle focus:outline-none focus:border-ink w-full";

  return (
    <main className="flex-1 flex items-center justify-center px-md">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-md flex flex-col gap-lg"
      >
        <header className="text-center">
          <h1 className="text-display-lg text-ink mb-sm">기술 면접 코치</h1>
          <p className="text-body-sm text-muted">
            이메일과 비밀번호로 면접 기록을 보호하세요.
          </p>
        </header>

        {/* Mode segmented control */}
        <div className="flex rounded-md border border-hairline overflow-hidden">
          {(["login", "register"] as Mode[]).map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => {
                setMode(m);
                setError(null);
              }}
              className={[
                "flex-1 py-sm text-body-md font-medium transition-colors",
                mode === m
                  ? "bg-ink text-white"
                  : "bg-canvas text-graphite hover:bg-paper",
              ].join(" ")}
            >
              {m === "login" ? "로그인" : "회원가입"}
            </button>
          ))}
        </div>

        <div className="flex flex-col gap-sm">
          <label className="flex flex-col gap-xs">
            <span className="text-uppercase-tag text-muted">이메일</span>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoFocus
              placeholder="you@example.com"
              autoComplete="email"
              className={inputClass}
            />
          </label>

          <label className="flex flex-col gap-xs">
            <span className="text-uppercase-tag text-muted">비밀번호</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={mode === "register" ? "8자 이상" : "비밀번호"}
              autoComplete={
                mode === "login" ? "current-password" : "new-password"
              }
              className={inputClass}
            />
          </label>

          {mode === "register" && (
            <label className="flex flex-col gap-xs">
              <span className="text-uppercase-tag text-muted">
                이름 <span className="text-subtle">(선택)</span>
              </span>
              <input
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                maxLength={32}
                placeholder="예: 김태호"
                autoComplete="name"
                className={inputClass}
              />
            </label>
          )}
        </div>

        {error && (
          <p className="text-body-sm text-error-text text-center">{error}</p>
        )}

        <button
          type="submit"
          disabled={!canSubmit}
          className="rounded-md bg-rausch text-white py-sm text-body-md font-medium disabled:bg-surface-strong disabled:text-subtle transition-colors"
        >
          {loading
            ? "처리 중…"
            : mode === "login"
              ? "로그인"
              : "회원가입"}
        </button>
      </form>
    </main>
  );
}
