"use client";

import { useState, useEffect, useRef, ChangeEvent, KeyboardEvent } from "react";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";
const CONVS_KEY = "hwp-conversations";
const ACTIVE_KEY = "hwp-active-conv";

interface Message {
  id: string;
  role: "user" | "assistant" | "system" | "info";
  content: string;
  fileReady?: boolean;
}

interface Conversation {
  id: string;
  title: string;
  createdAt: number;
}

function loadConversations(): Conversation[] {
  try {
    const raw = localStorage.getItem(CONVS_KEY);
    if (raw) return JSON.parse(raw) as Conversation[];
  } catch {}
  return [];
}

function saveConversations(convs: Conversation[]): void {
  localStorage.setItem(CONVS_KEY, JSON.stringify(convs));
}

function createNewConversation(): Conversation {
  return { id: crypto.randomUUID(), title: "새 대화", createdAt: Date.now() };
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [sessionId, setSessionId] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let convs = loadConversations();
    if (convs.length === 0) {
      const first = createNewConversation();
      convs = [first];
      saveConversations(convs);
      localStorage.setItem(ACTIVE_KEY, first.id);
    }
    const activeId = localStorage.getItem(ACTIVE_KEY) ?? convs[0].id;
    setConversations(convs);
    setSessionId(activeId);
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  async function handleSend() {
    const text = input.trim();
    if (!text || isLoading || !sessionId) return;

    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: text,
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsLoading(true);

    // 첫 메시지면 대화 제목 설정
    if (messages.length === 0) {
      const title = text.slice(0, 20);
      const updated = conversations.map((c) =>
        c.id === sessionId ? { ...c, title } : c
      );
      saveConversations(updated);
      setConversations(updated);
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 120_000);

    try {
      const res = await fetch(`${BACKEND_URL}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Session-ID": sessionId,
        },
        body: JSON.stringify({ message: text, session_id: sessionId }),
        signal: controller.signal,
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = (await res.json()) as {
        response: string;
        file_ready: boolean;
      };
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: data.response,
          fileReady: data.file_ready,
        },
      ]);
    } catch (err) {
      const isTimeout = err instanceof DOMException && err.name === "AbortError";
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "system",
          content: isTimeout
            ? "응답 시간이 초과되었습니다. 다시 시도해주세요."
            : "오류가 발생했습니다. 다시 시도해주세요.",
        },
      ]);
    } finally {
      clearTimeout(timeoutId);
      setIsLoading(false);
    }
  }

  async function handleFileUpload(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;

    if (!file.name.toLowerCase().endsWith(".hwpx")) {
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "system",
          content: "지원하지 않는 파일 형식입니다",
        },
      ]);
      return;
    }

    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await fetch(`${BACKEND_URL}/upload`, {
        method: "POST",
        headers: { "X-Session-ID": sessionId },
        body: formData,
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "info",
          content: `${file.name} 업로드 완료`,
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "system",
          content: "파일 업로드에 실패했습니다. 다시 시도해주세요.",
        },
      ]);
    } finally {
      setIsUploading(false);
    }
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void handleSend();
    }
  }

  function handleNewConversation() {
    const conv = createNewConversation();
    const updated = [conv, ...conversations];
    saveConversations(updated);
    localStorage.setItem(ACTIVE_KEY, conv.id);
    setConversations(updated);
    setSessionId(conv.id);
    setMessages([]);
  }

  async function handleSelectConversation(conv: Conversation) {
    if (conv.id === sessionId) return;
    localStorage.setItem(ACTIVE_KEY, conv.id);
    setSessionId(conv.id);

    const res = await fetch(`${BACKEND_URL}/history`, {
      headers: { "X-Session-ID": conv.id },
    });
    if (res.ok) {
      const data = (await res.json()) as {
        history: Array<{ role: string; content: string }>;
      };
      const restored: Message[] = data.history.map((m) => ({
        id: crypto.randomUUID(),
        role: m.role as Message["role"],
        content: m.content,
      }));
      setMessages(restored);
    } else {
      setMessages([]);
    }
  }

  async function handleDeleteConversation(
    e: React.MouseEvent,
    conv: Conversation,
  ) {
    e.stopPropagation();

    if (!window.confirm(`'${conv.title}' 대화를 삭제할까요?`)) return;

    await fetch(`${BACKEND_URL}/sessions/${conv.id}`, { method: "DELETE" });

    const updated = conversations.filter((c) => c.id !== conv.id);
    saveConversations(updated);
    setConversations(updated);

    if (conv.id === sessionId) {
      if (updated.length > 0) {
        setSessionId("");  // handleSelectConversation의 early-return 회피
        await handleSelectConversation(updated[0]);
      } else {
        handleNewConversation();
      }
    }
  }

  async function handleDownload() {
    const res = await fetch(`${BACKEND_URL}/download`, {
      headers: { "X-Session-ID": sessionId },
    });
    if (!res.ok) return;
    const blob = await res.blob();
    const contentDisposition = res.headers.get("content-disposition") ?? "";
    const match = /filename="?([^"]+)"?/.exec(contentDisposition);
    const filename = match?.[1] ?? "edited.hwpx";
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-header">
          <button className="new-conv-btn" onClick={handleNewConversation}>
            + 새 대화
          </button>
        </div>
        <ul className="conv-list">
          {conversations.map((conv) => (
            <li
              key={conv.id}
              className={`conv-item ${conv.id === sessionId ? "active" : ""}`}
              onClick={() => void handleSelectConversation(conv)}
            >
              <div className="conv-info">
                <span className="conv-title">{conv.title}</span>
                <span className="conv-date">
                  {new Date(conv.createdAt).toLocaleDateString("ko-KR")}
                </span>
              </div>
              <button
                className="conv-delete-btn"
                onClick={(e) => void handleDeleteConversation(e, conv)}
                title="대화 삭제"
                aria-label="대화 삭제"
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      </aside>

      <main className="chat-page">
        <header className="chat-header">
          <h1>HWP Editor Chatbot</h1>
          <span className="session-badge">세션 {sessionId.slice(0, 8)}</span>
        </header>

        <div className="messages-area">
          {messages.length === 0 && (
            <div className="empty-state">한글 문서 편집 요청을 입력하세요</div>
          )}
          {messages.map((msg) => (
            <div key={msg.id} className={`bubble ${msg.role}`}>
              {msg.content}
              {msg.role === "assistant" && (
                <div className="download-row">
                  <button
                    className="download-btn"
                    onClick={() => void handleDownload()}
                    disabled={!msg.fileReady}
                    title={msg.fileReady ? "HWPX 파일 다운로드" : "파일이 아직 준비되지 않았습니다"}
                  >
                    HWPX 다운로드
                  </button>
                </div>
              )}
            </div>
          ))}
          {isLoading && (
            <div className="bubble assistant">
              <span className="spinner" aria-label="로딩 중" />
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        <div className="input-row">
          <input
            ref={fileInputRef}
            type="file"
            accept=".hwpx"
            style={{ display: "none" }}
            onChange={(e) => void handleFileUpload(e)}
          />
          <button
            className="attach-btn"
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading || isLoading || !sessionId}
            aria-label="파일 첨부"
            title="HWPX 파일 첨부"
          >
            📎
          </button>
          <textarea
            className="message-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="메시지를 입력하세요... (Enter: 전송, Shift+Enter: 줄바꿈)"
            disabled={isLoading}
            rows={3}
          />
          <button
            className="send-btn"
            onClick={() => void handleSend()}
            disabled={isLoading || !input.trim()}
            aria-label="전송"
          >
            전송
          </button>
        </div>
      </main>
    </div>
  );
}
