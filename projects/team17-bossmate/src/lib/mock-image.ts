import type { MockImage, PromotionRequest } from "./types";

const categoryPalettes: Record<string, string[]> = {
  cafe: ["#f7c8d8", "#7f5539", "#fff7ed", "#d97706"],
  카페: ["#f7c8d8", "#7f5539", "#fff7ed", "#d97706"],
  pizza: ["#ef4444", "#facc15", "#fff7ed", "#166534"],
  피자: ["#ef4444", "#facc15", "#fff7ed", "#166534"],
  flower: ["#f9a8d4", "#22c55e", "#fff1f2", "#be185d"],
  꽃: ["#f9a8d4", "#22c55e", "#fff1f2", "#be185d"],
  hair: ["#111827", "#c084fc", "#f8fafc", "#0f766e"],
  미용: ["#111827", "#c084fc", "#f8fafc", "#0f766e"],
  korean: ["#b45309", "#ef4444", "#fff7ed", "#14532d"],
  한식: ["#b45309", "#ef4444", "#fff7ed", "#14532d"],
};

const purposeLabels: Record<PromotionRequest["purpose"], string> = {
  "new-menu": "신메뉴 출시",
  event: "이벤트",
  daily: "일상 홍보",
  reopening: "재오픈/리뉴얼",
  review: "단골 후기",
};

function escapeXml(value: string) {
  return value.replace(/[<>&"']/g, (char) => {
    const entities: Record<string, string> = {
      "<": "&lt;",
      ">": "&gt;",
      "&": "&amp;",
      '"': "&quot;",
      "'": "&apos;",
    };
    return entities[char] ?? char;
  });
}

function paletteFor(category: string) {
  const normalized = category.toLowerCase();
  const match = Object.entries(categoryPalettes).find(([key]) => normalized.includes(key));
  return match?.[1] ?? ["#1f7a4d", "#2563a7", "#fff7ed", "#cf5f3f"];
}

export function createMockImage(request: PromotionRequest, imagePrompt: string): MockImage {
  const palette = paletteFor(request.store.category);
  const title = `${request.store.storeName || "우리 가게"} ${purposeLabels[request.purpose]}`;
  const motif = request.detail || request.store.category || "오늘의 추천";
  const safeTitle = escapeXml(title);
  const safeMotif = escapeXml(motif);
  const safeVibe = escapeXml(request.store.vibe || "따뜻한 분위기");
  const safePrompt = escapeXml(imagePrompt);

  const svg = `
  <svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1080" viewBox="0 0 1080 1080">
    <defs>
      <linearGradient id="bg" x1="0" x2="1" y1="0" y2="1">
        <stop offset="0%" stop-color="${palette[0]}"/>
        <stop offset="58%" stop-color="${palette[1]}"/>
        <stop offset="100%" stop-color="${palette[2]}"/>
      </linearGradient>
      <filter id="soft" x="-20%" y="-20%" width="140%" height="140%">
        <feGaussianBlur stdDeviation="18"/>
      </filter>
    </defs>
    <rect width="1080" height="1080" fill="url(#bg)"/>
    <circle cx="890" cy="210" r="180" fill="${palette[3]}" opacity="0.32" filter="url(#soft)"/>
    <circle cx="180" cy="870" r="230" fill="#ffffff" opacity="0.24" filter="url(#soft)"/>
    <rect x="96" y="104" width="888" height="872" rx="44" fill="#fffaf2" opacity="0.92"/>
    <rect x="140" y="148" width="800" height="360" rx="34" fill="${palette[2]}" stroke="${palette[1]}" stroke-width="8"/>
    <circle cx="356" cy="328" r="112" fill="${palette[0]}" opacity="0.82"/>
    <circle cx="522" cy="328" r="112" fill="${palette[3]}" opacity="0.58"/>
    <circle cx="688" cy="328" r="112" fill="${palette[1]}" opacity="0.5"/>
    <text x="540" y="606" text-anchor="middle" font-family="Arial, sans-serif" font-size="56" font-weight="800" fill="#18211d">${safeTitle}</text>
    <text x="540" y="684" text-anchor="middle" font-family="Arial, sans-serif" font-size="42" font-weight="700" fill="${palette[1]}">${safeMotif}</text>
    <text x="540" y="744" text-anchor="middle" font-family="Arial, sans-serif" font-size="30" fill="#65706b">${safeVibe}</text>
    <foreignObject x="172" y="790" width="736" height="112">
      <div xmlns="http://www.w3.org/1999/xhtml" style="font-family:Arial,sans-serif;font-size:24px;line-height:1.45;color:#4b5563;text-align:center;word-break:keep-all;">${safePrompt}</div>
    </foreignObject>
  </svg>`;

  return {
    title,
    palette,
    motif,
    dataUrl: `data:image/svg+xml;base64,${Buffer.from(svg).toString("base64")}`,
  };
}
