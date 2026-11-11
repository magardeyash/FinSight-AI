import React, { useState, useEffect } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { invoicesApi } from "@/api/invoices";
import { StatusBadge } from "@/components/invoice/StatusBadge";
import { RiskBadge } from "@/components/invoice/RiskBadge";
import {
  ArrowLeft,
  CheckCircle2,
  XCircle,
  RotateCcw,
  AlertTriangle,
  FileText,
  Clock,
  ShieldAlert,
  Building,
  FileCheck,
  Calculator,
  Download,
  Edit3,
  Save,
  X,
  History,
} from "lucide-react";

export const InvoiceDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [pdfError, setPdfError] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editFields, setEditFields] = useState<Record<string, any>>({});
  const [activeTab, setActiveTab] = useState<"data" | "audit">("data");

  // Fetch Invoice Details
  const {
    data: invoice,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["invoice", id],
    queryFn: () => invoicesApi.getById(id!),
    enabled: !!id,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status && ["UPLOADED", "QUEUED", "PROCESSING", "APPROVING"].includes(status)) {
        return 3000;
      }
      return false;
    },
  });

  // Fetch Audit Logs
  const { data: auditLogs } = useQuery({
    queryKey: ["invoice-audit", id],
    queryFn: () => invoicesApi.getAuditLogs(id!),
    enabled: !!id && activeTab === "audit",
  });

  // Initialize editable fields when invoice data loads
  useEffect(() => {
    if (invoice?.extracted) {
      setEditFields({
        vendor_name: invoice.extracted.vendor_name || "",
        vendor_gstin: invoice.extracted.vendor_gstin || "",
        invoice_number: invoice.extracted.invoice_number || "",
        invoice_date: invoice.extracted.invoice_date || "",
        subtotal: invoice.extracted.subtotal ?? "",
        cgst: invoice.extracted.cgst ?? "",
        sgst: invoice.extracted.sgst ?? "",
        igst: invoice.extracted.igst ?? "",
        total_tax: invoice.extracted.total_tax ?? "",
        grand_total: invoice.extracted.grand_total ?? "",
      });
    }
  }, [invoice]);

  // Load PDF Blob safely
  useEffect(() => {
    let objectUrl: string | null = null;
    if (id) {
      invoicesApi
        .getFileBlob(id)
        .then((blob) => {
          objectUrl = URL.createObjectURL(blob);
          setPdfUrl(objectUrl);
        })
        .catch((err) => {
          console.error("PDF load error:", err);
          setPdfError("Could not load preview. The file may be restricted or corrupt.");
        });
    }
    return () => {
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
      }
    };
  }, [id]);

  // Mutations
  const approveMutation = useMutation({
    mutationFn: () =>
      invoicesApi.approve(id!, isEditing ? { corrections: editFields } : {}),
    onSuccess: () => {
      setIsEditing(false);
      queryClient.invalidateQueries({ queryKey: ["invoice", id] });
      queryClient.invalidateQueries({ queryKey: ["invoices"] });
    },
  });

  const rejectMutation = useMutation({
    mutationFn: (comment?: string) =>
      invoicesApi.reject(id!, { comment: comment || "Rejected by reviewer" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["invoice", id] });
      queryClient.invalidateQueries({ queryKey: ["invoices"] });
    },
  });

  const retryMutation = useMutation({
    mutationFn: () => invoicesApi.retry(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["invoice", id] });
      queryClient.invalidateQueries({ queryKey: ["invoices"] });
    },
  });

  const saveEditsMutation = useMutation({
    mutationFn: (fields: Record<string, any>) => invoicesApi.update(id!, fields),
    onSuccess: () => {
      setIsEditing(false);
      queryClient.invalidateQueries({ queryKey: ["invoice", id] });
    },
  });

  const handleSaveEdits = () => {
    // Parse numeric fields
    const parsed: Record<string, any> = { ...editFields };
    ["subtotal", "cgst", "sgst", "igst", "total_tax", "grand_total"].forEach((k) => {
      if (parsed[k] !== undefined && parsed[k] !== "") {
        parsed[k] = parseFloat(parsed[k]);
      }
    });
    saveEditsMutation.mutate(parsed);
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

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center gap-3">
          <RotateCcw className="w-8 h-8 animate-spin text-blue-600" />
          <span className="text-slate-500 font-medium text-sm">
            Retrieving document and extraction state...
          </span>
        </div>
      </div>
    );
  }

  if (error || !invoice) {
    return (
      <div className="max-w-xl mx-auto mt-12 bg-white p-8 rounded-xl border border-slate-200 text-center shadow-sm">
        <AlertTriangle className="w-12 h-12 text-rose-500 mx-auto mb-3" />
        <h3 className="text-lg font-bold text-slate-800">Invoice Not Found</h3>
        <p className="text-sm text-slate-500 mt-1 mb-6">
          The requested invoice ID does not exist or you do not have permission to inspect it.
        </p>
        <Link
          to="/invoices"
          className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Invoices
        </Link>
      </div>
    );
  }

  const canReview = invoice.status === "REVIEW_REQUIRED";
  const isFailed = invoice.status === "FAILED";

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Navigation & Header Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 pb-5">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate(-1)}
            className="p-2 hover:bg-slate-100 rounded-lg text-slate-500 transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <div className="flex items-center gap-2.5">
              <h2 className="text-xl font-bold tracking-tight text-slate-900">
                {invoice.extracted?.invoice_number || invoice.original_filename}
              </h2>
              <StatusBadge status={invoice.status} />
              <RiskBadge score={invoice.risk_score} isDuplicate={invoice.is_duplicate} />
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Uploaded on {new Date(invoice.created_at).toLocaleString()} • File:{" "}
              <span className="font-mono">{invoice.original_filename}</span>
            </p>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2.5">
          {isFailed && (
            <button
              onClick={() => retryMutation.mutate()}
              disabled={retryMutation.isPending}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-slate-800 hover:bg-slate-900 text-white rounded-lg text-sm font-medium shadow-sm transition-colors"
            >
              <RotateCcw className={`w-4 h-4 ${retryMutation.isPending ? "animate-spin" : ""}`} />
              Retry Extraction
            </button>
          )}

          {canReview && (
            <>
              <button
                onClick={() => {
                  const reason = window.prompt("Reason for rejection:");
                  if (reason !== null) rejectMutation.mutate(reason);
                }}
                disabled={rejectMutation.isPending}
                className="inline-flex items-center gap-1.5 px-4 py-2 bg-rose-50 hover:bg-rose-100 border border-rose-200 text-rose-700 rounded-lg text-sm font-medium transition-colors"
              >
                <XCircle className="w-4 h-4 text-rose-600" />
                Reject
              </button>

              <button
                onClick={() => approveMutation.mutate()}
                disabled={approveMutation.isPending}
                className="inline-flex items-center gap-1.5 px-5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-sm font-medium shadow-sm transition-colors"
              >
                <CheckCircle2 className="w-4 h-4" />
                {approveMutation.isPending ? "Approving..." : "Approve Invoice"}
              </button>
            </>
          )}
        </div>
      </div>

      {/* Warning/Alert Banners */}
      {invoice.is_duplicate && (
        <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl flex items-start gap-3 text-sm text-amber-800">
          <AlertTriangle className="w-5 h-5 shrink-0 text-amber-600 mt-0.5" />
          <div>
            <h4 className="font-semibold text-amber-900">Duplicate Document Detected</h4>
            <p className="text-xs text-amber-700 mt-0.5">
              {invoice.duplicate_reason ||
                "This document matches an existing invoice number, vendor, or cryptographic checksum."}
            </p>
          </div>
        </div>
      )}

      {invoice.validation_errors && invoice.validation_errors.length > 0 && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-sm text-rose-800">
          <div className="flex items-center gap-2 font-semibold text-rose-900 mb-1.5">
            <ShieldAlert className="w-4 h-4 text-rose-600" />
            Validation Discrepancies ({invoice.validation_errors.length})
          </div>
          <ul className="list-disc pl-5 space-y-1 text-xs text-rose-700">
            {invoice.validation_errors.map((err, i) => (
              <li key={i}>{err}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Two Column Layout: PDF Preview & Extracted Intelligence */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Side: PDF Viewer (5 cols) */}
        <div className="lg:col-span-5 bg-white rounded-xl border border-slate-200 p-4 shadow-sm h-[780px] flex flex-col">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100 mb-3">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
              <FileText className="w-4 h-4 text-blue-500" /> Source Document
            </span>
            {pdfUrl && (
              <a
                href={pdfUrl}
                download={invoice.original_filename}
                className="inline-flex items-center gap-1 text-xs font-medium text-blue-600 hover:text-blue-700"
              >
                <Download className="w-3.5 h-3.5" /> Download
              </a>
            )}
          </div>

          <div className="flex-1 rounded-lg overflow-hidden bg-slate-100 border border-slate-200 relative">
            {pdfUrl ? (
              <iframe
                src={pdfUrl}
                title="Invoice Document"
                className="w-full h-full border-none"
              />
            ) : pdfError ? (
              <div className="h-full flex flex-col items-center justify-center p-6 text-center text-slate-400">
                <AlertTriangle className="w-8 h-8 text-rose-400 mb-2" />
                <p className="text-sm">{pdfError}</p>
              </div>
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-slate-400">
                <RotateCcw className="w-6 h-6 animate-spin text-blue-500 mb-2" />
                <span className="text-xs">Rendering PDF preview...</span>
              </div>
            )}
          </div>
        </div>

        {/* Right Side: Extracted Structured Fields & Audit (7 cols) */}
        <div className="lg:col-span-7 space-y-5">
          {/* Tabs */}
          <div className="flex items-center justify-between border-b border-slate-200 pb-2">
            <div className="flex items-center gap-4">
              <button
                onClick={() => setActiveTab("data")}
                className={`text-sm font-semibold pb-2 border-b-2 -mb-2.5 transition-colors ${
                  activeTab === "data"
                    ? "border-blue-600 text-blue-600"
                    : "border-transparent text-slate-500 hover:text-slate-800"
                }`}
              >
                Structured Extraction
              </button>
              <button
                onClick={() => setActiveTab("audit")}
                className={`text-sm font-semibold pb-2 border-b-2 -mb-2.5 transition-colors flex items-center gap-1.5 ${
                  activeTab === "audit"
                    ? "border-blue-600 text-blue-600"
                    : "border-transparent text-slate-500 hover:text-slate-800"
                }`}
              >
                <History className="w-3.5 h-3.5" />
                Audit Trail
              </button>
            </div>

            {activeTab === "data" && !isEditing && (
              <button
                onClick={() => setIsEditing(true)}
                className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-600 hover:text-blue-600 px-2.5 py-1 rounded-md border border-slate-200 hover:border-blue-300 bg-white transition-colors"
              >
                <Edit3 className="w-3.5 h-3.5" />
                Correct Fields
              </button>
            )}

            {isEditing && (
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setIsEditing(false)}
                  className="inline-flex items-center gap-1 text-xs font-medium text-slate-500 hover:text-slate-700 px-2 py-1 rounded border border-slate-200"
                >
                  <X className="w-3.5 h-3.5" /> Cancel
                </button>
                <button
                  onClick={handleSaveEdits}
                  disabled={saveEditsMutation.isPending}
                  className="inline-flex items-center gap-1 text-xs font-medium text-white bg-blue-600 hover:bg-blue-700 px-2.5 py-1 rounded shadow-sm"
                >
                  <Save className="w-3.5 h-3.5" /> Save Changes
                </button>
              </div>
            )}
          </div>

          {activeTab === "data" ? (
            <div className="space-y-5">
              {/* Vendor & Invoice Metadata Card */}
              <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
                <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
                  <Building className="w-4 h-4 text-blue-500" /> Vendor & Tax Registration
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-[11px] font-semibold text-slate-500 uppercase">
                      Vendor Name
                    </label>
                    {isEditing ? (
                      <input
                        type="text"
                        value={editFields.vendor_name || ""}
                        onChange={(e) =>
                          setEditFields({ ...editFields, vendor_name: e.target.value })
                        }
                        className="mt-1 w-full text-sm font-medium text-slate-900 border border-slate-200 rounded-md p-2 bg-slate-50 focus:bg-white focus:outline-none focus:ring-1 focus:ring-blue-500"
                      />
                    ) : (
                      <p className="mt-1 text-sm font-semibold text-slate-900">
                        {invoice.extracted?.vendor_name || "—"}
                      </p>
                    )}
                  </div>

                  <div>
                    <label className="block text-[11px] font-semibold text-slate-500 uppercase">
                      Vendor GSTIN
                    </label>
                    {isEditing ? (
                      <input
                        type="text"
                        value={editFields.vendor_gstin || ""}
                        onChange={(e) =>
                          setEditFields({ ...editFields, vendor_gstin: e.target.value })
                        }
                        className="mt-1 w-full text-sm font-mono font-medium text-slate-900 border border-slate-200 rounded-md p-2 bg-slate-50 focus:bg-white focus:outline-none focus:ring-1 focus:ring-blue-500"
                      />
                    ) : (
                      <p className="mt-1 text-sm font-mono font-medium text-slate-900">
                        {invoice.extracted?.vendor_gstin || "—"}
                      </p>
                    )}
                  </div>
                </div>

                <div className="pt-3 border-t border-slate-100 grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-[11px] font-semibold text-slate-500 uppercase">
                      Invoice #
                    </label>
                    {isEditing ? (
                      <input
                        type="text"
                        value={editFields.invoice_number || ""}
                        onChange={(e) =>
                          setEditFields({ ...editFields, invoice_number: e.target.value })
                        }
                        className="mt-1 w-full text-sm font-semibold text-slate-900 border border-slate-200 rounded-md p-1.5 bg-slate-50 focus:bg-white"
                      />
                    ) : (
                      <p className="mt-1 text-sm font-semibold text-slate-900">
                        {invoice.extracted?.invoice_number || "—"}
                      </p>
                    )}
                  </div>

                  <div>
                    <label className="block text-[11px] font-semibold text-slate-500 uppercase">
                      Invoice Date
                    </label>
                    {isEditing ? (
                      <input
                        type="date"
                        value={editFields.invoice_date || ""}
                        onChange={(e) =>
                          setEditFields({ ...editFields, invoice_date: e.target.value })
                        }
                        className="mt-1 w-full text-sm text-slate-900 border border-slate-200 rounded-md p-1.5 bg-slate-50 focus:bg-white"
                      />
                    ) : (
                      <p className="mt-1 text-sm text-slate-700">
                        {invoice.extracted?.invoice_date || "—"}
                      </p>
                    )}
                  </div>

                  <div>
                    <label className="block text-[11px] font-semibold text-slate-500 uppercase">
                      Currency
                    </label>
                    <p className="mt-1 text-sm font-mono text-slate-700">
                      {invoice.extracted?.currency || "INR"}
                    </p>
                  </div>
                </div>
              </div>

              {/* Financial Calculation Breakdown Card */}
              <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
                <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
                  <Calculator className="w-4 h-4 text-emerald-500" /> Financial Reconciliation
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-slate-50 p-4 rounded-lg border border-slate-100">
                  <div>
                    <span className="text-[11px] text-slate-500 block">Subtotal</span>
                    {isEditing ? (
                      <input
                        type="number"
                        step="0.01"
                        value={editFields.subtotal || ""}
                        onChange={(e) =>
                          setEditFields({ ...editFields, subtotal: e.target.value })
                        }
                        className="w-full text-sm font-medium border border-slate-200 rounded p-1 bg-white"
                      />
                    ) : (
                      <span className="text-sm font-semibold text-slate-800">
                        {formatCurrency(invoice.extracted?.subtotal, invoice.extracted?.currency || "INR")}
                      </span>
                    )}
                  </div>

                  <div>
                    <span className="text-[11px] text-slate-500 block">CGST</span>
                    {isEditing ? (
                      <input
                        type="number"
                        step="0.01"
                        value={editFields.cgst || ""}
                        onChange={(e) =>
                          setEditFields({ ...editFields, cgst: e.target.value })
                        }
                        className="w-full text-sm font-medium border border-slate-200 rounded p-1 bg-white"
                      />
                    ) : (
                      <span className="text-sm font-semibold text-slate-800">
                        {formatCurrency(invoice.extracted?.cgst, invoice.extracted?.currency || "INR")}
                      </span>
                    )}
                  </div>

                  <div>
                    <span className="text-[11px] text-slate-500 block">SGST</span>
                    {isEditing ? (
                      <input
                        type="number"
                        step="0.01"
                        value={editFields.sgst || ""}
                        onChange={(e) =>
                          setEditFields({ ...editFields, sgst: e.target.value })
                        }
                        className="w-full text-sm font-medium border border-slate-200 rounded p-1 bg-white"
                      />
                    ) : (
                      <span className="text-sm font-semibold text-slate-800">
                        {formatCurrency(invoice.extracted?.sgst, invoice.extracted?.currency || "INR")}
                      </span>
                    )}
                  </div>

                  <div>
                    <span className="text-[11px] text-slate-500 block">IGST</span>
                    {isEditing ? (
                      <input
                        type="number"
                        step="0.01"
                        value={editFields.igst || ""}
                        onChange={(e) =>
                          setEditFields({ ...editFields, igst: e.target.value })
                        }
                        className="w-full text-sm font-medium border border-slate-200 rounded p-1 bg-white"
                      />
                    ) : (
                      <span className="text-sm font-semibold text-slate-800">
                        {formatCurrency(invoice.extracted?.igst, invoice.extracted?.currency || "INR")}
                      </span>
                    )}
                  </div>
                </div>

                <div className="flex items-center justify-between pt-2 px-1">
                  <div>
                    <span className="text-xs text-slate-500 uppercase tracking-wider block">
                      Total Tax
                    </span>
                    <span className="text-base font-semibold text-slate-700">
                      {formatCurrency(invoice.extracted?.total_tax, invoice.extracted?.currency || "INR")}
                    </span>
                  </div>

                  <div className="text-right">
                    <span className="text-xs font-semibold text-blue-600 uppercase tracking-wider block">
                      Grand Total
                    </span>
                    {isEditing ? (
                      <input
                        type="number"
                        step="0.01"
                        value={editFields.grand_total || ""}
                        onChange={(e) =>
                          setEditFields({ ...editFields, grand_total: e.target.value })
                        }
                        className="text-right text-lg font-bold text-slate-900 border border-slate-200 rounded p-1 bg-white"
                      />
                    ) : (
                      <span className="text-2xl font-bold text-slate-900">
                        {formatCurrency(invoice.extracted?.grand_total, invoice.extracted?.currency || "INR")}
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* Line Items Table */}
              <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
                    <FileCheck className="w-4 h-4 text-blue-500" /> Extracted Line Items (
                    {invoice.extracted?.line_items?.length || 0})
                  </div>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr className="border-b border-slate-200 bg-slate-50 text-slate-500 uppercase font-semibold">
                        <th className="py-2.5 px-3">Description</th>
                        <th className="py-2.5 px-3 text-right">Qty</th>
                        <th className="py-2.5 px-3 text-right">Unit Price</th>
                        <th className="py-2.5 px-3 text-right">Tax %</th>
                        <th className="py-2.5 px-3 text-right">Total</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {!invoice.extracted?.line_items ||
                      invoice.extracted.line_items.length === 0 ? (
                        <tr>
                          <td colSpan={5} className="py-6 text-center text-slate-400 italic">
                            No discrete line items detected in document.
                          </td>
                        </tr>
                      ) : (
                        invoice.extracted.line_items.map((item, idx) => (
                          <tr key={idx} className="hover:bg-slate-50/70">
                            <td className="py-2.5 px-3 font-medium text-slate-800">
                              {item.description}
                            </td>
                            <td className="py-2.5 px-3 text-right text-slate-600">
                              {item.quantity ?? "—"}
                            </td>
                            <td className="py-2.5 px-3 text-right text-slate-600">
                              {item.unit_price ? formatCurrency(item.unit_price) : "—"}
                            </td>
                            <td className="py-2.5 px-3 text-right text-slate-600">
                              {item.tax_rate !== undefined && item.tax_rate !== null
                                ? `${item.tax_rate}%`
                                : "—"}
                            </td>
                            <td className="py-2.5 px-3 text-right font-semibold text-slate-900">
                              {item.amount ? formatCurrency(item.amount) : "—"}
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          ) : (
            /* Audit Trail Tab */
            <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
                <Clock className="w-4 h-4 text-blue-500" /> System Lifecycle & Checkpoint Stream
              </div>

              {!auditLogs || auditLogs.length === 0 ? (
                <div className="py-8 text-center text-slate-400 text-sm">
                  No audit logs recorded for this document.
                </div>
              ) : (
                <div className="space-y-4 relative before:absolute before:left-3 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200">
                  {auditLogs.map((log) => (
                    <div key={log.id} className="relative pl-7">
                      <div className="absolute left-1.5 top-1.5 w-3.5 h-3.5 rounded-full bg-blue-600 border-2 border-white ring-1 ring-blue-200" />
                      <div className="bg-slate-50 rounded-lg p-3 border border-slate-100">
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-semibold text-xs text-slate-800 uppercase tracking-wider">
                            {log.action}
                          </span>
                          <span className="text-[11px] text-slate-400">
                            {new Date(log.created_at).toLocaleString()}
                          </span>
                        </div>
                        <p className="text-xs text-slate-600 mt-1">{log.detail}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
