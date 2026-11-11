import React from "react";
import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { useAuthStore } from "@/stores/authStore";
import { User as UserIcon } from "lucide-react";

export const AppShell: React.FC = () => {
  const { user } = useAuthStore();

  return (
    <div className="flex h-screen bg-slate-50 text-slate-900 font-sans antialiased overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0 h-full overflow-hidden">
        {/* Top Header */}
        <header className="h-16 bg-white border-b border-slate-200 px-8 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <h1 className="text-lg font-semibold text-slate-800">
              Enterprise Invoice Intelligence
            </h1>
            <span className="text-xs bg-blue-100 text-blue-700 font-medium px-2.5 py-0.5 rounded-full">
              Production AI
            </span>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2.5 text-sm text-slate-600 bg-slate-100/70 py-1.5 px-3 rounded-full border border-slate-200/60">
              <div className="w-6 h-6 rounded-full bg-blue-600 text-white flex items-center justify-center text-xs font-bold">
                {user?.full_name ? user.full_name[0].toUpperCase() : <UserIcon className="w-3.5 h-3.5" />}
              </div>
              <span className="font-medium text-slate-800">{user?.full_name || user?.email}</span>
            </div>
          </div>
        </header>

        {/* Main Content Area */}
        <main className="flex-1 overflow-y-auto p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
