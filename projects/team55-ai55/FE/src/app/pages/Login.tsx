import { useState } from "react";
import { useNavigate } from "react-router";
import { useAppStore } from "../store";
import { LayoutDashboard } from "lucide-react";

export default function Login() {
  const [name, setName] = useState("");
  const { login } = useAppStore();
  const navigate = useNavigate();

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    if (name.trim()) {
      login(name);
      navigate("/dashboard");
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#f2f4f6] p-4">
      <div className="w-full max-w-sm rounded-[24px] bg-white p-10 shadow-[0px_2px_30px_rgba(0,27,55,0.1)]">
        <div className="mb-8 flex flex-col items-center gap-3 text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-full bg-[#e8f3ff]">
            <LayoutDashboard className="h-7 w-7 text-[#3182f6]" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-[#212529]">PM Agent</h1>
            <p className="mt-1 text-[15px] text-[#4e5968]">
              팀의 일정을 AI가 똑똑하게 관리합니다
            </p>
          </div>
        </div>

        <form onSubmit={handleLogin} className="space-y-4">
          <div className="space-y-1.5">
            <label htmlFor="name" className="block text-[15px] font-semibold text-[#212529]">
              이름
            </label>
            <input
              id="name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="PM 이름을 입력하세요"
              className="w-full rounded-[7px] border border-[rgba(0,27,55,0.1)] bg-white px-3 py-[11px] text-[16px] text-[#212529] placeholder:text-[#b0b8c1] outline-none transition-shadow focus:border-[#3182f6] focus:ring-2 focus:ring-[#3182f6]/20"
              required
            />
          </div>
          <button
            type="submit"
            className="mt-2 w-full rounded-[7px] bg-[#3182f6] px-4 py-[11px] text-[15px] font-semibold text-[#f9fafb] transition-colors hover:bg-[#2272eb] focus:outline-none focus:ring-2 focus:ring-[#3182f6]/40 disabled:opacity-50"
          >
            로그인
          </button>
        </form>
      </div>
    </div>
  );
}
