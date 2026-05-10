// 빈 상태 대기 그래픽 — 돼지저금통, stroke에 보라 그라데이션.
// 본체+코는 떠다니고(orb-float), 눈은 깜빡(orb-twinkle-a).
// lucide piggy-bank base + 등 위에 동전 투입구 슬롯 line을 추가해 저금통 의미를 명시.

export function PendingOrb() {
  return (
    <div
      className="flex flex-col items-center gap-3"
      role="status"
      aria-label="입력을 기다리는 중"
    >
      <svg
        width="64"
        height="64"
        viewBox="0 0 24 24"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden
        style={{
          filter: 'drop-shadow(0 4px 10px rgba(139,92,246,0.30))',
          animation: 'orb-float 3.6s ease-in-out infinite',
        }}
      >
        <defs>
          <linearGradient
            id="violet-stroke"
            x1="0"
            y1="0"
            x2="1"
            y2="1"
            gradientUnits="objectBoundingBox"
          >
            <stop offset="0%" stopColor="#5b21b6" />
            <stop offset="100%" stopColor="#a78bfa" />
          </linearGradient>
          {/* 짧은 line·circle용 — 그라데이션이 작아도 안정적으로 보이도록 단색 violet */}
          <linearGradient id="violet-solid" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#7c3aed" />
            <stop offset="100%" stopColor="#7c3aed" />
          </linearGradient>
        </defs>

        {/* 본체 (lucide piggy-bank) */}
        <path
          d="M11 17h3v2a1 1 0 0 0 1 1h2a1 1 0 0 0 1-1v-3a3.16 3.16 0 0 0 2-2h1a1 1 0 0 0 1-1v-2a1 1 0 0 0-1-1h-1a5 5 0 0 0-2-4V3a4 4 0 0 0-3.2 1.6l-.3.4H11a6 6 0 0 0-6 6v1a5 5 0 0 0 2 4v3a1 1 0 0 0 1 1h2a1 1 0 0 0 1-1z"
          stroke="url(#violet-stroke)"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          fill="none"
        />

        {/* 코(주둥이) — lucide piggy-bank 좌측 곡선 */}
        <path
          d="M2 8v1a2 2 0 0 0 2 2h1"
          stroke="#6d28d9"
          strokeWidth="1.7"
          strokeLinecap="round"
          strokeLinejoin="round"
          fill="none"
        />

        {/* 동전 투입구 슬롯 — 등 좌측, 본체 톤과 어우러지도록 반투명 */}
        <line
          x1="10"
          y1="6.9"
          x2="12.5"
          y2="6.9"
          stroke="#6d28d9"
          strokeOpacity="0.55"
          strokeWidth="1.4"
          strokeLinecap="round"
        />

        {/* 눈 — 단색 violet 점, 깜빡 */}
        <circle
          cx="16"
          cy="10"
          r="0.7"
          fill="#5b21b6"
          style={{ animation: 'orb-twinkle-a 2.4s ease-in-out infinite' }}
        />
      </svg>
      <p
        className="text-[13px] font-semibold tracking-tight"
        style={{
          // shorthand `background` 대신 longhand `backgroundImage`로 분리.
          // React가 `background`(shorthand)와 `backgroundClip`(non-shorthand)이 같이 쓰일 때
          // 충돌 가능성을 경고하므로, 충돌 없이 명시적으로 image만 지정한다.
          backgroundImage: 'linear-gradient(135deg, #5b21b6 0%, #8b5cf6 100%)',
          WebkitBackgroundClip: 'text',
          backgroundClip: 'text',
          color: 'transparent',
          opacity: 0.7,
        }}
      >
        무엇이든 물어보세요.
      </p>
    </div>
  );
}
