"use client";

import { createContext, useCallback, useContext, useMemo, useState } from "react";
import type { ReactNode } from "react";
import type { ThreadMessage } from "@/lib/knowledgeChat";

type ChatMessagesContextValue = {
  messages: ThreadMessage[];
  appendMessage: (message: ThreadMessage) => void;
  replaceMessages: (messages: ThreadMessage[]) => void;
};

const ChatMessagesContext = createContext<ChatMessagesContextValue | null>(null);

type ProviderProps = {
  initialMessages?: ThreadMessage[];
  children: ReactNode;
};

export function ChatMessagesProvider({
  initialMessages = [],
  children,
}: ProviderProps) {
  const [messages, setMessages] = useState<ThreadMessage[]>(initialMessages);

  const appendMessage = useCallback((message: ThreadMessage) => {
    setMessages((prev) => [...prev, message]);
  }, []);

  const replaceMessages = useCallback((next: ThreadMessage[]) => {
    setMessages(next);
  }, []);

  const value = useMemo(
    () => ({ messages, appendMessage, replaceMessages }),
    [messages, appendMessage, replaceMessages],
  );

  return (
    <ChatMessagesContext.Provider value={value}>
      {children}
    </ChatMessagesContext.Provider>
  );
}

export function useChatMessages(): ChatMessagesContextValue | null {
  return useContext(ChatMessagesContext);
}
