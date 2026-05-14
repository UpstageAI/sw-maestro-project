'use client';

// ─── MissionCard ───
// Coach가 미션을 제안하면 AI 메시지 아래에 이 카드가 표시된다.
//
// 상태 흐름:
//   pending → accepted (수락 버튼 클릭)
//           → rejected (거절 버튼 클릭)
//   accepted → completed (채팅으로 완료 보고 → complete_mission 툴 → store.completedMissionIds에 id 추가)
//
// 상태 변경은 PATCH /api/missions 로 DB에도 반영된다.
// 완료(completed)는 버튼이 아니라 store의 completedMissionIds Set으로 감지 → 폭죽 효과.

import { useState, useEffect, useRef } from 'react';
import confetti from 'canvas-confetti';
import { useChatStore } from '@/lib/store/chat-store';

type Props = {
  mission: { id: string; text: string; savingAmount: number };
};

// 미션 상태를 서버 DB에도 반영
async function updateMissionStatus(missionId: string, status: 'accepted' | 'rejected') {
  await fetch('/api/missions', {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ missionId, status }),
  });
}

export function MissionCard({ mission }: Props) {
  // 로컬 UI 상태 (수락/거절 버튼 즉시 반응용)
  const [status, setStatus] = useState<'pending' | 'accepted' | 'rejected'>('pending');

  // 폭죽 중복 방지 — 완료 전환 시 딱 한 번만 터뜨린다
  const firedRef = useRef(false);

  // store에서 완료된 미션 id 목록 확인 (Coach가 complete_mission 호출 시 추가됨)
  const isCompleted = useChatStore((s) => s.completedMissionIds.has(mission.id));

  // isCompleted가 false → true 로 바뀌는 순간 폭죽 실행
  useEffect(() => {
    if (!isCompleted || firedRef.current) return;
    firedRef.current = true;
    confetti({
      particleCount: 120,
      spread: 80,
      origin: { y: 0.6 },
      colors: ['#5b21b6', '#7c3aed', '#a78bfa', '#fbbf24', '#f472b6'],
    });
  }, [isCompleted]);

  const handleAction = (next: 'accepted' | 'rejected') => {
    setStatus(next);
    updateMissionStatus(mission.id, next); // DB 반영 (await 없이 fire-and-forget)
  };

  return (
    <div
      className={`my-2 rounded-xl border p-4 transition-opacity ${
        status === 'rejected' ? 'opacity-40' : ''
      }`}
      style={{
        borderColor: '#5b21b6',
        background: 'linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%)',
      }}
    >
      <p className="mb-1 text-xs font-semibold" style={{ color: '#5b21b6' }}>
        행동 미션
      </p>
      <p className="mb-2 text-sm leading-relaxed">{mission.text}</p>
      <p className="mb-3 text-xs text-gray-500">
        절약 예상: {mission.savingAmount.toLocaleString()}원
      </p>

      {/* 완료 상태: store.completedMissionIds 기준 */}
      {isCompleted ? (
        <p className="text-sm font-semibold" style={{ color: '#5b21b6' }}>
          🎉 완료!
        </p>
      ) : status === 'pending' ? (
        // 대기 상태: 수락·거절 버튼
        <div className="flex gap-2">
          <button
            onClick={() => handleAction('accepted')}
            className="rounded-lg px-4 py-1.5 text-sm font-medium text-white"
            style={{ backgroundColor: '#5b21b6' }}
          >
            수락
          </button>
          <button
            onClick={() => handleAction('rejected')}
            className="rounded-lg border px-4 py-1.5 text-sm font-medium text-gray-600"
          >
            거절
          </button>
        </div>
      ) : status === 'accepted' ? (
        // 수락 상태: 도전 중 텍스트만 표시
        <p className="text-sm font-semibold" style={{ color: '#5b21b6' }}>
          ✓ 도전 중!
        </p>
      ) : null /* 거절 상태: opacity 낮아지고 버튼 없음 */}
    </div>
  );
}
