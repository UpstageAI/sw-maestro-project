import { Logo } from "@/components/ui";

export const Footer = () => (
  <footer
    style={{
      borderTop: "1px solid var(--line)",
      padding: "32px 48px",
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
      color: "var(--ink-mute)",
      fontSize: 13,
      background: "white",
    }}
  >
    <Logo size={20} />
    <div>© 2026 twinmatch · Multi-Agent Dating Platform</div>
  </footer>
);
