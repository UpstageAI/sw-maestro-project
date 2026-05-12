export interface OcrResult {
  text: string;
  source: "upstage" | "mock";
  raw?: unknown;
}
