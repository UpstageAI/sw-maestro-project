import { BottomNav } from "../../../components/bottom-nav";
import { ChatShell } from "../../../components/chat/chat-shell";
import { buildChatSuggestions } from "../../../components/chat/suggestions";
import { PhoneFrame } from "../../../components/phone-frame";

const defaultSuggestions = buildChatSuggestions({
  category: "테크",
  page: "feed",
  topKeyword: "AI",
});

export default function ChatPage() {
  return (
    <main className="flex min-h-dvh items-center justify-center bg-bg px-5 py-6 text-ink">
      <PhoneFrame contentClassName="bg-bg">
        <div data-testid="chat-page" className="page-enter-chat min-h-0 flex-1">
          <ChatShell suggestions={defaultSuggestions} />
        </div>
        <BottomNav active="chat" />
      </PhoneFrame>
    </main>
  );
}
