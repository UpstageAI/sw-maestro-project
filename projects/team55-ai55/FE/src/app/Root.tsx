import { Outlet } from "react-router";
import { AppProvider } from "./store";

export default function Root() {
  return (
    <AppProvider>
      <div className="min-h-screen bg-[#f2f4f6] text-[#212529] font-sans">
        <Outlet />
      </div>
    </AppProvider>
  );
}
