import { ConversationFlow } from "@/components/screens/ConversationFlow";

export default async function ConversationPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <ConversationFlow conversationId={id} />;
}
