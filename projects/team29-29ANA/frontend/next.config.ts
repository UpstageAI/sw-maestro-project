import type { NextConfig } from "next";

const BACKEND_BASE_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  // 프론트의 /api/*, /health 요청을 FastAPI 백엔드로 프록시.
  // 같은 origin 처럼 호출되어 CORS 우회 + 도커 통합 시 환경변수만 변경하면 됨.
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${BACKEND_BASE_URL}/api/:path*` },
      { source: "/health", destination: `${BACKEND_BASE_URL}/health` },
    ];
  },
};

export default nextConfig;
