import React from "react";
import { NavLink, useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  FileSpreadsheet,
  CheckSquare,
  LogOut,
  Layers,
  Sparkles,
} from "lucide-react";
import { useAuthStore } from "@/stores/authStore";
import { useQuery } from "@tanstack/react-query";
import { dashboardApi } from "@/api/dashboard";

export const Sidebar: React.FC = () => {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();

  // Poll dashboard stats to show real-time pending review badge count
  const { data: stats } = useQuery({
    queryKey: ["dashboard-stats-nav"],
    queryFn: dashboardApi.getStats,
    refetchInterval: 5000,
  });

  const pendingReviewsCount = stats?.pending_reviews ?? 0;

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const navItems = [
    {
      label: "Dashboard",
      to: "/",
      icon: LayoutDashboard,
    },
    {
      label: "All Invoices",
      to: "/invoices",
      icon: FileSpreadsheet,
    },
    {
      label: "Review Queue",
      to: "/review",
      icon: CheckSquare,
      badge: pendingReviewsCount > 0 ? pendingReviewsCount : undefined,
    },
  ];

  return (
    <aside className="w-64 bg-white border-r border-slate-200 flex flex-col justify-between h-screen sticky top-0 shrink-0 select-none">
      <div>
        {/* Brand Header */}
        <div className="h-16 flex items-center gap-3 px-6 border-b border-slate-100">
          <div className="w-9 h-9 rounded-lg bg-blue-600 flex items-center justify-center text-white shadow-sm shadow-blue-500/20">
            <Layers className="w-5 h-5" />
          </div>
          <div>
            <span className="font-bold text-slate-900 tracking-tight text-base flex items-center gap-1.5">
              FinSight AI
              <Sparkles className="w-3.5 h-3.5 text-blue-500" />
            </span>
            <span className="text-[10px] uppercase font-semibold text-slate-400 tracking-wider block">
              Agentic Processing
            </span>
          </div>
        </div>

        {/* Navigation Menu */}
        <nav className="p-4 space-y-1.5">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/"}
                className={({ isActive }) =>
                  `flex items-center justify-between px-3.5 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? "bg-blue-50 text-blue-700 font-semibold"
                      : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                  }`
                }
              >
                <div className="flex items-center gap-3">
                  <Icon className="w-4 h-4" />
                  <span>{item.label}</span>
                </div>
                {item.badge !== undefined && (
                  <span className="bg-amber-100 text-amber-800 text-[11px] font-bold px-2 py-0.5 rounded-full border border-amber-200">
                    {item.badge}
                  </span>
                )}
              </NavLink>
            );
          })}
        </nav>
      </div>

      {/* User Footer */}
      <div className="p-4 border-t border-slate-100 bg-slate-50/50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5 overflow-hidden">
            <div className="w-8 h-8 rounded-full bg-blue-100 text-blue-700 font-bold flex items-center justify-center text-xs shrink-0">
              {user?.full_name?.charAt(0).toUpperCase() || user?.email.charAt(0).toUpperCase() || "U"}
            </div>
            <div className="truncate">
              <p className="text-xs font-semibold text-slate-900 truncate">
                {user?.full_name || "Finance User"}
              </p>
              <p className="text-[11px] text-slate-500 truncate">{user?.email}</p>
            </div>
          </div>

          <button
            onClick={handleLogout}
            title="Log out"
            className="p-1.5 rounded-md text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-colors"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </aside>
  );
};
