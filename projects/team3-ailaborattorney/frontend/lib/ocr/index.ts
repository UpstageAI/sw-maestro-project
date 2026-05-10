import type { OcrResult } from "./types";
import { ocrWithUpstage } from "./upstage";
import { ocrMock } from "./mock";

export * from "./types";

export async function runOcr(filePath: string): Promise<OcrResult> {
  const key = process.env.UPSTAGE_API_KEY;
  if (key && key.trim().length > 0) {
    try { return await ocrWithUpstage(filePath, key); }
    catch (e) {
      console.warn("[ocr] Upstage 실패, mock으로 fallback:", (e as Error).message);
      return ocrMock(filePath);
    }
  }
  return ocrMock(filePath);
}
