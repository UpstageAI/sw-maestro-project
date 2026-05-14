import { useEffect, useState } from 'react';
import type { BriefingResult } from '../types';
import { sendEmail } from '../api';

interface Props {
  briefingResult: BriefingResult | null;
  defaultRecipient?: string;
}

export default function EmailSection({ briefingResult, defaultRecipient = '' }: Props) {
  const [recipient, setRecipient] = useState(defaultRecipient);

  useEffect(() => {
    if (defaultRecipient) setRecipient(defaultRecipient);
  }, [defaultRecipient]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const handleSend = async () => {
    if (!briefingResult || !recipient.trim()) return;
    setLoading(true);
    setMessage(null);
    try {
      await sendEmail(recipient.trim(), briefingResult);
      setMessage({ type: 'success', text: `${recipient.trim()}으로 전송했습니다.` });
    } catch (e: unknown) {
      setMessage({ type: 'error', text: e instanceof Error ? e.message : '전송 실패' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mt-2 bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
      <div className="flex items-center gap-2 mb-1">
        <svg className="w-4 h-4 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
        </svg>
        <h2 className="text-sm font-bold text-slate-800">이메일로 받기</h2>
      </div>
      <p className="text-xs text-slate-400 mb-4">생성된 브리핑을 이메일로 전송합니다.</p>
      <div className="flex gap-2">
        <input
          type="email"
          value={recipient}
          onChange={(e) => setRecipient(e.target.value)}
          placeholder="recipient@example.com"
          className="flex-1 border border-slate-200 rounded-xl px-3.5 py-2.5 text-sm outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100 transition-all"
        />
        <button
          onClick={handleSend}
          disabled={!briefingResult || loading}
          className="px-5 py-2.5 bg-indigo-600 text-white text-sm font-semibold rounded-xl hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed shadow-sm hover:shadow-indigo-200 hover:shadow-md transition-all"
        >
          {loading ? '전송 중...' : '전송'}
        </button>
      </div>
      {message && (
        <div className={`mt-3 text-xs px-3 py-2 rounded-lg font-medium
          ${message.type === 'success' ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-600'}`}>
          {message.text}
        </div>
      )}
    </div>
  );
}
