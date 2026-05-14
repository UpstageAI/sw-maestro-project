'use client';

import type { AnalysisNode } from '@/types/analysis';

const NODE_ICONS: Record<string, string> = {
  input:    '📥',
  summary:  '📋',
  decision: '✅',
  agenda:   '📅',
};

interface ProgressBarProps {
  nodes: AnalysisNode[];
}

export default function ProgressBar({ nodes }: ProgressBarProps) {
  return (
    <div className="flex items-center gap-0">
      {nodes.map((node, i) => (
        <div key={node.id} className="flex items-center flex-1 last:flex-none">
          <div className="flex flex-col items-center gap-1.5">
            <NodeCircle node={node} />
            <span
              className="text-[13px] whitespace-nowrap transition-colors duration-300"
              style={{ color: node.status === 'done' ? '#2563EB' : '#6B7280' }}
            >
              {node.label}
            </span>
          </div>

          {i < nodes.length - 1 && (
            <div
              className="flex-1 h-0.5 mx-2 mb-5 transition-colors duration-300"
              style={{
                backgroundColor:
                  nodes[i + 1].status !== 'pending' || node.status === 'done'
                    ? '#2563EB'
                    : '#E5E7EB',
              }}
            />
          )}
        </div>
      ))}
    </div>
  );
}

function NodeCircle({ node }: { node: AnalysisNode }) {
  const { status } = node;

  const baseStyle: React.CSSProperties = {
    width: 40,
    height: 40,
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: 18,
    transition: 'all 300ms ease',
    flexShrink: 0,
  };

  const variantStyle: React.CSSProperties =
    status === 'done'
      ? { background: '#2563EB', border: 'none' }
      : status === 'active'
      ? { background: '#EFF6FF', border: '2px solid #2563EB' }
      : { background: '#F3F4F6', border: '2px solid #E5E7EB' };

  return (
    <div
      style={{ ...baseStyle, ...variantStyle }}
      className={status === 'active' ? 'animate-pulse' : undefined}
    >
      {status === 'done' ? (
        <CheckIcon />
      ) : (
        <span style={{ filter: status === 'pending' ? 'grayscale(1) opacity(0.4)' : 'none' }}>
          {NODE_ICONS[node.id]}
        </span>
      )}
    </div>
  );
}

function CheckIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
      <path d="M3.5 9.5L7 13L14.5 5.5" stroke="white" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
