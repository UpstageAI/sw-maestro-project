import { redirect } from "next/navigation";

// /analysis deprecated — analysis is now inline in /chat (left column)
// and detailed in the right rail per turn.
export default function AnalysisRedirect() {
  redirect("/chat");
}
