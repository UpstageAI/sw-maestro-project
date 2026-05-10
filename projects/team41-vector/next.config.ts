import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  devIndicators: false,
  serverExternalPackages: ['better-sqlite3'],
  allowedDevOrigins: ['192.168.0.37', '100.90.11.65'],
  // Turbopack이 workspace root를 정확히 잡도록 명시.
  // factpokmoney/는 부모 폴더(Team41_Vector/)와 별도 프로젝트라 자동 추론이 실패함.
  // process.cwd()는 dev/build 명령을 실행한 디렉토리(=factpokmoney/) 기준.
  turbopack: {
    root: process.cwd(),
  },
};

export default nextConfig;
