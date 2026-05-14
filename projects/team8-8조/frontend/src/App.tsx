import { useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { collectNews, fetchSettings, generateBriefing } from './api';
import ArticleCard from './components/ArticleCard';
import CollectionMetrics from './components/CollectionMetrics';
import EmailSection from './components/EmailSection';
import Sidebar from './components/Sidebar';
import StepIndicator from './components/StepIndicator';
import type { AppSettings, BriefingResult, CollectionResult } from './types';

export default function App() {
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [perKeywordLimit, setPerKeywordLimit] = useState(3);
  const [topK, setTopK] = useState(5);

  const [interest, setInterest] = useState('AI 산업 동향');
  const [keywordText, setKeywordText] = useState('AI, 반도체, 스타트업');

  const [collectLoading, setCollectLoading] = useState(false);
  const [briefingLoading, setBriefingLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [collectionResult, setCollectionResult] = useState<CollectionResult | null>(() => {
    try { return JSON.parse(localStorage.getItem('collectionResult') || 'null'); } catch { return null; }
  });
  const [briefingResult, setBriefingResult] = useState<BriefingResult | null>(() => {
    try { return JSON.parse(localStorage.getItem('briefingResult') || 'null'); } catch { return null; }
  });

  const step = briefingResult ? 3 : collectionResult ? 2 : 1;

  useEffect(() => {
    if (collectionResult) localStorage.setItem('collectionResult', JSON.stringify(collectionResult));
    else localStorage.removeItem('collectionResult');
  }, [collectionResult]);

  useEffect(() => {
    if (briefingResult) localStorage.setItem('briefingResult', JSON.stringify(briefingResult));
    else localStorage.removeItem('briefingResult');
  }, [briefingResult]);

  useEffect(() => {
    fetchSettings()
      .then((s) => {
        setSettings(s);
        setPerKeywordLimit(s.per_keyword_limit);
        setTopK(s.top_k);
      })
      .catch(() => {});
  }, []);

  const handleCollect = async () => {
    setError(null);
    setCollectLoading(true);
    setCollectionResult(null);
    setBriefingResult(null);
    try {
      const result = await collectNews(interest, keywordText, perKeywordLimit);
      setCollectionResult(result);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '수집 실패');
    } finally {
      setCollectLoading(false);
    }
  };

  const handleBriefing = async () => {
    if (!collectionResult) return;
    setError(null);
    setBriefingLoading(true);
    try {
      const result = await generateBriefing(collectionResult, topK);
      setBriefingResult(result);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '브리핑 생성 실패');
    } finally {
      setBriefingLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-slate-900 px-6 py-4 shadow-lg">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-indigo-500 rounded-xl flex items-center justify-center shadow-md">
              <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 12h6m-6-4h2" />
              </svg>
            </div>
            <div>
              <h1 className="text-base font-bold text-white leading-none">Daily News Agent</h1>
              <p className="text-xs text-slate-400 mt-0.5">AI 기반 맞춤형 뉴스 브리핑</p>
            </div>
          </div>
          {settings && (
            <span className={`text-xs px-3 py-1.5 rounded-full font-semibold ring-1
              ${settings.ai_mode === 'Upstage'
                ? 'bg-emerald-500/20 text-emerald-400 ring-emerald-500/30'
                : 'bg-amber-500/20 text-amber-400 ring-amber-500/30'}`}>
              {settings.ai_mode} 모드
            </span>
          )}
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-6 py-8 flex gap-6">
        <Sidebar
          settings={settings}
          perKeywordLimit={perKeywordLimit}
          topK={topK}
          onPerKeywordLimitChange={setPerKeywordLimit}
          onTopKChange={setTopK}
        />

        <main className="flex-1 min-w-0">
          <StepIndicator step={step as 1 | 2 | 3} />

          {/* Input Card */}
          <div className="bg-white rounded-2xl border border-slate-200 p-5 mb-4 shadow-sm">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">검색 설정</p>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-medium text-slate-600 block mb-1.5">관심 분야</label>
                <input
                  type="text"
                  value={interest}
                  onChange={(e) => setInterest(e.target.value)}
                  className="w-full border border-slate-200 rounded-xl px-3.5 py-2.5 text-sm outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100 transition-all"
                  placeholder="예: AI 산업 동향"
                />
              </div>
              <div>
                <label className="text-xs font-medium text-slate-600 block mb-1.5">검색 키워드 <span className="text-slate-400">(최대 3개, 쉼표 구분)</span></label>
                <input
                  type="text"
                  value={keywordText}
                  onChange={(e) => setKeywordText(e.target.value)}
                  className="w-full border border-slate-200 rounded-xl px-3.5 py-2.5 text-sm outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100 transition-all"
                  placeholder="예: AI, 반도체, 스타트업"
                />
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="grid grid-cols-2 gap-3 mb-5">
            <button
              onClick={handleCollect}
              disabled={collectLoading || briefingLoading}
              className="py-3 bg-indigo-600 text-white text-sm font-semibold rounded-xl hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed shadow-sm hover:shadow-indigo-200 hover:shadow-md transition-all flex items-center justify-center gap-2"
            >
              {collectLoading ? (
                <>
                  <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  수집 중...
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                  뉴스 수집 및 저장
                </>
              )}
            </button>
            <button
              onClick={handleBriefing}
              disabled={!collectionResult || briefingLoading || collectLoading}
              className="py-3 bg-slate-800 text-white text-sm font-semibold rounded-xl hover:bg-slate-900 disabled:opacity-40 disabled:cursor-not-allowed shadow-sm hover:shadow-slate-200 hover:shadow-md transition-all flex items-center justify-center gap-2"
            >
              {briefingLoading ? (
                <>
                  <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  생성 중...
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  브리핑 생성
                </>
              )}
            </button>
          </div>

          {/* Error */}
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-600 text-sm rounded-xl px-4 py-3 mb-4 flex items-center gap-2">
              <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              {error}
            </div>
          )}

          {/* Loading states */}
          {collectLoading && (
            <div className="bg-indigo-50 border border-indigo-200 text-indigo-600 text-sm rounded-xl px-4 py-3 mb-4 flex items-center gap-2">
              <svg className="animate-spin w-4 h-4 shrink-0" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              뉴스를 수집하는 중입니다...
            </div>
          )}
          {briefingLoading && (
            <div className="bg-slate-100 border border-slate-200 text-slate-600 text-sm rounded-xl px-4 py-3 mb-4 flex items-center gap-2">
              <svg className="animate-spin w-4 h-4 shrink-0" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              AI가 브리핑을 생성하는 중입니다...
            </div>
          )}

          {/* Collection Metrics */}
          {collectionResult && !collectLoading && (
            <CollectionMetrics result={collectionResult} />
          )}

          {/* Briefing */}
          {briefingResult && (
            <>
              <div className="bg-white rounded-2xl border border-slate-200 p-6 mb-5 shadow-sm">
                <div className="flex items-center gap-2 mb-4">
                  <div className="w-6 h-6 bg-indigo-100 rounded-lg flex items-center justify-center">
                    <svg className="w-3.5 h-3.5 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                  </div>
                  <h2 className="text-base font-bold text-slate-800">생성된 브리핑</h2>
                </div>
                <div className="prose prose-sm max-w-none text-slate-700 break-words overflow-hidden [&_a]:break-all">
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      a: ({ href, children }) => (
                        <a href={href} target="_blank" rel="noopener noreferrer" className="text-indigo-600 hover:text-indigo-800">
                          {children}
                        </a>
                      ),
                    }}
                  >
                    {briefingResult.briefing_markdown}
                  </ReactMarkdown>
                </div>
              </div>

              <div className="mb-5">
                <div className="flex items-center gap-2 mb-3">
                  <h2 className="text-base font-bold text-slate-800">선별된 기사</h2>
                  <span className="text-xs bg-slate-100 text-slate-500 px-2 py-0.5 rounded-full font-medium">
                    {briefingResult.selected_articles.length}개
                  </span>
                </div>
                <div className="grid grid-cols-3 gap-4">
                  {briefingResult.selected_articles.map((article) => (
                    <ArticleCard key={article.link} article={article} />
                  ))}
                </div>
              </div>
            </>
          )}

          <EmailSection briefingResult={briefingResult} defaultRecipient={settings?.email_to_default} />
        </main>
      </div>
    </div>
  );
}
