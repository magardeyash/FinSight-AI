import React from "react";
import { ShieldCheck, ShieldAlert, Copy } from "lucide-react";

interface RiskBadgeProps {
  score: number;
  flags?: string[];
  isDuplicate?: boolean;
  className?: string;
}

export const RiskBadge: React.FC<RiskBadgeProps> = ({
  score,
  flags: _flags = [],
  isDuplicate = false,
  className = "",
}) => {
  const isHighRisk = score >= 0.40 || isDuplicate;

  if (isDuplicate) {
    return (
      <div
        className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-semibold bg-amber-50 text-amber-800 border border-amber-300 ${className}`}
      >
        <Copy className="w-3.5 h-3.5 text-amber-600" />
        <span>Duplicate ({(score * 100).toFixed(0)}%)</span>
      </div>
    );
  }

  if (isHighRisk) {
    return (
      <div
        className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200 ${className}`}
      >
        <ShieldAlert className="w-3.5 h-3.5 text-rose-600" />
        <span>High Risk ({(score * 100).toFixed(0)}%)</span>
      </div>
    );
  }

  return (
    <div
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 ${className}`}
    >
      <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
      <span>Low Risk ({(score * 100).toFixed(0)}%)</span>
    </div>
  );
};
