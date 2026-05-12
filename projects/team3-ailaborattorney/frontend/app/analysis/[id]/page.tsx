import { getDb } from "@/lib/db";
import AnalyzeTrigger from "./analyze-trigger";
import QaChat from "@/components/qa-chat";

type Row = {
  id: string;
  file_path: string;
  original_name: string | null;
  parsed_data: string | null;
  rule_result: string | null;
  ai_result: string | null;
  user_info: string | null;
};

export default async function AnalysisPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const db = getDb();
  const row = db.prepare(
    `SELECT id, file_path, original_name, parsed_data, rule_result, ai_result, user_info
     FROM contracts WHERE id = ?`
  ).get(id) as Row | undefined;

  if (!row) {
    return (
      <section className="space-y-3 pt-6">
        <h1 className="text-[24px] font-bold tracking-tight text-grey-900">분석 결과</h1>
        <div className="rounded-2xl bg-danger-bg p-5">
          <p className="text-[14px] font-semibold text-danger">해당 계약서를 찾을 수 없어요.</p>
          <p className="mt-1 text-[12px] text-grey-700">URL을 다시 확인하거나 새로 업로드해주세요.</p>
        </div>
      </section>
    );
  }

  const initial = {
    id: row.id,
    parsed: row.parsed_data ? JSON.parse(row.parsed_data) : null,
    rule: row.rule_result ? JSON.parse(row.rule_result) : null,
    ai: row.ai_result ? JSON.parse(row.ai_result) : null,
  };

  return (
    <section className="space-y-9">
      <header className="space-y-2 pt-2">
        <span className="inline-flex items-center gap-1.5 rounded-full bg-toss-blue-bg px-2.5 py-1 text-[11px] font-semibold text-toss-blue">
          STEP 2 · 분석 결과
        </span>
        <h1 className="text-[24px] sm:text-[28px] font-bold tracking-tight text-grey-900 leading-tight">
          계약서 검토 결과
        </h1>
        <p className="flex items-center gap-1.5 text-[13px] text-grey-500 truncate">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
          </svg>
          <span className="truncate">{row.original_name ?? row.file_path}</span>
        </p>
      </header>

      <div>
        <AnalyzeTrigger id={id} initial={initial as any} />
      </div>

      <div className="space-y-3">
        <div className="space-y-1">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-grey-100 px-2.5 py-1 text-[11px] font-semibold text-grey-700">
            STEP 3 · 추가 질문
          </span>
          <h2 className="text-[18px] font-bold tracking-tight text-grey-900">계약서에 대해 더 물어보세요</h2>
          <p className="text-[13px] text-grey-500">근로기준법, 권리, 조항 해석 등 무엇이든 OK</p>
        </div>
        <QaChat contractId={id} />
      </div>
    </section>
  );
}
