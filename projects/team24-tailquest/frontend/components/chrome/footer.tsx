// Minimal Airbnb-style legal band — the 3-column link grid was removed
// per spec; the chat interface doesn't need marketing footer chrome.

import { Icon } from "@/components/chrome/icon";

export function Footer() {
  return (
    <footer className="bg-canvas border-t border-hairline w-full mt-auto">
      <div className="max-w-airbnb mx-auto px-xl py-md flex flex-col md:flex-row items-center justify-between gap-md">
        <p className="text-caption-sm text-muted">
          © 2026 TailQuest AI · 24조 ·{" "}
          <a href="#" className="hover:underline">개인정보처리방침</a> ·{" "}
          <a href="#" className="hover:underline">이용약관</a>
        </p>
        <div className="flex items-center gap-md text-caption-sm text-ink">
          <button
            type="button"
            className="flex items-center gap-1 hover:underline"
          >
            <Icon name="language" size={16} />
            한국어 (KR)
          </button>
        </div>
      </div>
    </footer>
  );
}
