"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import type { ReactNode } from "react";
import { ApiError } from "@/lib/api";
import {
  fetchWhoami,
  loginUser,
  logoutUser,
  type AuthUser,
  type LoginRequest,
} from "@/lib/auth";

type AuthStatus = "loading" | "unauthenticated" | "authenticated";

type AuthContextValue = {
  status: AuthStatus;
  user: AuthUser | null;
  error: string | null;
  // Promise를 반환해 호출 측이 성공/실패 분기 가능.
  login: (body: LoginRequest) => Promise<AuthUser>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

type ProviderProps = {
  initialUser?: AuthUser | null;
  children: ReactNode;
};

export function AuthProvider({ initialUser = null, children }: ProviderProps) {
  const [user, setUser] = useState<AuthUser | null>(initialUser);
  const [status, setStatus] = useState<AuthStatus>(
    initialUser ? "authenticated" : "loading",
  );
  const [error, setError] = useState<string | null>(null);

  // 사용자가 명시적으로 호출하는 refresh()와, mount 시 실행되는 effect 내부 fetch는
  // 분리해서 작성한다 (react-hooks/set-state-in-effect 룰 회피).
  const refreshTriggerRef = useRef<() => void>(() => {});

  useEffect(() => {
    let cancelled = false;
    let abortController: AbortController | null = null;

    const run = async () => {
      abortController?.abort();
      const controller = new AbortController();
      abortController = controller;

      try {
        const result = await fetchWhoami(controller.signal);
        if (cancelled || controller.signal.aborted) return;
        if (result.authenticated && result.user) {
          setUser(result.user);
          setStatus("authenticated");
        } else {
          setUser(null);
          setStatus("unauthenticated");
        }
        setError(null);
      } catch (cause) {
        if (cancelled || controller.signal.aborted) return;
        setUser(null);
        setStatus("unauthenticated");
        setError(extractMessage(cause));
      }
    };

    refreshTriggerRef.current = () => {
      if (cancelled) return;
      void run();
    };

    void run();

    return () => {
      cancelled = true;
      abortController?.abort();
      refreshTriggerRef.current = () => {};
    };
  }, []);

  const refresh = useCallback(async () => {
    refreshTriggerRef.current();
  }, []);

  const login = useCallback(async (body: LoginRequest) => {
    setStatus("loading");
    setError(null);
    try {
      const next = await loginUser(body);
      setUser(next);
      setStatus("authenticated");
      return next;
    } catch (cause) {
      setUser(null);
      setStatus("unauthenticated");
      // 로그인 컨텍스트에서는 503/UPSTREAM도 자격증명 오류일 수 있음을 함께 안내.
      const message = extractMessage(cause, { context: "login" });
      setError(message);
      // 호출 측에서 동일 메시지를 다시 보여줄 수 있도록 message로 감싼 새 Error 던짐.
      throw new Error(message);
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await logoutUser();
    } catch {
      // 서버 측 실패해도 프론트는 무조건 폐기.
    } finally {
      setUser(null);
      setStatus("unauthenticated");
      setError(null);
    }
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ status, user, error, login, logout, refresh }),
    [status, user, error, login, logout, refresh],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth는 <AuthProvider> 안에서만 사용할 수 있습니다.");
  }
  return ctx;
}

// 컨텍스트가 없는 환경(예: Storybook 단독 컴포넌트) 대응용 nullable 변종.
export function useOptionalAuth(): AuthContextValue | null {
  return useContext(AuthContext);
}

type ExtractMessageOptions = {
  // login 컨텍스트에서는 백엔드의 503 UPSTREAM_UNAVAILABLE 응답이
  // 실제로는 SOMA 자격증명 오류인 경우가 많아 그 가능성을 함께 안내한다.
  context?: "login" | "default";
};

function extractMessage(
  cause: unknown,
  options: ExtractMessageOptions = {},
): string {
  const isLogin = options.context === "login";

  if (cause instanceof ApiError) {
    if (cause.status === 401) {
      return "이메일 또는 비밀번호가 올바르지 않습니다.";
    }
    if (cause.status === 400 && cause.code === "INVALID_REQUEST") {
      return cause.message;
    }
    if (cause.status === 503) {
      if (isLogin) {
        return "로그인에 실패했습니다. 이메일·비밀번호가 정확한지 확인하거나 잠시 후 다시 시도해 주세요.";
      }
      return "백엔드 서비스가 잠시 응답하지 않습니다. 잠시 후 다시 시도해 주세요.";
    }
    return cause.message;
  }
  if (cause instanceof Error) return cause.message;
  return "알 수 없는 오류가 발생했습니다.";
}
