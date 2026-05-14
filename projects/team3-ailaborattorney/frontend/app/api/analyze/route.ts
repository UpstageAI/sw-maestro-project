import { NextRequest, NextResponse } from "next/server";
import { getDb } from "@/lib/db";
import { runOcr } from "@/lib/ocr";
import { parseContract } from "@/lib/parser";
import { runRules } from "@/lib/rules";
import { analyze as agentAnalyze } from "@/lib/agent";

export const runtime = "nodejs";
export const maxDuration = 60;

export async function POST(req: NextRequest) {
  const { id } = (await req.json()) as { id: string };
  if (!id) return NextResponse.json({ error: "id required" }, { status: 400 });

  const db = getDb();
  const row = db.prepare(
    `SELECT id, file_path, user_info FROM contracts WHERE id = ?`
  ).get(id) as { id: string; file_path: string; user_info: string | null } | undefined;
  if (!row) return NextResponse.json({ error: "not found" }, { status: 404 });

  const userInfoRaw = row.user_info ? JSON.parse(row.user_info) : {};
  const userInfo = {
    weeklyHours: userInfoRaw.weekly_hours,
    age: userInfoRaw.age,
  };

  const ocr = await runOcr(row.file_path);
  const parsed = parseContract(ocr.text);
  const rule = runRules(parsed as any, userInfo);
  const ai = await agentAnalyze({
    contract_data: parsed as any,
    rule_result: rule as any,
    user_info: userInfoRaw,
  });

  db.prepare(
    `UPDATE contracts
     SET parsed_data = ?, rule_result = ?, ai_result = ?, updated_at = datetime('now')
     WHERE id = ?`
  ).run(JSON.stringify(parsed), JSON.stringify(rule), JSON.stringify(ai), id);

  return NextResponse.json({
    id,
    ocrSource: ocr.source,
    parsed,
    rule,
    ai,
  });
}

export async function GET(req: NextRequest) {
  const url = new URL(req.url);
  const id = url.searchParams.get("id");
  if (!id) return NextResponse.json({ error: "id required" }, { status: 400 });

  const db = getDb();
  const row = db.prepare(
    `SELECT id, parsed_data, rule_result, ai_result, user_info FROM contracts WHERE id = ?`
  ).get(id) as
    | { id: string; parsed_data: string | null; rule_result: string | null; ai_result: string | null; user_info: string | null }
    | undefined;
  if (!row) return NextResponse.json({ error: "not found" }, { status: 404 });

  return NextResponse.json({
    id: row.id,
    parsed: row.parsed_data ? JSON.parse(row.parsed_data) : null,
    rule: row.rule_result ? JSON.parse(row.rule_result) : null,
    ai: row.ai_result ? JSON.parse(row.ai_result) : null,
    userInfo: row.user_info ? JSON.parse(row.user_info) : null,
  });
}
