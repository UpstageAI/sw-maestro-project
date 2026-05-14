export default function Header() {
  return (
    <header className="h-14 bg-white border-b border-[#E6E8EB] flex items-center justify-between px-6 shrink-0">
      <span className="text-[18px] font-bold tracking-[-0.5px] text-[#111827]">
        MeetFlow
      </span>
      <span className="flex items-center gap-1.5 text-[13px] text-[#374151] border border-[#E6E8EB] rounded-full px-3 py-1.5">
        <span className="w-2 h-2 rounded-full bg-[#10B981] shrink-0" />
        LangGraph Workflow
      </span>
    </header>
  );
}
