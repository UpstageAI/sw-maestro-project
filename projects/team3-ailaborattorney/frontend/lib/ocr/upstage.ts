import fs from "node:fs";
import path from "node:path";
import type { OcrResult } from "./types";

const ENDPOINT = "https://api.upstage.ai/v1/document-ai/document-parse";

function htmlToText(html: string): string {
  return html
    .replace(/<\s*br\s*\/?>/gi, "\n")
    .replace(/<\/(p|div|li|tr|h[1-6])>/gi, "\n")
    .replace(/<[^>]+>/g, " ")
    .replace(/&nbsp;/gi, " ")
    .replace(/&amp;/gi, "&")
    .replace(/&lt;/gi, "<")
    .replace(/&gt;/gi, ">")
    .replace(/&#(\d+);/g, (_, n) => String.fromCodePoint(Number(n)))
    .replace(/[ \t]+/g, " ")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

export async function ocrWithUpstage(filePath: string, apiKey: string): Promise<OcrResult> {
  const abs = path.resolve(filePath);
  if (!fs.existsSync(abs)) throw new Error(`file not found: ${abs}`);
  const buf = fs.readFileSync(abs);
  const filename = path.basename(abs);
  // Node 20+ has FormData/Blob globals
  const form = new FormData();
  form.append("document", new Blob([buf]), filename);
  form.append("model", "document-parse");
  // Document Parse 는 기본적으로 content.html 만 채우는 경우가 많아서
  // markdown/text 도 함께 요청해 둔다.
  form.append("output_formats", "['html','markdown','text']");
  const res = await fetch(ENDPOINT, {
    method: "POST",
    headers: { Authorization: `Bearer ${apiKey}` },
    body: form,
  });
  if (!res.ok) {
    const t = await res.text().catch(() => "");
    throw new Error(`Upstage OCR failed: ${res.status} ${t}`);
  }
  const json: any = await res.json();
  const c = json?.content ?? {};
  const text: string =
    (typeof c.text === "string" && c.text.trim().length > 0 && c.text) ||
    (typeof c.markdown === "string" && c.markdown.trim().length > 0 && c.markdown) ||
    (typeof c.html === "string" && c.html.trim().length > 0 && htmlToText(c.html)) ||
    (typeof json?.text === "string" && json.text) ||
    "";
  return { text, source: "upstage", raw: json };
}
