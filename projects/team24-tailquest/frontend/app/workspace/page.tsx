import { redirect } from "next/navigation";

// /workspace deprecated — onboarding → /chat is the canonical flow.
// Kept as a redirect so any old links resolve gracefully.
export default function WorkspaceRedirect() {
  redirect("/onboarding");
}
