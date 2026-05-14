import { useState } from 'react';

interface ApiKeyInputProps {
  value: string;
  onChange: (value: string) => void;
}

export default function ApiKeyInput({ value, onChange }: ApiKeyInputProps) {
  const [reveal, setReveal] = useState(false);

  return (
    <div className="space-y-2">
      <label className="block text-sm font-semibold text-gray-700">
        Solar API 키 <span className="text-red-400" aria-label="필수">*</span>
      </label>
      <div className="relative">
        <input
          type={reveal ? 'text' : 'password'}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="up_..."
          autoComplete="off"
          spellCheck={false}
          className="w-full rounded-xl border border-gray-200 bg-white px-3 py-2.5 pr-16 text-sm text-gray-800 placeholder:text-gray-400 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/30"
        />
        <button
          type="button"
          onClick={() => setReveal((v) => !v)}
          className="absolute right-2 top-1/2 -translate-y-1/2 rounded-lg px-2 py-1 text-xs font-medium text-primary hover:bg-cream-dark"
        >
          {reveal ? '숨김' : '보기'}
        </button>
      </div>
      <p className="text-[11px] leading-relaxed text-gray-500">
        키는 세션에만 저장되고 서버 요청 시 헤더로만 전달돼요. 페이지를 닫으면
        지워집니다.{' '}
        <a
          href="https://console.upstage.ai/api-keys"
          target="_blank"
          rel="noreferrer"
          className="underline text-primary"
        >
          키 발급 페이지
        </a>
      </p>
    </div>
  );
}
