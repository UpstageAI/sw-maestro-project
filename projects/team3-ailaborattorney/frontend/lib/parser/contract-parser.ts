import type { ParsedContract } from "./types";

// 한국어 숫자 정규화 (1,800,000 → 1800000)
const numFrom = (s: string): number | undefined => {
  const cleaned = s.replace(/[,원\s]/g, "");
  const n = Number(cleaned);
  return Number.isFinite(n) ? n : undefined;
};

export function parseContract(rawText: string): ParsedContract {
  const t = rawText.replace(/\r/g, "");
  const out: ParsedContract = { rawText: t, contractType: "unknown" };

  // 월급 ("월 1,800,000원", "월급 ...원", "월급여 ...원")
  const m1 = t.match(/월\s*급?(?:여)?\s*[:：]?\s*([\d,]+)\s*원/);
  if (m1) out.monthlyWage = numFrom(m1[1]);

  // 시급 — 다양한 표기 변형 처리
  //  - "시급 11,000원"
  //  - "시간급 / 시간당 11,000원"
  //  - 정부 표준 단시간근로자 양식: "시간(일, 월)급 : 11,000 원"
  const hourlyPatterns: RegExp[] = [
    /시\s*급\s*[:：]?\s*([\d,]+)\s*원/,
    /시간\s*당\s*[:：]?\s*([\d,]+)\s*원/,
    /시간\s*급\s*[:：]?\s*([\d,]+)\s*원/,
    /시간\s*\([^)]*\)\s*급\s*[:：]?\s*([\d,]+)\s*원/,
  ];
  for (const re of hourlyPatterns) {
    const m = t.match(re);
    if (m) {
      out.hourlyWage = numFrom(m[1]);
      break;
    }
  }

  // 주 근로시간 ("주 45시간", "주 40시간" 등)
  const m3 = t.match(/주\s*(\d+)\s*시간/);
  if (m3) out.weeklyHours = Number(m3[1]);

  // 1일 근로시간 ("1일 9시간", "일 8시간")
  const m4 = t.match(/(?:1\s*일|일)\s*(\d+(?:\.\d+)?)\s*시간/);
  if (m4) out.dailyHours = Number(m4[1]);

  // 휴게시간 ("휴게 30분", "휴게시간 ... 30분")
  const m5 = t.match(/휴게(?:시간)?[^\d]*(\d+)\s*분/);
  if (m5) out.breakMinutes = Number(m5[1]);

  // 주휴일 명시
  if (/주휴일|매주\s*\S{1,3}요일/.test(t)) out.weeklyRestDays = 1;

  // 수습 ("수습기간 ... 3개월", "본 임금의 90%")
  const mp = t.match(/수습[^\n]{0,40}?(\d+)\s*개월/);
  if (mp) out.probationMonths = Number(mp[1]);
  const mpr = t.match(/본\s*임금의\s*(\d+)\s*%/);
  if (mpr) out.probationWageRate = Number(mpr[1]) / 100;

  // 계약기간
  const md = t.match(/(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일\s*부터\s*(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일\s*까지/);
  if (md) {
    const [, sy, sm, sd, ey, em, ed] = md;
    const pad = (s: string) => s.padStart(2, "0");
    out.startDate = `${sy}-${pad(sm)}-${pad(sd)}`;
    out.endDate = `${ey}-${pad(em)}-${pad(ed)}`;
    out.contractType = "fixed_term";
  } else if (/기간의\s*정함이\s*없|정규직/.test(t)) {
    out.contractType = "permanent";
  }

  return out;
}
