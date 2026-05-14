import { useState } from "react";
import { useNavigate } from "react-router";
import { useAppStore, Member, Milestone, mintId } from "../store";
import { ChevronRight, ArrowLeft, Plus, X, Bot } from "lucide-react";
import { approveMilestones, createProject, suggestMilestones, userFacingApiError } from "../apiClient";

const STEPS = ["프로젝트 정보", "팀원 설정", "마일스톤 확인"] as const;

export default function NewProject() {
  const navigate = useNavigate();
  const { addProject } = useAppStore();
  const [step, setStep] = useState(1);
  const [projectId, setProjectId] = useState(() => mintId("proj"));
  const today = new Date().toISOString().split("T")[0];
  const defaultEnd = new Date();
  defaultEnd.setDate(defaultEnd.getDate() + 28);

  // Step 1: Info
  const [name, setName] = useState("");
  const [goal, setGoal] = useState("");
  const [startsAt, setStartsAt] = useState(today);
  const [endsAt, setEndsAt] = useState(defaultEnd.toISOString().split("T")[0]);
  const [baseHours, setBaseHours] = useState(40);
  const [defaultWorkStart, setDefaultWorkStart] = useState("09:00");
  const [defaultWorkEnd, setDefaultWorkEnd] = useState("18:00");
  const [weekendEnabled, setWeekendEnabled] = useState(false);
  const [weekendWorkStart, setWeekendWorkStart] = useState("10:00");
  const [weekendWorkEnd, setWeekendWorkEnd] = useState("16:00");
  const [apiError, setApiError] = useState("");

  // Step 2: Members
  const [members, setMembers] = useState<Member[]>([]);
  const [newMemberName, setNewMemberName] = useState("");
  const [newMemberRole, setNewMemberRole] = useState("Developer");
  const [newMemberHours, setNewMemberHours] = useState(40);
  const [newMemberWorkStart, setNewMemberWorkStart] = useState("09:00");
  const [newMemberWorkEnd, setNewMemberWorkEnd] = useState("18:00");

  // Step 3: Milestones
  const [isAgentLoading, setIsAgentLoading] = useState(false);
  const [milestones, setMilestones] = useState<Milestone[]>([]);

  const handleAddMember = () => {
    if (newMemberName.trim()) {
      setMembers([
        ...members,
        {
          id: mintId("mem"),
          name: newMemberName,
          role: newMemberRole,
          availableHours: newMemberHours,
          workStart: newMemberWorkStart,
          workEnd: newMemberWorkEnd,
        },
      ]);
      setNewMemberName("");
    }
  };

  const handleRemoveMember = (id: string) => {
    setMembers(members.filter((m) => m.id !== id));
  };

  const generateMilestones = async () => {
    setIsAgentLoading(true);
    setApiError("");
    let resolvedProjectId = projectId;
    const draftProject = {
      id: projectId,
      name,
      goal,
      startsAt,
      endsAt,
      baseHours,
      defaultWorkStart,
      defaultWorkEnd,
      weekendEnabled,
      weekendWorkStart,
      weekendWorkEnd,
      members,
      milestones: [],
      tasks: [],
      events: [],
    };
    try {
      resolvedProjectId = await createProject(draftProject);
      setProjectId(resolvedProjectId);
      setMilestones(await suggestMilestones({ ...draftProject, id: resolvedProjectId }));
      setStep(3);
    } catch (error) {
      setApiError(userFacingApiError(error, "마일스톤 제안 요청이 실패했습니다."));
      setMilestones([]);
    } finally {
      setIsAgentLoading(false);
    }
  };

  const handleFinish = async () => {
    const localProject = {
      id: projectId,
      name,
      goal,
      startsAt,
      endsAt,
      baseHours,
      defaultWorkStart,
      defaultWorkEnd,
      weekendEnabled,
      weekendWorkStart,
      weekendWorkEnd,
      members,
      milestones: milestones
        .filter((milestone) => milestone.status !== "archived")
        .map((milestone) => ({ ...milestone, status: "approved" })),
      tasks: [],
      events: [],
    };
    try {
      const approvedMilestones = await approveMilestones({ ...localProject, milestones });
      addProject({ ...localProject, milestones: approvedMilestones });
      navigate("/dashboard");
    } catch (error) {
      setApiError(userFacingApiError(error, "마일스톤 승인 요청이 실패했습니다."));
    }
  };

  const inputClass =
    "w-full rounded-[7px] border border-[rgba(0,27,55,0.1)] bg-white px-3 py-[10px] text-[16px] text-[#212529] placeholder:text-[#b0b8c1] outline-none focus:border-[#3182f6] focus:ring-2 focus:ring-[#3182f6]/20 transition-shadow";
  const inputSmClass =
    "w-full rounded-[7px] border border-[rgba(0,27,55,0.1)] bg-white px-2 py-1.5 text-sm text-[#212529] placeholder:text-[#b0b8c1] outline-none focus:border-[#3182f6] focus:ring-1 focus:ring-[#3182f6]/20";
  const labelClass = "mb-1.5 block text-[15px] font-semibold text-[#212529]";
  const labelSmClass = "mb-1 block text-xs font-semibold text-[#4e5968]";

  return (
    <div className="mx-auto max-w-3xl p-6 py-12">
      {/* Navigation */}
      <div className="mb-8 flex items-center justify-between">
        <button
          onClick={() => (step > 1 ? setStep(step - 1) : navigate(-1))}
          className="flex items-center gap-1 text-sm font-semibold text-[#4e5968] hover:text-[#212529] transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          뒤로
        </button>

        {/* Step indicator */}
        <div className="flex items-center gap-2">
          {STEPS.map((label, idx) => {
            const stepNum = idx + 1;
            const isDone = step > stepNum;
            const isCurrent = step === stepNum;
            return (
              <div key={stepNum} className="flex items-center gap-2">
                <div className="flex items-center gap-1.5">
                  <div
                    className={`flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold transition-colors ${
                      isDone
                        ? "bg-[#3182f6] text-white"
                        : isCurrent
                          ? "bg-[#3182f6] text-white"
                          : "bg-[#d1d6db] text-[#6b7684]"
                    }`}
                  >
                    {isDone ? "✓" : stepNum}
                  </div>
                  <span
                    className={`hidden text-xs font-medium sm:block ${
                      isCurrent ? "text-[#212529]" : "text-[#6b7684]"
                    }`}
                  >
                    {label}
                  </span>
                </div>
                {idx < STEPS.length - 1 && (
                  <div className={`h-px w-8 ${step > stepNum ? "bg-[#3182f6]" : "bg-[#d1d6db]"}`} />
                )}
              </div>
            );
          })}
        </div>
      </div>

      <div className="rounded-[24px] bg-white p-8 shadow-[0px_2px_30px_rgba(0,27,55,0.1)]">
        {/* Step 1: Project Info */}
        {step === 1 && (
          <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4">
            <div>
              <h2 className="text-2xl font-bold text-[#212529]">프로젝트 기본 정보</h2>
              <p className="mt-1 text-[15px] text-[#4e5968]">
                AI Agent가 분석할 수 있도록 프로젝트의 목표를 명확히 적어주세요.
              </p>
            </div>
            <div className="space-y-4">
              <div>
                <label className={labelClass}>프로젝트 이름</label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="예: AI PM Assistant 웹 서비스"
                  className={inputClass}
                />
              </div>
              <div>
                <label className={labelClass}>프로젝트 목표 (Agent 프롬프트용)</label>
                <textarea
                  value={goal}
                  onChange={(e) => setGoal(e.target.value)}
                  placeholder="예: 4주 안에 MVP 런칭. 핵심 기능은 AI 일정 추천과 우선순위 분석."
                  rows={4}
                  className="w-full rounded-[7px] border border-[rgba(0,27,55,0.1)] bg-white px-3 py-[10px] text-[16px] text-[#212529] placeholder:text-[#b0b8c1] outline-none focus:border-[#3182f6] focus:ring-2 focus:ring-[#3182f6]/20 transition-shadow"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className={labelClass}>시작일</label>
                  <input type="date" value={startsAt} onChange={(e) => setStartsAt(e.target.value)} className={inputClass} />
                </div>
                <div>
                  <label className={labelClass}>종료일</label>
                  <input type="date" value={endsAt} onChange={(e) => setEndsAt(e.target.value)} className={inputClass} />
                </div>
              </div>
              <div>
                <label className={labelClass}>기본 주당 근무시간 (시간)</label>
                <input
                  type="number"
                  value={baseHours}
                  onChange={(e) => setBaseHours(Number(e.target.value))}
                  className={inputClass}
                />
              </div>
              <div className="rounded-[14px] border border-[rgba(0,27,55,0.08)] bg-[#f9fafb] p-4">
                <div className="mb-3 text-sm font-bold text-[#212529]">기본 근무가능시간</div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className={labelSmClass}>평일 시작</label>
                    <input type="time" value={defaultWorkStart} onChange={(e) => setDefaultWorkStart(e.target.value)} className={inputSmClass} />
                  </div>
                  <div>
                    <label className={labelSmClass}>평일 종료</label>
                    <input type="time" value={defaultWorkEnd} onChange={(e) => setDefaultWorkEnd(e.target.value)} className={inputSmClass} />
                  </div>
                </div>
                <label className="mt-3 flex cursor-pointer items-center gap-2 text-sm font-medium text-[#4e5968]">
                  <input
                    type="checkbox"
                    checked={weekendEnabled}
                    onChange={(e) => setWeekendEnabled(e.target.checked)}
                    className="h-4 w-4 rounded border-[#d1d6db] accent-[#3182f6]"
                  />
                  주말 근무 허용
                </label>
                {weekendEnabled && (
                  <div className="mt-3 grid grid-cols-2 gap-3">
                    <div>
                      <label className={labelSmClass}>주말 시작</label>
                      <input type="time" value={weekendWorkStart} onChange={(e) => setWeekendWorkStart(e.target.value)} className={inputSmClass} />
                    </div>
                    <div>
                      <label className={labelSmClass}>주말 종료</label>
                      <input type="time" value={weekendWorkEnd} onChange={(e) => setWeekendWorkEnd(e.target.value)} className={inputSmClass} />
                    </div>
                  </div>
                )}
              </div>
            </div>
            <div className="flex justify-end pt-2">
              <button
                onClick={() => setStep(2)}
                disabled={!name.trim() || !goal.trim()}
                className="flex items-center gap-1 rounded-[7px] bg-[#3182f6] px-5 py-[11px] text-[15px] font-semibold text-white hover:bg-[#2272eb] disabled:opacity-40 transition-colors"
              >
                다음 <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        )}

        {/* Step 2: Members */}
        {step === 2 && (
          <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4">
            <div>
              <h2 className="text-2xl font-bold text-[#212529]">팀원 및 가용 시간 설정</h2>
              <p className="mt-1 text-[15px] text-[#4e5968]">
                일정 할당을 위해 팀원별 주당 근무 가능 시간을 입력해주세요.
              </p>
            </div>

            <div className="rounded-[14px] border border-[rgba(0,27,55,0.08)] bg-[#f9fafb] p-4">
              <div className="grid grid-cols-6 gap-3 items-end">
                <div className="col-span-2 sm:col-span-1">
                  <label className={labelSmClass}>이름</label>
                  <input
                    type="text"
                    value={newMemberName}
                    onChange={(e) => setNewMemberName(e.target.value)}
                    className={inputSmClass}
                    placeholder="홍길동"
                  />
                </div>
                <div className="col-span-2 sm:col-span-1">
                  <label className={labelSmClass}>역할</label>
                  <input
                    type="text"
                    value={newMemberRole}
                    onChange={(e) => setNewMemberRole(e.target.value)}
                    className={inputSmClass}
                  />
                </div>
                <div className="col-span-2 sm:col-span-1">
                  <label className={labelSmClass}>주당 시간</label>
                  <input
                    type="number"
                    value={newMemberHours}
                    onChange={(e) => setNewMemberHours(Number(e.target.value))}
                    className={inputSmClass}
                  />
                </div>
                <div className="col-span-2 sm:col-span-1">
                  <label className={labelSmClass}>시작</label>
                  <input
                    type="time"
                    value={newMemberWorkStart}
                    onChange={(e) => setNewMemberWorkStart(e.target.value)}
                    className={inputSmClass}
                  />
                </div>
                <div className="col-span-2 sm:col-span-1">
                  <label className={labelSmClass}>종료</label>
                  <input
                    type="time"
                    value={newMemberWorkEnd}
                    onChange={(e) => setNewMemberWorkEnd(e.target.value)}
                    className={inputSmClass}
                  />
                </div>
                <div className="col-span-2 pb-[1px] sm:col-span-1">
                  <button
                    onClick={handleAddMember}
                    disabled={newMemberWorkEnd <= newMemberWorkStart}
                    className="flex w-full items-center justify-center gap-1 rounded-[7px] bg-[#191f28] px-3 py-1.5 text-sm font-semibold text-white hover:bg-[#4e5968] disabled:opacity-40 transition-colors"
                  >
                    <Plus className="h-4 w-4" /> 추가
                  </button>
                </div>
              </div>
            </div>

            <div className="space-y-2">
              {members.length === 0 ? (
                <div className="py-8 text-center text-[15px] text-[#6b7684]">
                  추가된 팀원이 없습니다.
                </div>
              ) : (
                members.map((member) => (
                  <div
                    key={member.id}
                    className="flex items-center justify-between rounded-[14px] border border-[rgba(0,27,55,0.08)] bg-white p-3"
                  >
                    <div>
                      <span className="font-semibold text-[#212529]">{member.name}</span>
                      <span className="ml-2 rounded-[19px] bg-[#e8f3ff] px-2.5 py-0.5 text-xs font-semibold text-[#1b64da]">
                        {member.role}
                      </span>
                    </div>
                    <div className="flex items-center gap-4 text-sm text-[#4e5968]">
                      <span>{member.availableHours}h / 주</span>
                      <span>{member.workStart}–{member.workEnd}</span>
                      <button
                        onClick={() => handleRemoveMember(member.id)}
                        className="text-[#f04452] hover:text-[#d22030] transition-colors"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>

            <div className="flex justify-between pt-2">
              <button
                onClick={() => setStep(1)}
                className="text-[15px] font-semibold text-[#4e5968] hover:text-[#212529] transition-colors"
              >
                이전
              </button>
              <button
                onClick={generateMilestones}
                disabled={members.length === 0 || isAgentLoading}
                className="flex items-center gap-2 rounded-[7px] bg-[#3182f6] px-5 py-[11px] text-[15px] font-semibold text-white hover:bg-[#2272eb] disabled:opacity-40 transition-colors"
              >
                {isAgentLoading ? (
                  <>
                    <Bot className="h-4 w-4 animate-bounce" />
                    Agent 분석 중...
                  </>
                ) : (
                  <>
                    <Bot className="h-4 w-4" />
                    마일스톤 제안 받기
                  </>
                )}
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Milestones */}
        {step === 3 && (
          <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4">
            <div className="flex items-start justify-between">
              <div>
                <h2 className="flex items-center gap-2 text-2xl font-bold text-[#212529]">
                  <Bot className="h-6 w-6 text-[#3182f6]" />
                  Agent 제안 마일스톤
                </h2>
                <p className="mt-1 text-[15px] text-[#4e5968]">
                  프로젝트 목표를 분석하여 도출한 마일스톤입니다. [G1 승인]
                </p>
              </div>
            </div>

            <div className="space-y-3">
              {apiError && (
                <div className="rounded-[14px] border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
                  {apiError}
                </div>
              )}
              {milestones.map((m, idx) => (
                <div
                  key={m.id}
                  className="grid gap-3 rounded-[14px] border border-[#e8f3ff] bg-[#f0f7ff] p-4 sm:grid-cols-[32px_1fr_150px_32px]"
                >
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-[#e8f3ff] text-xs font-bold text-[#3182f6]">
                    {idx + 1}
                  </div>
                  <input
                    value={m.title}
                    onChange={(event) =>
                      setMilestones((prev) =>
                        prev.map((item) => (item.id === m.id ? { ...item, title: event.target.value } : item)),
                      )
                    }
                    className="rounded-[7px] border border-[#e8f3ff] bg-white px-3 py-2 text-sm font-medium text-[#212529] outline-none focus:border-[#3182f6] focus:ring-1 focus:ring-[#3182f6]/20"
                    aria-label={`${idx + 1}번 마일스톤 이름`}
                  />
                  <input
                    type="date"
                    value={m.dueDate}
                    onChange={(event) =>
                      setMilestones((prev) =>
                        prev.map((item) => (item.id === m.id ? { ...item, dueDate: event.target.value } : item)),
                      )
                    }
                    className="rounded-[7px] border border-[#e8f3ff] bg-white px-3 py-2 text-sm text-[#212529] outline-none focus:border-[#3182f6] focus:ring-1 focus:ring-[#3182f6]/20"
                    aria-label={`${idx + 1}번 마일스톤 마감일`}
                  />
                  <input
                    type="checkbox"
                    checked={m.status !== "archived"}
                    onChange={(event) =>
                      setMilestones((prev) =>
                        prev.map((item) =>
                          item.id === m.id ? { ...item, status: event.target.checked ? "pending" : "archived" } : item,
                        ),
                      )
                    }
                    className="h-4 w-4 rounded border-[#d1d6db] accent-[#3182f6]"
                    aria-label={`${m.title} 채택 여부`}
                  />
                </div>
              ))}
            </div>

            <div className="flex justify-between pt-2">
              <button
                onClick={() => setStep(2)}
                className="text-[15px] font-semibold text-[#4e5968] hover:text-[#212529] transition-colors"
              >
                이전
              </button>
              <button
                onClick={handleFinish}
                disabled={milestones.length === 0 || milestones.every((milestone) => milestone.status === "archived")}
                className="flex items-center gap-2 rounded-[7px] bg-[#191f28] px-5 py-[11px] text-[15px] font-semibold text-white hover:bg-[#4e5968] disabled:opacity-40 transition-colors"
              >
                승인 및 프로젝트 생성
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
