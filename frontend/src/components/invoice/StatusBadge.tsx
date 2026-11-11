import React from "react";
import { InvoiceStatus } from "@/types";
import { Clock, CheckCircle2, AlertTriangle, XCircle, RefreshCw, Loader2 } from "lucide-react";

interface StatusBadgeProps {
  status: InvoiceStatus;
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, className = "" }) => {
  switch (status) {
    case "APPROVED":
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200/60 ${className}`}
        >
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
          Approved
        </span>
      );
    case "REVIEW_REQUIRED":
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200/60 ${className}`}
        >
          <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
          Review Required
        </span>
      );
    case "PROCESSING":
    case "APPROVING":
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200/60 ${className}`}
        >
          <Loader2 className="w-3.5 h-3.5 text-blue-600 animate-spin" />
          {status === "APPROVING" ? "Finalizing..." : "Processing..."}
        </span>
      );
    case "QUEUED":
    case "UPLOADED":
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-700 border border-slate-200 ${className}`}
        >
          <Clock className="w-3.5 h-3.5 text-slate-500" />
          Queued
        </span>
      );
    case "REJECTED":
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-600 border border-slate-300 ${className}`}
        >
          <XCircle className="w-3.5 h-3.5 text-slate-500" />
          Rejected
        </span>
      );
    case "FAILED":
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-rose-50 text-rose-700 border border-rose-200/60 ${className}`}
        >
          <RefreshCw className="w-3.5 h-3.5 text-rose-600" />
          Failed
        </span>
      );
    default:
      return (
        <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-700 ${className}`}>
          {status}
        </span>
      );
  }
};
