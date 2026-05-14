'use client';

// ─── 메인 페이지 ───
// 앱의 유일한 화면. 세로로 꽉 채우는 채팅 레이아웃.
// Header(로고) + MessageList(대화 목록) + ChatInput(입력창) 세 블록으로 구성.
// useTypewriter는 한 글자씩 타이핑 효과를 주는 훅 — 여기서 한 번만 실행하면 된다.

import { Header } from '@/components/header';
import { MessageList } from '@/components/chat/message-list';
import { ChatInput } from '@/components/chat/chat-input';
import { useChatStore } from '@/lib/store/chat-store';
import { useTypewriter } from '@/lib/hooks/use-typewriter';

export default function Home() {
  useTypewriter(); // AI 응답을 한 글자씩 출력하는 타이핑 효과

  const messages = useChatStore((s) => s.messages);
  const isTyping = useChatStore((s) => s.isTyping);
  const currentTypingId = useChatStore((s) => s.currentTypingId);

  return (
    // max-w-3xl: 너무 넓으면 가독성이 떨어져서 가운데 정렬로 고정 너비 유지
    <main className="mx-auto flex h-[100dvh] w-full max-w-3xl flex-col px-4 sm:px-6 lg:px-8">
      <Header />
      <MessageList
        messages={messages}
        isTyping={isTyping}
        currentTypingId={currentTypingId}
      />
      <ChatInput />
    </main>
  );
}
