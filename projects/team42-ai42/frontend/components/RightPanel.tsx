'use client';

import { useState } from 'react';
import type { AnalysisNode, AnalysisResult, AnalysisStatus } from '@/types/analysis';
import ProgressBar from './ProgressBar';
import ResultCard from './ResultCard';

interface RightPanelProps {
  status: AnalysisStatus;
  nodes: AnalysisNode[];
  result: AnalysisResult;
  error: string | null;
  onReset: () => void;
}

export default function RightPanel({ status, nodes, result, error, onReset }: RightPanelProps) {
  const [copied, setCopied] = useState(false);

  const isStreaming = status === 'streaming';
  const hasStarted = status !== 'idle';
  const isError = status === 'error';

  const summaryVisible = hasStarted && nodes.find(n => n.id === 'summary')?.status !== 'pending';
  const decisionVisible = hasStarted && nodes.find(n => n.id === 'decision')?.status !== 'pending';
  const agendaVisible = hasStarted && nodes.find(n => n.id === 'agenda')?.status !== 'pending';

  const handleCopyMarkdown = async () => {
    if (!result.summary && !result.decisions && !result.agenda) return;
    const md = buildMarkdown(result);
    await navigator.clipboard.writeText(md);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="bg-white border border-[#E6E8EB] rounded-[12px] p-6 flex flex-col gap-4 overflow-y-auto">
      {/* 패널 헤더 */}
      <div className="flex items-center justify-between">
        <h2 className="text-[20px] font-bold tracking-[-0.5px] text-[#111827]">분석 결과</h2>
        {isStreaming && (
          <span className="flex items-center gap-1.5 text-[13px] text-[#2563EB] bg-[#EFF6FF] border border-[#BFDBFE] rounded-full px-3 py-1.5">
            <span className="w-2 h-2 rounded-full bg-[#2563EB] animate-pulse shrink-0" />
            실시간 생성
          </span>
        )}
      </div>

      {/* 프로그레스 바 */}
      {hasStarted && (
        <div className="py-2">
          <ProgressBar nodes={nodes} />
        </div>
      )}

      {error && (
        <div className="rounded-[8px] border border-[#FECACA] bg-[#FEF2F2] px-4 py-3 text-[14px] leading-relaxed text-[#991B1B]">
          {error}
        </div>
      )}

      {/* 결과 카드들 */}
      {!hasStarted ? (
        <div className="flex-1 flex items-center justify-center text-[15px] text-[#9CA3AF]">
          좌측에 전사문을 입력하고 분석을 시작하세요.
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          <ResultCard
            icon="📋"
            title="핵심 요약"
            items={result.summary}
            visible={!!summaryVisible}
          />
          <ResultCard
            icon="✅"
            title="결정 사항"
            items={result.decisions}
            visible={!!decisionVisible}
          />
          <ResultCard
            icon="📅"
            title="다음 회의 안건"
            items={result.agenda}
            visible={!!agendaVisible}
          />
        </div>
      )}

      {/* 액션 버튼 */}
      {(status === 'complete' || isError) && (
        <div className="flex justify-end gap-2 pt-2">
          {status === 'complete' && (
            <ActionButton icon={<CopyIcon />} label={copied ? '복사됨!' : 'Markdown 복사'} onClick={handleCopyMarkdown} />
          )}
          <ActionButton icon={<RefreshIcon />} label="다시 생성" onClick={onReset} />
        </div>
      )}
    </div>
  );
}

function ActionButton({ icon, label, onClick }: { icon: React.ReactNode; label: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-1.5 border border-[#E6E8EB] bg-white text-[13px] font-bold text-[#374151] rounded-[8px] px-4 py-2.5"
      style={{ transition: 'background-color 150ms ease' }}
      onMouseEnter={e => { e.currentTarget.style.backgroundColor = '#F9FAFB'; }}
      onMouseLeave={e => { e.currentTarget.style.backgroundColor = '#FFFFFF'; }}
    >
      {icon}
      {label}
    </button>
  );
}

function CopyIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <rect x="4" y="4" width="9" height="9" rx="1.5" stroke="#374151" strokeWidth="1.4" />
      <path d="M3 10H2a1 1 0 01-1-1V2a1 1 0 011-1h7a1 1 0 011 1v1" stroke="#374151" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  );
}

function RefreshIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <path d="M12 7A5 5 0 112 7" stroke="#374151" strokeWidth="1.4" strokeLinecap="round" />
      <path d="M12 4V7H9" stroke="#374151" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function buildMarkdown(result: AnalysisResult): string {
  const lines: string[] = ['# MeetFlow 분석 결과\n'];
  if (result.summary) {
    lines.push('## 핵심 요약');
    result.summary.forEach(s => lines.push(`- ${s}`));
    lines.push('');
  }
  if (result.decisions) {
    lines.push('## 결정 사항');
    result.decisions.forEach(d => lines.push(`- ${d}`));
    lines.push('');
  }
  if (result.agenda) {
    lines.push('## 다음 회의 안건');
    result.agenda.forEach(a => lines.push(`- ${a}`));
    lines.push('');
  }
  return lines.join('\n');
}
