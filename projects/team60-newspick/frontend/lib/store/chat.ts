import { create } from "zustand";
import {
  startChatStream,
  type ChatArticleSummary,
  type EventSourceLike,
} from "../../components/chat/chat-stream";

export type ChatMessage = {
  articles?: ChatArticleSummary[];
  id: string;
  role: "user" | "assistant";
  text: string;
  status?: "done" | "pending" | "streaming";
};

type ChatState = {
  draft: string;
  errorMessage: string | null;
  isPending: boolean;
  threadMessages: ChatMessage[];
};

type ChatActions = {
  reset: () => void;
  setDraft: (draft: string) => void;
  submit: (streamFactory?: (url: string) => EventSourceLike) => void;
};

const initialState: ChatState = {
  draft: "",
  errorMessage: null,
  isPending: false,
  threadMessages: [],
};

let activeStream: { close: () => void } | null = null;

export const useChatStore = create<ChatState & ChatActions>((set, get) => ({
  ...initialState,
  reset: () => {
    activeStream?.close();
    activeStream = null;
    set({ ...initialState });
  },
  setDraft: (draft) => set({ draft }),
  submit: (streamFactory) => {
    const state = get();
    const message = state.draft.trim();
    if (!message || state.isPending) {
      return;
    }

    const baseIndex = state.threadMessages.length;
    const assistantId = `assistant-${baseIndex + 2}`;

    set({
      draft: "",
      errorMessage: null,
      isPending: true,
      threadMessages: [
        ...state.threadMessages,
        { id: `user-${baseIndex + 1}`, role: "user", text: message },
        { id: assistantId, role: "assistant", status: "pending", text: "" },
      ],
    });

    activeStream = startChatStream({
      eventSourceFactory: streamFactory,
      message,
      onDone: (articles) => {
        activeStream = null;
        set((current) => ({
          isPending: false,
          threadMessages: current.threadMessages.map((item) =>
            item.id === assistantId ? { ...item, articles, status: "done" as const } : item,
          ),
        }));
      },
      onError: (errorMessage) => {
        activeStream = null;
        set((current) => ({
          errorMessage,
          isPending: false,
          threadMessages: current.threadMessages.filter((item) => item.id !== assistantId),
        }));
      },
      onToken: (text) => {
        set((current) => ({
          threadMessages: current.threadMessages.map((item) =>
            item.id === assistantId ? { ...item, status: "streaming" as const, text } : item,
          ),
        }));
      },
    });
  },
}));
