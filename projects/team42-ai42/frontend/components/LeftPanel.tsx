'use client';

import { useState } from 'react';
import { MOCK_TRANSCRIPT } from '@/lib/mockData';

interface LeftPanelProps {
  onStart: (transcript: string) => void;
  onReset: () => void;
  isStreaming: boolean;
}

export default function LeftPanel({ onStart, onReset, isStreaming }: LeftPanelProps) {
  const [text, setText] = useState('');

  const handleStart = () => {
    if (!text.trim() || isStreaming) return;
    onStart(text);
  };

  const handleSample = () => {
    setText(MOCK_TRANSCRIPT);
    onReset();
  };

  return (
    <div className="bg-white border border-[#E6E8EB] rounded-[12px] p-6 flex flex-col gap-3">
      <h2 className="text-[20px] font-bold tracking-[-0.5px] text-[#111827]">
        전사문 입력
      </h2>

      <textarea
        className="flex-1 resize-none border border-[#E6E8EB] rounded-[8px] p-4 text-[15px] leading-[1.87] text-[#111827] placeholder-[#9CA3AF] outline-none focus:border-[#2563EB] min-h-[360px]"
        style={{
          transition: 'border-color 200ms ease, box-shadow 200ms ease',
        }}
        onFocus={e => {
          e.target.style.boxShadow = '0 0 0 3px #EFF6FF';
        }}
        onBlur={e => {
          e.target.style.boxShadow = 'none';
        }}
        placeholder="회의 전사문을 입력하세요..."
        value={text}
        onChange={e => setText(e.target.value)}
        disabled={isStreaming}
      />

      <div className="flex gap-3">
        <button
          onClick={handleStart}
          disabled={!text.trim() || isStreaming}
          className="flex-1 flex items-center justify-center gap-2 bg-[#2563EB] text-white text-[15px] font-bold rounded-[8px] py-[14px] disabled:opacity-50 disabled:cursor-not-allowed"
          style={{ transition: 'background-color 150ms ease' }}
          onMouseEnter={e => { if (!e.currentTarget.disabled) e.currentTarget.style.backgroundColor = '#1D4ED8'; }}
          onMouseLeave={e => { e.currentTarget.style.backgroundColor = '#2563EB'; }}
        >
          <PlayIcon />
          분석 시작
        </button>

        <button
          onClick={handleSample}
          disabled={isStreaming}
          className="flex-1 flex items-center justify-center gap-2 bg-white border border-[#E6E8EB] text-[#374151] text-[15px] font-bold rounded-[8px] py-[14px] disabled:opacity-50 disabled:cursor-not-allowed"
          style={{ transition: 'background-color 150ms ease' }}
          onMouseEnter={e => { if (!e.currentTarget.disabled) e.currentTarget.style.backgroundColor = '#F9FAFB'; }}
          onMouseLeave={e => { e.currentTarget.style.backgroundColor = '#FFFFFF'; }}
        >
          샘플 불러오기
        </button>
      </div>

      <p className="text-[13px] text-[#9CA3AF]">ⓘ 전사문 기반 분석</p>
    </div>
  );
}

function PlayIcon() {
  return (
    <svg width="14" height="16" viewBox="0 0 14 16" fill="none">
      <path d="M1 1.5L13 8L1 14.5V1.5Z" fill="currentColor" />
    </svg>
  );
}
