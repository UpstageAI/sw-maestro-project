/** @type {import('next').NextConfig} */
const nextConfig = {
  // Strict mode is OFF.
  //
  // Reason: dev double-invokes every effect, which collides with our
  // chat-shell mount effect — the cleanup aborts the in-flight
  // generateSeedQuestion fetch (via AbortController), the second pass
  // sees `seededSessionsRef.has("__new__")` and early-returns, and
  // setSeeding(false) is gated behind `!ctrl.signal.aborted` so the
  // user is left stuck on "면접관이 첫 질문을 준비 중입니다…".
  //
  // Production is unaffected — Next.js single-fires effects in prod builds
  // regardless of this flag.
  reactStrictMode: false,
  // Default Next.js rewrite proxy times out at ~30s, which is shorter than
  // a worst-case /sessions run (analyzer + retriever + question_generator +
  // evaluator + optional web_search via Tavily). Bump to 2 min so local dev
  // doesn't ECONNRESET on slow LLM paths. Production goes through nginx and
  // ignores this entirely.
  experimental: {
    proxyTimeout: 120_000,
  },
  async rewrites() {
    const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";
    return [
      {
        source: "/api/backend/:path*",
        destination: `${backendUrl}/:path*`,
      },
    ];
  },
};

export default nextConfig;
