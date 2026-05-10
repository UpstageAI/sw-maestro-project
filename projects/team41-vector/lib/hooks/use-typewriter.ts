'use client';

import { useEffect, useRef } from 'react';
import { useChatStore } from '@/lib/store/chat-store';

// 글자당 ms. 24~32ms 권장. 너무 빠르면 효과가 없고, 너무 느리면 답답함.
const SPEED_MS = 28;

/**
 * 타이핑 흉내내기 effect.
 *
 * - store의 currentTypingId가 세팅되면 해당 메시지의 fullContent를 한 글자씩 appendChar로 추가.
 * - 끝까지 채우면 finishTyping 호출 → currentTypingId/isTyping/fullContents 정리.
 * - 컴포넌트 unmount 또는 currentTypingId 변경 시 setInterval cleanup.
 *
 * ChatPanel 등 채팅 화면 루트 컴포넌트에서 한 번만 호출하면 된다.
 */
export function useTypewriter(): void {
  const currentTypingId = useChatStore((s) => s.currentTypingId);
  const appendChar = useChatStore((s) => s.appendChar);
  const finishTyping = useChatStore((s) => s.finishTyping);

  // setInterval id 보관 — React 환경에서는 number(window) 타입.
  const intervalRef = useRef<number | null>(null);

  useEffect(() => {
    if (!currentTypingId) return;

    // 시작 시점에 store에서 풀 텍스트와 현재 진행 인덱스를 읽는다.
    // 이후 tick에서는 store 구독 없이 클로저 변수로 진행 → 리렌더 폭주 방지.
    const startState = useChatStore.getState();
    const full = startState.fullContents[currentTypingId];
    if (typeof full !== 'string') return;
    const startMsg = startState.messages.find((m) => m.id === currentTypingId);
    let i = startMsg ? startMsg.content.length : 0;

    intervalRef.current = window.setInterval(() => {
      if (i >= full.length) {
        if (intervalRef.current !== null) {
          window.clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
        finishTyping(currentTypingId);
        return;
      }
      appendChar(currentTypingId, full[i]);
      i += 1;
    }, SPEED_MS);

    return () => {
      if (intervalRef.current !== null) {
        window.clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [currentTypingId, appendChar, finishTyping]);
}
