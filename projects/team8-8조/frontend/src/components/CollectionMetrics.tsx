import type { CollectionResult } from '../types';

interface Props {
  result: CollectionResult;
}

export default function CollectionMetrics({ result }: Props) {
  const metrics = [
    { label: '검색 키워드', value: result.keywords.length, color: 'text-slate-800' },
    { label: '수집된 기사', value: result.collected_count, color: 'text-indigo-600' },
    { label: '새로 저장', value: result.stored_count, color: 'text-emerald-600' },
    { label: '중복 제외', value: result.skipped_existing_count, color: 'text-slate-400' },
  ];

  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-5 mb-5 shadow-sm">
      <div className="flex items-center gap-2 mb-4">
        <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
        <p className="text-sm font-semibold text-slate-700">뉴스 수집 완료</p>
      </div>
      <div className="grid grid-cols-4 gap-3">
        {metrics.map(({ label, value, color }) => (
          <div key={label} className="text-center py-3 px-2 bg-slate-50 rounded-xl">
            <div className={`text-3xl font-bold tracking-tight ${color}`}>{value}</div>
            <div className="text-xs text-slate-500 mt-1 font-medium">{label}</div>
          </div>
        ))}
      </div>
      {result.errors.length > 0 && (
        <p className="text-amber-600 text-xs mt-3 bg-amber-50 px-3 py-2 rounded-lg">{result.errors.join(' | ')}</p>
      )}
    </div>
  );
}
