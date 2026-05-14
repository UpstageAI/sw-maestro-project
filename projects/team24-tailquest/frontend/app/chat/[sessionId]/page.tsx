import { ChatShell } from "@/components/chat/chat-shell";

interface Props {
  params: { sessionId: string };
}

export default function SessionPage({ params }: Props) {
  return <ChatShell sessionId={params.sessionId} />;
}
