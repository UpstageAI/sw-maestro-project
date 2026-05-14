'use client';

import { create } from 'zustand';
import type { ChatMessage } from '@/lib/types';
import { sendMessage as apiSendMessage } from '@/lib/api/chat';

function uuid(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') return crypto.randomUUID();
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16);
  });
}

// 인메모리 상태만 사용 — localStorage/sessionStorage 미사용 (UI_BRIEF 8절).
// 타이핑 중인 메시지의 전체 텍스트는 ChatMessage 타입을 더럽히지 않도록
// 별도 맵(`fullContents`)에 보관하고, hook이 한 글자씩 message.content에 채워 넣는다.

type ChatState = {
  userId: string;
  messages: ChatMessage[];
  isTyping: boolean;
  currentTypingId: string | null;
  attachment: File | null;
  fullContents: Record<string, string>;
  completedMissionIds: Set<string>; // 대화로 완료된 미션 id 목록 → MissionCard에서 참조

  attachFile: (file: File | null) => void;
  sendMessage: (text: string) => Promise<void>;
  appendChar: (id: string, char: string) => void;
  finishTyping: (id: string) => void;
  reset: () => void;
};

const initialState = {
  userId: uuid(),
  messages: [] as ChatMessage[],
  isTyping: false,
  currentTypingId: null as string | null,
  attachment: null as File | null,
  fullContents: {} as Record<string, string>,
  completedMissionIds: new Set<string>(),
};

export const useChatStore = create<ChatState>((set, get) => ({
  ...initialState,

  attachFile: (file) => set({ attachment: file }),

  appendChar: (id, char) =>
    set((s) => ({
      messages: s.messages.map((m) =>
        m.id === id ? { ...m, content: m.content + char } : m,
      ),
    })),

  finishTyping: (id) =>
    set((s) => {
      if (s.currentTypingId !== id) return s;
      // 종료된 메시지의 전체 텍스트 캐시를 메모리에서 제거.
      const nextFull: Record<string, string> = { ...s.fullContents };
      delete nextFull[id];
      return {
        ...s,
        currentTypingId: null,
        isTyping: false,
        fullContents: nextFull,
      };
    }),

  sendMessage: async (text) => {
    const { isTyping, attachment } = get();
    // 중복 전송 가드: 응답 대기/타이핑 중이면 무시.
    if (isTyping) return;
    const trimmed = text.trim();
    // 빈 텍스트 + 첨부 없음이면 no-op.
    if (!trimmed && !attachment) return;

    const userMsg: ChatMessage = {
      id: uuid(),
      role: 'user',
      content: text,
      createdAt: Date.now(),
      attachment: attachment
        ? { name: attachment.name, size: attachment.size }
        : undefined,
    };

    // 첨부는 user 메시지에 메타로만 보존되고 store의 attachment는 비운다(연속 전송 방지).
    const sentAttachment = attachment;
    set((s) => ({
      messages: [...s.messages, userMsg],
      isTyping: true,
      attachment: null,
    }));

    try {
      const reply = await apiSendMessage({
        message: text,
        userId: get().userId,
        attachment: sentAttachment ?? undefined,
      });

      // 빈 content의 ai 메시지를 push하고, 전체 텍스트는 fullContents에 보관.
      // typewriter hook이 currentTypingId를 보고 한 글자씩 content를 채워 나간다.
      const aiPlaceholder: ChatMessage = { ...reply, content: '' };
      const nextCompleted = new Set(get().completedMissionIds);
      if (reply.completedMissionId) nextCompleted.add(reply.completedMissionId);
      set((s) => ({
        messages: [...s.messages, aiPlaceholder],
        currentTypingId: aiPlaceholder.id,
        fullContents: { ...s.fullContents, [aiPlaceholder.id]: reply.content },
        completedMissionIds: nextCompleted,
      }));
    } catch {
      // API 실패 시 시스템 메시지로 안내하고 인디케이터 복구.
      const errMsg: ChatMessage = {
        id: uuid(),
        role: 'system',
        content: '응답을 받지 못했어요. 잠시 후 다시 시도해주세요.',
        createdAt: Date.now(),
      };
      set((s) => ({
        messages: [...s.messages, errMsg],
        isTyping: false,
        currentTypingId: null,
      }));
    }
  },

  reset: () => set({ ...initialState, userId: uuid() }),
}));
