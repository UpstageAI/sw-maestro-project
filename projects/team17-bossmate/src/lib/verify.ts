import type { PromotionRequest, Verification } from "./types";

type ExtractedFields = {
  storeName?: string | null;
  dish?: string | null;
  benefit?: string | null;
  koreanText?: string[];
};

type IEResponse = {
  choices?: Array<{ message?: { content?: string } }>;
};

const extractionSchema = {
  name: "promotion_card_fields",
  schema: {
    type: "object",
    properties: {
      storeName: {
        type: "string",
        description:
          "The store/brand name shown prominently on the image, in Korean if present. Empty string if not visible.",
      },
      dish: {
        type: "string",
        description:
          "The featured menu item or dish name on the image, in Korean if present. Empty string if not visible.",
      },
      benefit: {
        type: "string",
        description:
          "The promotional benefit phrase such as discount, event, new-menu badge, or call-to-action, in Korean if present. Empty string if not visible.",
      },
      koreanText: {
        type: "array",
        items: { type: "string" },
        description: "All distinct Korean text phrases that appear on the image.",
      },
    },
    required: ["storeName", "dish", "benefit", "koreanText"],
  },
};

function normalize(value: string): string {
  return value.replace(/\s+/g, "").toLowerCase();
}

function imageContainsPhrase(haystackText: string[], phrase: string): boolean {
  const normalizedPhrase = normalize(phrase);
  if (!normalizedPhrase) return true;
  return haystackText.some((piece) => normalize(piece).includes(normalizedPhrase));
}

function buildMissingList(request: PromotionRequest, extracted: ExtractedFields): string[] {
  const haystack = [
    extracted.storeName ?? "",
    extracted.dish ?? "",
    extracted.benefit ?? "",
    ...(extracted.koreanText ?? []),
  ].filter(Boolean);

  const missing: string[] = [];
  const storeName = request.store.storeName?.trim();
  if (storeName && !imageContainsPhrase(haystack, storeName)) {
    missing.push(`상호명 "${storeName}"`);
  }

  const detail = request.detail?.trim();
  if (detail) {
    const detailTokens = detail.split(/\s+/).filter((t) => t.length >= 2);
    const headline = detailTokens.slice(0, 2).join(" ");
    if (headline && !imageContainsPhrase(haystack, headline)) {
      missing.push(`핵심 메시지 "${headline}"`);
    }
  }

  return missing;
}

export function isUpstageConfigured() {
  return Boolean(process.env.UPSTAGE_API_KEY);
}

export async function verifyImage(
  pngDataUrl: string,
  request: PromotionRequest,
  attempt: number,
): Promise<Verification> {
  if (!isUpstageConfigured()) {
    return {
      ok: true,
      missing: [],
      extracted: {},
      attempted: attempt,
      skipped: true,
      notes: "UPSTAGE_API_KEY 미설정으로 검증을 건너뛰었습니다.",
    };
  }

  const baseUrl = process.env.UPSTAGE_BASE_URL ?? "https://api.upstage.ai/v1";
  const url = `${baseUrl.replace(/\/$/, "")}/information-extraction`;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 60000);

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${process.env.UPSTAGE_API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: "information-extract",
        response_format: {
          type: "json_schema",
          json_schema: extractionSchema,
        },
        messages: [
          {
            role: "user",
            content: [{ type: "image_url", image_url: { url: pngDataUrl } }],
          },
        ],
      }),
      signal: controller.signal,
    });

    if (!response.ok) {
      return {
        ok: true,
        missing: [],
        extracted: {},
        attempted: attempt,
        skipped: true,
        notes: `Upstage IE HTTP ${response.status} — 검증을 건너뛰었습니다.`,
      };
    }

    const data = (await response.json()) as IEResponse;
    const content = data.choices?.[0]?.message?.content;
    if (!content) {
      return {
        ok: true,
        missing: [],
        extracted: {},
        attempted: attempt,
        skipped: true,
        notes: "Upstage IE 응답이 비어 있어 검증을 건너뛰었습니다.",
      };
    }

    let extracted: ExtractedFields = {};
    try {
      extracted = JSON.parse(content) as ExtractedFields;
    } catch {
      return {
        ok: true,
        missing: [],
        extracted: {},
        attempted: attempt,
        skipped: true,
        notes: "Upstage IE 결과 파싱에 실패하여 검증을 건너뛰었습니다.",
      };
    }

    const missing = buildMissingList(request, extracted);

    return {
      ok: missing.length === 0,
      missing,
      extracted,
      attempted: attempt,
    };
  } catch {
    return {
      ok: true,
      missing: [],
      extracted: {},
      attempted: attempt,
      skipped: true,
      notes: "Upstage IE 호출이 실패하여 검증을 건너뛰었습니다.",
    };
  } finally {
    clearTimeout(timeout);
  }
}
