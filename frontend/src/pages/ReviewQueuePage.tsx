import React, { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { invoicesApi } from "@/api/invoices";
import { StatusBadge } from "@/components/invoice/StatusBadge";
import { RiskBadge } from "@/components/invoice/RiskBadge";
import {
  CheckCircle2,
  XCircle,
  FileText,
  RotateCcw,
  Download,
  ShieldAlert,
  ChevronRight,
  Sparkles,
} from "lucide-react";

export const ReviewQueuePage: React.FC = () => {
  const queryClient = useQueryClient();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [editFields, setEditFields] = useState<Record<string, any>>({});

  // Query invoices in REVIEW_REQUIRED status
  const {
    data,
    isLoading,
  } = useQuery({
    queryKey: ["review-queue"],
    queryFn: () => invoicesApi.list({ status: "REVIEW_REQUIRED", page_size: 50 }),
    refetchInterval: 5000,
  });

  const invoices = data?.items || [];
  const selectedInvoice = invoices.find((inv) => inv.id === selectedId) || invoices[0];

  // Set default selection
  useEffect(() => {
    if (!selectedId && invoices.length > 0) {
      setSelectedId(invoices[0].id);
    }
  }, [invoices, selectedId]);

  // Sync edit form with current selection
  useEffect(() => {
    if (selectedInvoice?.extracted) {
      setEditFields({
        vendor_name: selectedInvoice.extracted.vendor_name || "",
        vendor_gstin: selectedInvoice.extracted.vendor_gstin || "",
        invoice_number: selectedInvoice.extracted.invoice_number || "",
        invoice_date: selectedInvoice.extracted.invoice_date || "",
        subtotal: selectedInvoice.extracted.subtotal ?? "",
        cgst: selectedInvoice.extracted.cgst ?? "",
        sgst: selectedInvoice.extracted.sgst ?? "",
        igst: selectedInvoice.extracted.igst ?? "",
        total_tax: selectedInvoice.extracted.total_tax ?? "",
        grand_total: selectedInvoice.extracted.grand_total ?? "",
      });
    }
  }, [selectedInvoice]);

  // Load PDF Blob when selected invoice changes
  useEffect(() => {
    let objectUrl: string | null = null;
    if (selectedInvoice?.id) {
      invoicesApi
        .getFileBlob(selectedInvoice.id)
        .then((blob) => {
          objectUrl = URL.createObjectURL(blob);
          setPdfUrl(objectUrl);
        })
        .catch((err) => {
          console.error("PDF preview error:", err);
          setPdfUrl(null);
        });
    }
    return () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [selectedInvoice?.id]);

  // Approve & Reject Mutations
  const approveMutation = useMutation({
    mutationFn: (id: string) => {
      const parsed: Record<string, any> = { ...editFields };
      ["subtotal", "cgst", "sgst", "igst", "total_tax", "grand_total"].forEach((k) => {
        if (parsed[k] !== undefined && parsed[k] !== "") {
          parsed[k] = parseFloat(parsed[k]);
        }
      });
      return invoicesApi.approve(id, { corrections: parsed });
    },
    onSuccess: () => {
      setSelectedId(null);
      queryClient.invalidateQueries({ queryKey: ["review-queue"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-stats"] });
    },
  });

  const rejectMutation = useMutation({
    mutationFn: ({ id, comment }: { id: string; comment?: string }) =>
      invoicesApi.reject(id, { comment }),
    onSuccess: () => {
      setSelectedId(null);
      queryClient.invalidateQueries({ queryKey: ["review-queue"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-stats"] });
    },
  });

  const handleApprove = () => {
    if (selectedInvoice) {
      approveMutation.mutate(selectedInvoice.id);
    }
  };

  const handleReject = () => {
    if (selectedInvoice) {
      const comment = window.prompt("Reason for rejection:") || undefined;
      rejectMutation.mutate({ id: selectedInvoice.id, comment });
    }
  };

  const formatCurrency = (val?: number | null, curr = "INR") => {
    if (val === undefined || val === null) return "—";
    try {
      return new Intl.NumberFormat("en-IN", {
        style: "currency",
        currency: curr,
      }).format(val);
    } catch {
      return `${curr} ${val.toFixed(2)}`;
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-2xl font-bold tracking-tight text-slate-900">
              Human-in-the-Loop Review Queue
            </h2>
            <span className="bg-amber-100 text-amber-800 text-xs font-bold px-2.5 py-0.5 rounded-full border border-amber-200">
              {invoices.length} Pending
            </span>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Invoices paused by LangGraph interrupt logic due to high risk scores, validation
            mismatches, or duplicate flags.
          </p>
        </div>
      </div>

      {isLoading ? (
        <div className="bg-white rounded-xl border border-slate-200 p-12 text-center shadow-sm">
          <RotateCcw className="w-8 h-8 animate-spin text-blue-600 mx-auto mb-2" />
          <p className="text-sm text-slate-500 font-medium">Loading review queue...</p>
        </div>
      ) : invoices.length === 0 ? (
        /* Empty State */
        <div className="bg-white rounded-xl border border-slate-200 p-16 text-center shadow-sm max-w-2xl mx-auto">
          <div className="w-14 h-14 bg-emerald-50 rounded-2xl flex items-center justify-center text-emerald-600 mx-auto mb-4 border border-emerald-100">
            <CheckCircle2 className="w-7 h-7" />
          </div>
          <h3 className="text-lg font-bold text-slate-900">Review Queue Clear</h3>
          <p className="text-sm text-slate-500 mt-1.5 max-w-md mx-auto">
            All submitted invoices have either passed automated validation thresholds or have
            already been adjudicated.
          </p>
        </div>
      ) : (
        /* Master-Detail Review Interface */
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Column: Queue List (4 cols) */}
          <div className="lg:col-span-4 bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden flex flex-col max-h-[820px]">
            <div className="p-4 border-b border-slate-100 bg-slate-50/75 flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-600">
                Pending Items ({invoices.length})
              </span>
              <span className="text-[11px] text-slate-400">Select to inspect</span>
            </div>

            <div className="overflow-y-auto divide-y divide-slate-100 flex-1">
              {invoices.map((inv) => {
                const isSelected = selectedInvoice?.id === inv.id;
                return (
                  <button
                    key={inv.id}
                    onClick={() => setSelectedId(inv.id)}
                    className={`w-full text-left p-4 transition-all flex items-start justify-between gap-3 ${
                      isSelected
                        ? "bg-blue-50/80 border-l-4 border-blue-600"
                        : "hover:bg-slate-50"
                    }`}
                  >
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between gap-2 mb-1">
                        <span className="font-semibold text-sm text-slate-900 truncate">
                          {inv.extracted?.invoice_number || inv.original_filename}
                        </span>
                        <RiskBadge score={inv.risk_score} isDuplicate={inv.is_duplicate} />
                      </div>
                      <p className="text-xs text-slate-600 font-medium truncate">
                        {inv.extracted?.vendor_name || "Unknown Vendor"}
                      </p>
                      <div className="flex items-center gap-2 mt-2 text-[11px] text-slate-400">
                        <span className="font-semibold text-slate-700">
                          {formatCurrency(inv.extracted?.grand_total, inv.extracted?.currency || "INR")}
                        </span>
                        <span>•</span>
                        <span>{new Date(inv.created_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                    <ChevronRight className={`w-4 h-4 mt-2 shrink-0 ${isSelected ? "text-blue-600" : "text-slate-300"}`} />
                  </button>
                );
              })}
            </div>
          </div>

          {/* Right Column: Active Inspection Pane (8 cols) */}
          {selectedInvoice && (
            <div className="lg:col-span-8 space-y-5">
              {/* Reviewer Action Bar */}
              <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm flex flex-col sm:flex-row items-center justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2.5">
                    <h3 className="text-lg font-bold text-slate-900">
                      Adjudicate: {selectedInvoice.extracted?.invoice_number || selectedInvoice.original_filename}
                    </h3>
                    <StatusBadge status={selectedInvoice.status} />
                  </div>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Correct any misextracted fields below, then approve to resume the LangGraph workflow.
                  </p>
                </div>

                <div className="flex items-center gap-2.5 w-full sm:w-auto">
                  <button
                    onClick={handleReject}
                    disabled={rejectMutation.isPending}
                    className="flex-1 sm:flex-none inline-flex items-center justify-center gap-1.5 px-4 py-2 bg-rose-50 hover:bg-rose-100 border border-rose-200 text-rose-700 rounded-lg text-sm font-medium transition-colors"
                  >
                    <XCircle className="w-4 h-4 text-rose-600" />
                    Reject
                  </button>
                  <button
                    onClick={handleApprove}
                    disabled={approveMutation.isPending}
                    className="flex-1 sm:flex-none inline-flex items-center justify-center gap-1.5 px-5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-sm font-medium shadow-sm transition-colors"
                  >
                    <CheckCircle2 className="w-4 h-4" />
                    {approveMutation.isPending ? "Approving..." : "Approve & Resume"}
                  </button>
                </div>
              </div>

              {/* Discrepancies & Risk Reason Callout */}
              {(selectedInvoice.validation_errors.length > 0 ||
                selectedInvoice.risk_flags.length > 0 ||
                selectedInvoice.is_duplicate) && (
                <div className="bg-amber-50/70 border border-amber-200/90 rounded-xl p-4 text-xs space-y-2">
                  <div className="flex items-center gap-2 font-semibold text-amber-900 text-sm">
                    <ShieldAlert className="w-4 h-4 text-amber-600" />
                    Why this invoice required review:
                  </div>

                  {selectedInvoice.is_duplicate && (
                    <div className="text-amber-800 font-medium">
                      ⚠️ Duplicate match: {selectedInvoice.duplicate_reason || "Matches existing invoice."}
                    </div>
                  )}

                  {selectedInvoice.risk_flags.length > 0 && (
                    <div>
                      <span className="font-semibold text-amber-800">Risk flags triggered: </span>
                      <span className="text-amber-700 font-mono">
                        {selectedInvoice.risk_flags.join(", ")}
                      </span>
                    </div>
                  )}

                  {selectedInvoice.validation_errors.length > 0 && (
                    <div>
                      <span className="font-semibold text-amber-800">Calculation / Schema errors:</span>
                      <ul className="list-disc pl-5 mt-1 text-amber-700 space-y-0.5">
                        {selectedInvoice.validation_errors.map((err, i) => (
                          <li key={i}>{err}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              {/* Split Sub-pane: PDF and Form */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                {/* PDF Viewer */}
                <div className="bg-white rounded-xl border border-slate-200 p-3 shadow-sm h-[560px] flex flex-col">
                  <div className="flex items-center justify-between pb-2 border-b border-slate-100 mb-2">
                    <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 flex items-center gap-1">
                      <FileText className="w-3.5 h-3.5 text-blue-500" /> Original Document
                    </span>
                    {pdfUrl && (
                      <a
                        href={pdfUrl}
                        download={selectedInvoice.original_filename}
                        className="text-[11px] font-medium text-blue-600 hover:underline flex items-center gap-1"
                      >
                        <Download className="w-3 h-3" /> Save
                      </a>
                    )}
                  </div>
                  <div className="flex-1 rounded bg-slate-100 overflow-hidden border border-slate-200">
                    {pdfUrl ? (
                      <iframe
                        src={pdfUrl}
                        title="Document Preview"
                        className="w-full h-full border-none"
                      />
                    ) : (
                      <div className="h-full flex items-center justify-center text-xs text-slate-400">
                        Loading preview...
                      </div>
                    )}
                  </div>
                </div>

                {/* Inline Correction Form */}
                <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm space-y-3 h-[560px] overflow-y-auto">
                  <div className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-slate-500 pb-2 border-b border-slate-100">
                    <Sparkles className="w-3.5 h-3.5 text-blue-500" /> Human Field Corrections
                  </div>

                  <div className="space-y-3 text-xs">
                    <div>
                      <label className="font-semibold text-slate-600 block mb-1">Vendor Name</label>
                      <input
                        type="text"
                        value={editFields.vendor_name || ""}
                        onChange={(e) =>
                          setEditFields({ ...editFields, vendor_name: e.target.value })
                        }
                        className="w-full border border-slate-200 rounded-lg p-2 text-xs focus:ring-1 focus:ring-blue-500 focus:outline-none"
                      />
                    </div>

                    <div>
                      <label className="font-semibold text-slate-600 block mb-1">Vendor GSTIN</label>
                      <input
                        type="text"
                        value={editFields.vendor_gstin || ""}
                        onChange={(e) =>
                          setEditFields({ ...editFields, vendor_gstin: e.target.value })
                        }
                        placeholder="22AAAAA0000A1Z5"
                        className="w-full font-mono border border-slate-200 rounded-lg p-2 text-xs focus:ring-1 focus:ring-blue-500 focus:outline-none"
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="font-semibold text-slate-600 block mb-1">Invoice #</label>
                        <input
                          type="text"
                          value={editFields.invoice_number || ""}
                          onChange={(e) =>
                            setEditFields({ ...editFields, invoice_number: e.target.value })
                          }
                          className="w-full border border-slate-200 rounded-lg p-2 text-xs focus:ring-1 focus:ring-blue-500 focus:outline-none"
                        />
                      </div>
                      <div>
                        <label className="font-semibold text-slate-600 block mb-1">Invoice Date</label>
                        <input
                          type="date"
                          value={editFields.invoice_date || ""}
                          onChange={(e) =>
                            setEditFields({ ...editFields, invoice_date: e.target.value })
                          }
                          className="w-full border border-slate-200 rounded-lg p-2 text-xs focus:ring-1 focus:ring-blue-500 focus:outline-none"
                        />
                      </div>
                    </div>

                    <div className="pt-2 border-t border-slate-100">
                      <span className="font-semibold text-slate-700 block mb-2">
                        Financial Calculations
                      </span>

                      <div className="grid grid-cols-2 gap-2">
                        <div>
                          <label className="text-[11px] text-slate-500 block mb-0.5">Subtotal</label>
                          <input
                            type="number"
                            step="0.01"
                            value={editFields.subtotal || ""}
                            onChange={(e) =>
                              setEditFields({ ...editFields, subtotal: e.target.value })
                            }
                            className="w-full border border-slate-200 rounded-lg p-1.5 text-xs"
                          />
                        </div>
                        <div>
                          <label className="text-[11px] text-slate-500 block mb-0.5">Total Tax</label>
                          <input
                            type="number"
                            step="0.01"
                            value={editFields.total_tax || ""}
                            onChange={(e) =>
                              setEditFields({ ...editFields, total_tax: e.target.value })
                            }
                            className="w-full border border-slate-200 rounded-lg p-1.5 text-xs"
                          />
                        </div>
                        <div>
                          <label className="text-[11px] text-slate-500 block mb-0.5">CGST</label>
                          <input
                            type="number"
                            step="0.01"
                            value={editFields.cgst || ""}
                            onChange={(e) =>
                              setEditFields({ ...editFields, cgst: e.target.value })
                            }
                            className="w-full border border-slate-200 rounded-lg p-1.5 text-xs"
                          />
                        </div>
                        <div>
                          <label className="text-[11px] text-slate-500 block mb-0.5">SGST</label>
                          <input
                            type="number"
                            step="0.01"
                            value={editFields.sgst || ""}
                            onChange={(e) =>
                              setEditFields({ ...editFields, sgst: e.target.value })
                            }
                            className="w-full border border-slate-200 rounded-lg p-1.5 text-xs"
                          />
                        </div>
                      </div>

                      <div className="mt-3 bg-blue-50/60 p-2.5 rounded-lg border border-blue-100 flex items-center justify-between">
                        <label className="font-bold text-blue-900 uppercase tracking-wider text-xs">
                          Grand Total
                        </label>
                        <input
                          type="number"
                          step="0.01"
                          value={editFields.grand_total || ""}
                          onChange={(e) =>
                            setEditFields({ ...editFields, grand_total: e.target.value })
                          }
                          className="w-36 text-right font-bold text-sm border border-blue-300 rounded p-1 bg-white"
                        />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
