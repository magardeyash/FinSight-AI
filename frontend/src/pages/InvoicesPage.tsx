import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { invoicesApi } from "@/api/invoices";
import { StatusBadge } from "@/components/invoice/StatusBadge";
import { RiskBadge } from "@/components/invoice/RiskBadge";
import {
  Search,
  Filter,
  RefreshCw,
  ExternalLink,
  RotateCcw,
  FileSpreadsheet,
  AlertCircle,
} from "lucide-react";

export const InvoicesPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [searchTerm, setSearchTerm] = useState<string>("");

  const {
    data,
    isLoading,
    isRefetching,
    refetch,
    error,
  } = useQuery({
    queryKey: ["invoices", page, pageSize, statusFilter, searchTerm],
    queryFn: () =>
      invoicesApi.list({
        page,
        page_size: pageSize,
        status: statusFilter || undefined,
        search: searchTerm || undefined,
      }),
    refetchInterval: (query) => {
      // Auto-poll every 4s if any invoices are currently in-flight
      const hasActive = query.state.data?.items.some((inv) =>
        ["UPLOADED", "QUEUED", "PROCESSING", "APPROVING"].includes(inv.status)
      );
      return hasActive ? 4000 : false;
    },
  });

  const retryMutation = useMutation({
    mutationFn: (id: string) => invoicesApi.retry(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["invoices"] });
    },
  });

  const formatCurrency = (amount?: number | null, currency: string = "INR") => {
    if (amount === undefined || amount === null) return "—";
    try {
      return new Intl.NumberFormat("en-IN", {
        style: "currency",
        currency: currency || "INR",
      }).format(amount);
    } catch {
      return `${currency} ${amount.toFixed(2)}`;
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-slate-900">
            Invoice Repository
          </h2>
          <p className="text-sm text-slate-500 mt-1">
            Browse, filter, and inspect structured financial documents processed by FinSight AI.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => refetch()}
            disabled={isRefetching}
            className="inline-flex items-center gap-2 px-3.5 py-2 bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 rounded-lg text-sm font-medium shadow-sm transition-all"
          >
            <RefreshCw className={`w-4 h-4 ${isRefetching ? "animate-spin text-blue-600" : ""}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm flex flex-col md:flex-row gap-4 justify-between items-center">
        <form onSubmit={handleSearchSubmit} className="relative w-full md:w-96">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search by invoice # or vendor name..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 focus:bg-white transition-all"
          />
        </form>

        <div className="flex items-center gap-3 w-full md:w-auto">
          <div className="flex items-center gap-2 text-sm text-slate-500 shrink-0">
            <Filter className="w-4 h-4" />
            <span className="text-xs font-semibold uppercase tracking-wider">Status:</span>
          </div>
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(1);
            }}
            className="bg-slate-50 border border-slate-200 text-slate-700 rounded-lg text-sm px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition-all"
          >
            <option value="">All Statuses</option>
            <option value="APPROVED">Approved</option>
            <option value="REVIEW_REQUIRED">Review Required</option>
            <option value="PROCESSING">Processing</option>
            <option value="QUEUED">Queued</option>
            <option value="UPLOADED">Uploaded</option>
            <option value="FAILED">Failed</option>
            <option value="REJECTED">Rejected</option>
          </select>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl flex items-center gap-3 text-sm text-rose-700">
          <AlertCircle className="w-5 h-5 shrink-0 text-rose-600" />
          <span>Failed to load invoices. Please verify the backend connection.</span>
        </div>
      )}

      {/* Invoices Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50/75 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                <th className="py-3 px-4">Invoice / Vendor</th>
                <th className="py-3 px-4">Source File</th>
                <th className="py-3 px-4">Grand Total</th>
                <th className="py-3 px-4">Risk Evaluation</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Uploaded At</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-sm text-slate-700">
              {isLoading ? (
                <tr>
                  <td colSpan={7} className="text-center py-12 text-slate-400">
                    <div className="flex flex-col items-center gap-2">
                      <RefreshCw className="w-5 h-5 animate-spin text-blue-500" />
                      <span>Loading invoices...</span>
                    </div>
                  </td>
                </tr>
              ) : !data || data.items.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center py-12 text-slate-400">
                    <div className="flex flex-col items-center gap-2">
                      <FileSpreadsheet className="w-8 h-8 text-slate-300" />
                      <span>No invoices found matching your criteria.</span>
                    </div>
                  </td>
                </tr>
              ) : (
                data.items.map((inv) => (
                  <tr
                    key={inv.id}
                    className="hover:bg-slate-50/80 transition-colors group"
                  >
                    <td className="py-3.5 px-4 font-medium text-slate-900">
                      <div className="flex flex-col">
                        <span className="font-semibold text-slate-800">
                          {inv.extracted?.invoice_number || (
                            <span className="italic text-slate-400">Not Extracted</span>
                          )}
                        </span>
                        <span className="text-xs text-slate-500">
                          {inv.extracted?.vendor_name || "Unknown Vendor"}
                        </span>
                      </div>
                    </td>

                    <td className="py-3.5 px-4">
                      <div className="text-xs text-slate-600 font-mono truncate max-w-[180px]" title={inv.original_filename}>
                        {inv.original_filename}
                      </div>
                      <div className="text-[11px] text-slate-400">
                        {(inv.file_size_bytes / 1024).toFixed(1)} KB
                      </div>
                    </td>

                    <td className="py-3.5 px-4 font-semibold text-slate-900">
                      {inv.extracted?.grand_total !== undefined && inv.extracted?.grand_total !== null ? (
                        formatCurrency(inv.extracted.grand_total, inv.extracted?.currency || "INR")
                      ) : (
                        <span className="text-slate-400 text-xs font-normal">—</span>
                      )}
                    </td>

                    <td className="py-3.5 px-4">
                      <RiskBadge score={inv.risk_score} isDuplicate={inv.is_duplicate} />
                    </td>

                    <td className="py-3.5 px-4">
                      <StatusBadge status={inv.status} />
                    </td>

                    <td className="py-3.5 px-4 text-xs text-slate-500">
                      {new Date(inv.created_at).toLocaleDateString([], {
                        month: "short",
                        day: "numeric",
                        year: "numeric",
                      })}
                    </td>

                    <td className="py-3.5 px-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        {inv.status === "FAILED" && (
                          <button
                            onClick={() => retryMutation.mutate(inv.id)}
                            disabled={retryMutation.isPending}
                            title="Retry Processing"
                            className="p-1.5 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-colors"
                          >
                            <RotateCcw className="w-3.5 h-3.5" />
                          </button>
                        )}
                        <Link
                          to={`/invoices/${inv.id}`}
                          className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-blue-50 text-blue-700 hover:bg-blue-100 text-xs font-medium transition-colors"
                        >
                          <span>Inspect</span>
                          <ExternalLink className="w-3.5 h-3.5" />
                        </Link>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Bar */}
        {data && data.pagination.total_pages > 1 && (
          <div className="p-4 border-t border-slate-200 flex items-center justify-between text-xs text-slate-500 bg-slate-50/50">
            <span>
              Showing page <strong className="text-slate-700">{data.pagination.page}</strong> of{" "}
              <strong className="text-slate-700">{data.pagination.total_pages}</strong> (
              {data.pagination.total_count} total records)
            </span>
            <div className="flex items-center gap-2">
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="px-3 py-1.5 rounded-md border border-slate-200 bg-white font-medium hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Previous
              </button>
              <button
                disabled={page >= data.pagination.total_pages}
                onClick={() => setPage((p) => p + 1)}
                className="px-3 py-1.5 rounded-md border border-slate-200 bg-white font-medium hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
