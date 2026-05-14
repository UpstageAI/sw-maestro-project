import type { PromotionRequest, SolarCopy } from "./types";

const purposeLabels: Record<PromotionRequest["purpose"], string> = {
  "new-menu": "신메뉴 출시",
  event: "이벤트",
  daily: "일상 홍보",
  reopening: "재오픈/리뉴얼",
  review: "단골 후기",
};

function fallbackCopy(request: PromotionRequest): SolarCopy {
  const storeName = request.store.storeName || "우리 가게";
  const category = request.store.category || "가게";
  const detail = request.detail || purposeLabels[request.purpose];
  const vibe = request.store.vibe || "따뜻한";
  const feedbackLine = request.feedback ? `\n요청하신 방향도 반영했어요: ${request.feedback}` : "";

  return {
    copyText: `${storeName}에서 준비한 ${detail} 소식입니다.\n${vibe} 분위기의 ${category} 감성을 담아 오늘 방문하고 싶은 이유를 전해드려요.${feedbackLine}\n가볍게 들러 특별한 순간을 만나보세요.`,
    hashtags: ["우리동네가게", "소상공인", category.replace(/\s+/g, ""), detail.replace(/\s+/g, "")].filter(Boolean),
    imagePrompt: `${category} 매장의 ${detail} 홍보용 SNS 이미지, ${vibe} 톤, 깔끔한 구성, 메뉴와 분위기가 잘 보이는 장면`,
    tone: vibe,
    source: "fallback",
  };
}

function parseSolarJson(content: string, request: PromotionRequest): SolarCopy {
  const parsed = JSON.parse(content) as Partial<SolarCopy>;
  if (!parsed.copyText || !Array.isArray(parsed.hashtags) || !parsed.imagePrompt) {
    return fallbackCopy(request);
  }

  return {
    copyText: String(parsed.copyText),
    hashtags: parsed.hashtags.map(String).slice(0, 6),
    imagePrompt: String(parsed.imagePrompt),
    tone: parsed.tone ? String(parsed.tone) : request.store.vibe,
    source: "solar",
  };
}

export function isSolarConfigured() {
  return Boolean(process.env.UPSTAGE_API_KEY);
}

export async function generateSolarCopy(request: PromotionRequest): Promise<SolarCopy> {
  if (!process.env.UPSTAGE_API_KEY) {
    return fallbackCopy(request);
  }

  const baseUrl = process.env.UPSTAGE_BASE_URL ?? "https://api.upstage.ai/v1";
  const model = process.env.UPSTAGE_MODEL ?? "solar-pro3";
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);

  try {
    const response = await fetch(`${baseUrl.replace(/\/$/, "")}/chat/completions`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${process.env.UPSTAGE_API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model,
        temperature: 0.6,
        response_format: { type: "json_object" },
        messages: [
          {
            role: "system",
            content: [
              "You are a Korean small-business SNS promotion copywriter.",
              "",
              "Return ONLY a strict JSON object with these keys:",
              "- copyText: Korean promotion copy. MUST hit the target Korean character count for the platform (count each Hangul/space/punctuation as 1):",
              "  • instagram: 80-150 chars, 2-3 short sentences. Hook the reader fast.",
              "  • naver: 200-350 chars, 3-4 sentences. Search-friendly, descriptive tone.",
              "  • baemin: 120-200 chars, 2-3 sentences. Menu appeal and ordering CTA.",
              "  If the natural copy is below the lower bound, EXPAND with sensory detail, target-customer scenario, or visit/order invitation — but ONLY using information present in the input.",
              '- hashtags: array of 4-6 Korean hashtags as plain text WITHOUT the leading "#".',
              "- imagePrompt: English description for an image generation model.",
              "  TARGET STYLE: Instagram promotional card / 카드뉴스 — NOT a realistic photograph or candid storefront.",
              "  Composition:",
              "    • Clean background: soft color gradient, blurred food close-up, or minimalist solid color with brand accent",
              "    • Bold large Korean headline text taking 30-50% of the frame (storeName + key message)",
              "    • Optional secondary smaller Korean line",
              "    • Modern flat/illustrated style OR hero food shot with an overlay text panel",
              "    • Square or vertical layout with intentional text margins",
              "  Avoid: storefront/exterior signage, candid restaurant scenes, photojournalistic angles, busy backgrounds with crowds.",
              '  Preserve the menu/dish name from the input EXACTLY. Use the exact Korean phrase inside double quotes AND its romanization, e.g. "된장찌개" doenjang jjigae. Do NOT substitute a different dish.',
              '  Always include the exact Korean phrase(s) for storeName and the key benefit/menu in double quotes within the prompt, e.g. text "소마분식" and "된장찌개 한상 신메뉴" displayed prominently with strong typography.',
              '- tone: a short Korean phrase describing the brand/copy tone (e.g. "따뜻하고 정감 있는").',
              "",
              "Hard rules:",
              "- Do NOT invent details. No fabricated discounts, prices, ingredients, customer types, or unrelated dishes. Use only facts from the input.",
              "- Always include the storeName and the core item from 'detail' inside copyText, naturally.",
              "- Use natural Korean SNS register; avoid stiff/formal language.",
              "- Avoid superlatives like 최고, 1등, 최저가, 절대.",
              "- No medical or adult content.",
              "- If feedback is provided, reflect the requested adjustment while keeping format and rules.",
              "- Output JSON only — no markdown fences, no explanation.",
            ].join("\n"),
          },
          {
            role: "user",
            content: JSON.stringify({
              store: request.store,
              purpose: purposeLabels[request.purpose],
              detail: request.detail,
              platform: request.platform ?? "instagram",
              feedback: request.feedback ?? "",
            }),
          },
        ],
      }),
      signal: controller.signal,
    });

    if (!response.ok) {
      return fallbackCopy(request);
    }

    const data = (await response.json()) as {
      choices?: Array<{ message?: { content?: string } }>;
    };
    const content = data.choices?.[0]?.message?.content;
    if (!content) {
      return fallbackCopy(request);
    }

    return parseSolarJson(content, request);
  } catch {
    return fallbackCopy(request);
  } finally {
    clearTimeout(timeout);
  }
}
