'use client';

import Header from '@/components/Header';
import LeftPanel from '@/components/LeftPanel';
import RightPanel from '@/components/RightPanel';
import { useAnalyzeStream } from '@/hooks/useAnalyzeStream';

export default function Home() {
  const { status, nodes, result, startAnalysis, reset, error } = useAnalyzeStream();

  return (
    <div className="flex flex-col min-h-screen bg-[#F8FAFC]">
      <Header />

      <main className="flex-1 flex p-6 gap-6 overflow-hidden">
        {/* 좌측 패널 40% */}
        <div className="w-[40%] shrink-0 flex flex-col">
          <LeftPanel
            onStart={startAnalysis}
            onReset={reset}
            isStreaming={status === 'streaming'}
          />
        </div>

        {/* 우측 패널 60% */}
        <div className="flex-1 flex flex-col min-h-0">
          <RightPanel
            status={status}
            nodes={nodes}
            result={result}
            error={error}
            onReset={reset}
          />
        </div>
      </main>
    </div>
  );
}
