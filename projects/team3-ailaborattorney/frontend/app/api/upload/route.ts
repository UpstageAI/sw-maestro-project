import { NextRequest, NextResponse } from "next/server";
import { randomUUID } from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { getDb } from "@/lib/db";

export const runtime = "nodejs";

export async function POST(req: NextRequest) {
  const form = await req.formData();
  const file = form.get("file");
  if (!(file instanceof File)) {
    return NextResponse.json({ error: "file is required" }, { status: 400 });
  }
  const weekly = form.get("weekly_hours");
  const age = form.get("age");

  const id = randomUUID();
  const safeName = file.name.replace(/[^\w.\-가-힣]/g, "_");
  const uploadsDir = path.join(process.cwd(), "uploads");
  fs.mkdirSync(uploadsDir, { recursive: true });
  const filePath = path.join(uploadsDir, `${id}-${safeName}`);
  const buf = Buffer.from(await file.arrayBuffer());
  fs.writeFileSync(filePath, buf);

  const userInfo: Record<string, number> = {};
  if (weekly && weekly !== "") userInfo.weekly_hours = Number(weekly);
  if (age && age !== "") userInfo.age = Number(age);

  const db = getDb();
  db.prepare(
    `INSERT INTO contracts (id, file_path, original_name, user_info) VALUES (?, ?, ?, ?)`
  ).run(id, filePath, file.name, JSON.stringify(userInfo));

  return NextResponse.json({ id, filePath });
}
