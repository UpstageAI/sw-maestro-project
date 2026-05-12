// ─── 프론트 → 백엔드 채팅 API 래퍼 ───
// 컴포넌트가 직접 fetch를 쓰지 않고 이 함수만 호출하도록 추상화.
// 파일 첨부가 있으면 먼저 /api/upload로 CSV를 올리고, 그 다음 /api/chat으로 분석 요청.

import type { ChatMessage } from '@/lib/types';

export type SendMessageInput = {
  message: string;
  userId: string;
  attachment?: File; // CSV 파일 (있을 때만)
};

export async function sendMessage(input: SendMessageInput): Promise<ChatMessage> {
  // ── 파일 첨부가 있는 경우 ──
  // 1) /api/upload 로 CSV 업로드 → DB에 transactions 저장
  // 2) message='' 로 /api/chat 호출 → 자동 초기 분석 시작
  if (input.attachment) {
    const form = new FormData();
    form.append('file', input.attachment);
    form.append('userId', input.userId);

    const uploadRes = await fetch('/api/upload', { method: 'POST', body: form });
    if (!uploadRes.ok) {
      const err = await uploadRes.json().catch(() => ({ error: 'CSV 업로드에 실패했어요.' }));
      throw new Error(err.error);
    }

    // 업로드 완료 후 빈 메시지로 분석 요청 (route.ts에서 isInitialAnalysis=true 로 처리됨)
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: '', userId: input.userId }),
    });
    if (!res.ok) throw new Error('분석 요청에 실패했어요.');
    return res.json();
  }

  // ── 일반 텍스트 메시지 ──
  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: input.message, userId: input.userId }),
  });
  if (!res.ok) throw new Error('응답을 받지 못했어요.');
  return res.json();
}
