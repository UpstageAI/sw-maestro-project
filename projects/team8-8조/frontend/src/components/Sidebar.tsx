import type { AppSettings } from '../types';

interface Props {
  settings: AppSettings | null;
  perKeywordLimit: number;
  topK: number;
  onPerKeywordLimitChange: (v: number) => void;
  onTopKChange: (v: number) => void;
}

export default function Sidebar({ settings, perKeywordLimit, topK, onPerKeywordLimitChange, onTopKChange }: Props) {
  return (
    <aside className="w-56 shrink-0 flex flex-col gap-3">
      {settings && (
        <div className="bg-white rounded-2xl border border-slate-200 p-4 shadow-sm">
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">환경 정보</p>
          <div className="space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="text-xs text-slate-500">AI 모드</span>
              <span className={`text-xs px-2.5 py-1 rounded-full font-semibold
                ${settings.ai_mode === 'Upstage'
                  ? 'bg-emerald-100 text-emerald-700'
                  : 'bg-amber-100 text-amber-700'}`}>
                {settings.ai_mode}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs text-slate-500">뉴스 소스</span>
              <span className={`text-xs px-2.5 py-1 rounded-full font-semibold
                ${settings.news_source === 'Naver(한글) + Google'
                  ? 'bg-blue-100 text-blue-700'
                  : 'bg-slate-100 text-slate-600'}`}>
                {settings.news_source === 'Naver(한글) + Google' ? 'Naver+Google' : 'Google only'}
              </span>
            </div>
            <div className="text-xs text-slate-400 truncate pt-1 border-t border-slate-100" title={settings.chroma_path}>
              {settings.chroma_path}
            </div>
          </div>
        </div>
      )}

      <div className="bg-white rounded-2xl border border-slate-200 p-4 shadow-sm">
        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-4">수집 설정</p>
        <div className="space-y-5">
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-medium text-slate-600">키워드별 수집 수</label>
              <span className="text-sm font-bold text-indigo-600">{perKeywordLimit}</span>
            </div>
            <input
              type="range"
              min={1}
              max={20}
              value={perKeywordLimit}
              onChange={(e) => onPerKeywordLimitChange(Number(e.target.value))}
              className="w-full accent-indigo-600"
            />
            <div className="flex justify-between text-xs text-slate-300 mt-1">
              <span>1</span>
              <span>20</span>
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-medium text-slate-600">브리핑 기사 수</label>
              <span className="text-sm font-bold text-indigo-600">{topK}</span>
            </div>
            <input
              type="range"
              min={3}
              max={12}
              value={topK}
              onChange={(e) => onTopKChange(Number(e.target.value))}
              className="w-full accent-indigo-600"
            />
            <div className="flex justify-between text-xs text-slate-300 mt-1">
              <span>3</span>
              <span>12</span>
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}
