import { redirect } from "next/navigation";

// /practice deprecated — chat is the unified experience now.
export default function PracticeRedirect() {
  redirect("/chat");
}
