import React from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { dashboardApi } from "@/api/dashboard";
import { UploadZone } from "@/components/invoice/UploadZone";
import {
  FileText,
  CheckCircle2,
  Clock,
  AlertTriangle,
  IndianRupee,
  ArrowUpRight,
  Activity,
  ChevronRight,
  TrendingUp,
} from "lucide-react";
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
} from "recharts";

const STATUS_COLOR_MAP: Record<string, string> = {
  APPROVED: "#10b981",
  REVIEW_REQUIRED: "#f59e0b",
  PROCESSING: "#3b82f6",
  QUEUED: "#6366f1",
  UPLOADED: "#94a3b8",
  FAILED: "#ef4444",
  REJECTED: "#64748b",
};

export const DashboardPage: React.FC = () => {
  const { data: stats, isLoading: statsLoading, refetch: refetchStats } = useQuery({
    queryKey: ["dashboard-stats"],
    queryFn: dashboardApi.getStats,
    refetchInterval: 5000,
  });

  const { data: recentActivity, isLoading: activityLoading } = useQuery({
    queryKey: ["dashboard-activity"],
    queryFn: dashboardApi.getRecentActivity,
    refetchInterval: 5000,
  });

  const formatCurrency = (val: number = 0) => {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    }).format(val);
  };

  const chartData = (stats?.status_distribution || []).map((item) => ({
    name: item.name.replace("_", " "),
    value: item.value,
    color: item.color || STATUS_COLOR_MAP[item.name] || "#94a3b8",
  }));

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Top Banner / Hero */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-slate-900">
            Financial Document Overview
          </h2>
          <p className="text-sm text-slate-500 mt-1">
            Real-time pipeline metrics, automated invoice extraction, and human validation stream.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link
            to="/review"
            className="inline-flex items-center gap-2 px-4 py-2 bg-amber-500 hover:bg-amber-600 text-white rounded-lg text-sm font-medium shadow-sm transition-all"
          >
            <Clock className="w-4 h-4" />
            Review Queue
            {stats && stats.pending_reviews > 0 && (
              <span className="bg-amber-700/50 text-white text-xs px-2 py-0.5 rounded-full font-bold ml-1">
                {stats.pending_reviews}
              </span>
            )}
          </Link>
          <Link
            to="/invoices"
            className="inline-flex items-center gap-2 px-4 py-2 bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 rounded-lg text-sm font-medium shadow-sm transition-all"
          >
            All Invoices
            <ArrowUpRight className="w-4 h-4" />
          </Link>
        </div>
      </div>

      {/* 5 KPI Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {/* Total Invoices */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 mb-3">
            <span className="text-xs font-semibold uppercase tracking-wider">Total Processed</span>
            <div className="p-2 bg-slate-100 rounded-lg text-slate-600">
              <FileText className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-slate-900">
            {statsLoading ? "—" : stats?.total_invoices ?? 0}
          </div>
          <div className="text-xs text-slate-400 mt-1 flex items-center gap-1">
            <Activity className="w-3 h-3 text-blue-500" /> All-time ingested
          </div>
        </div>

        {/* Approved */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 mb-3">
            <span className="text-xs font-semibold uppercase tracking-wider">Approved</span>
            <div className="p-2 bg-emerald-50 rounded-lg text-emerald-600">
              <CheckCircle2 className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-emerald-600">
            {statsLoading ? "—" : stats?.approved_invoices ?? 0}
          </div>
          <div className="text-xs text-slate-400 mt-1">Verified & finalized</div>
        </div>

        {/* Pending Review */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 mb-3">
            <span className="text-xs font-semibold uppercase tracking-wider">Pending Review</span>
            <div className="p-2 bg-amber-50 rounded-lg text-amber-600">
              <Clock className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-amber-600">
            {statsLoading ? "—" : stats?.pending_reviews ?? 0}
          </div>
          <div className="text-xs text-slate-400 mt-1">Requires human signoff</div>
        </div>

        {/* Failed */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 mb-3">
            <span className="text-xs font-semibold uppercase tracking-wider">Failed / Rejected</span>
            <div className="p-2 bg-rose-50 rounded-lg text-rose-600">
              <AlertTriangle className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-rose-600">
            {statsLoading ? "—" : stats?.failed_jobs ?? 0}
          </div>
          <div className="text-xs text-slate-400 mt-1">Extraction or policy failure</div>
        </div>

        {/* Approved Financial Value */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 mb-3">
            <span className="text-xs font-semibold uppercase tracking-wider">Approved Value</span>
            <div className="p-2 bg-blue-50 rounded-lg text-blue-600">
              <IndianRupee className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-slate-900 truncate" title={formatCurrency(stats?.total_approved_value)}>
            {statsLoading ? "—" : formatCurrency(stats?.total_approved_value)}
          </div>
          <div className="text-xs text-slate-400 mt-1 flex items-center gap-1">
            <TrendingUp className="w-3 h-3 text-emerald-500" /> Total authorized
          </div>
        </div>
      </div>

      {/* Main Grid: Upload Zone + Status Analytics */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Upload Card (2 Cols) */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 p-6 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-base font-semibold text-slate-900">
                  Ingest Financial Document
                </h3>
                <p className="text-xs text-slate-500">
                  Upload PDF invoices (up to 10MB, max 5 pages). Pipeline automatically performs
                  text extraction, Gemini structured analysis, arithmetic validation, and risk routing.
                </p>
              </div>
            </div>
            <UploadZone onUploadSuccess={() => refetchStats()} />
          </div>
        </div>

        {/* Recharts Pipeline Distribution (1 Col) */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm flex flex-col">
          <h3 className="text-base font-semibold text-slate-900 mb-1">
            Pipeline Distribution
          </h3>
          <p className="text-xs text-slate-500 mb-4">
            Breakdown across processing states
          </p>

          <div className="flex-1 min-h-[240px] flex items-center justify-center">
            {chartData.length === 0 || chartData.every((d) => d.value === 0) ? (
              <div className="text-center text-slate-400 text-xs py-8">
                No invoices processed yet
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={230}>
                <PieChart>
                  <Pie
                    data={chartData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    innerRadius={55}
                    outerRadius={80}
                    paddingAngle={3}
                  >
                    {chartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#0f172a",
                      color: "#fff",
                      borderRadius: "8px",
                      fontSize: "12px",
                      border: "none",
                    }}
                  />
                  <Legend
                    verticalAlign="bottom"
                    iconSize={8}
                    wrapperStyle={{ fontSize: "11px", paddingTop: "10px" }}
                  />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>

      {/* Recent Activity Timeline Feed */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-slate-500" />
            <h3 className="text-base font-semibold text-slate-900">
              Recent System & Workflow Audit Stream
            </h3>
          </div>
          <Link
            to="/invoices"
            className="text-xs font-medium text-blue-600 hover:text-blue-700 flex items-center gap-1"
          >
            View all invoices
            <ChevronRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {activityLoading ? (
          <div className="py-8 text-center text-slate-400 text-sm">
            Loading activity stream...
          </div>
        ) : !recentActivity || recentActivity.length === 0 ? (
          <div className="py-8 text-center text-slate-400 text-sm">
            No workflow events recorded yet. Upload an invoice to trigger agent execution.
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {recentActivity.slice(0, 8).map((act) => (
              <div
                key={act.id}
                className="py-3.5 flex items-center justify-between gap-4 hover:bg-slate-50/70 px-2 rounded-lg transition-colors"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-2 h-2 rounded-full bg-blue-500 shrink-0" />
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-slate-800 truncate">
                      {act.detail}
                    </p>
                    <div className="flex items-center gap-2 text-xs text-slate-400 mt-0.5">
                      <span className="font-mono bg-slate-100 px-1.5 py-0.5 rounded text-[11px] text-slate-600">
                        {act.action}
                      </span>
                      <span>•</span>
                      <span>Invoice ID: {act.invoice_id.slice(-8)}</span>
                    </div>
                  </div>
                </div>
                <div className="text-xs text-slate-400 shrink-0">
                  {new Date(act.created_at).toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                    second: "2-digit",
                  })}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
