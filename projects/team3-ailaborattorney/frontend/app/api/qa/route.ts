import { NextRequest, NextResponse } from "next/server";
import { getDb } from "@/lib/db";
import { qa as agentQa } from "@/lib/agent";

export const runtime = "nodejs";
export const maxDuration = 30;

export async function POST(req: NextRequest) {
  const { contractId, question } = (await req.json()) as { contractId?: string; question?: string };
  if (!contractId || !question || question.trim().length === 0) {
    return NextResponse.json({ error: "contractId and question required" }, { status: 400 });
  }

  const db = getDb();
  const row = db.prepare(
    `SELECT id, parsed_data, rule_result, ai_result FROM contracts WHERE id = ?`
  ).get(contractId) as
    | { id: string; parsed_data: string | null; rule_result: string | null; ai_result: string | null }
    | undefined;
  if (!row) return NextResponse.json({ error: "contract not found" }, { status: 404 });

  const context = {
    parsed: row.parsed_data ? JSON.parse(row.parsed_data) : null,
    rule: row.rule_result ? JSON.parse(row.rule_result) : null,
    ai: row.ai_result ? JSON.parse(row.ai_result) : null,
  };

  const result = await agentQa({ question, context });

  db.prepare(
    `INSERT INTO qa_logs (contract_id, question, answer) VALUES (?, ?, ?)`
  ).run(contractId, question, result.answer);

  return NextResponse.json(result);
}

export async function GET(req: NextRequest) {
  const url = new URL(req.url);
  const contractId = url.searchParams.get("contractId");
  if (!contractId) return NextResponse.json({ error: "contractId required" }, { status: 400 });
  const db = getDb();
  const rows = db.prepare(
    `SELECT id, question, answer, created_at FROM qa_logs WHERE contract_id = ? ORDER BY id ASC`
  ).all(contractId);
  return NextResponse.json({ logs: rows });
}
