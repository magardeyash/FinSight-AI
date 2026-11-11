import React, { useState, useRef } from "react";
import { Upload, FileText, CheckCircle, AlertCircle, Loader2 } from "lucide-react";
import { invoicesApi } from "@/api/invoices";

interface UploadZoneProps {
  onUploadSuccess?: () => void;
  className?: string;
}

export const UploadZone: React.FC<UploadZoneProps> = ({ onUploadSuccess, className = "" }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [statusMessage, setStatusMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFiles = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setStatusMessage(null);
    setIsUploading(true);

    let successCount = 0;
    let errorCount = 0;
    let lastError = "";

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      if (!file.name.toLowerCase().endsWith(".pdf")) {
        errorCount++;
        lastError = `File '${file.name}' is not a PDF. Only digital PDF files are supported.`;
        continue;
      }

      try {
        await invoicesApi.upload(file);
        successCount++;
      } catch (err: any) {
        errorCount++;
        lastError = err.response?.data?.detail || `Upload failed for ${file.name}.`;
      }
    }

    setIsUploading(false);

    if (errorCount === 0 && successCount > 0) {
      setStatusMessage({
        type: "success",
        text: `Successfully queued ${successCount} invoice${successCount > 1 ? "s" : ""} for AI extraction!`,
      });
      if (onUploadSuccess) onUploadSuccess();
    } else if (successCount > 0) {
      setStatusMessage({
        type: "error",
        text: `Uploaded ${successCount} invoice(s), but ${errorCount} failed: ${lastError}`,
      });
      if (onUploadSuccess) onUploadSuccess();
    } else {
      setStatusMessage({
        type: "error",
        text: lastError || "Failed to upload file.",
      });
    }

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    handleFiles(e.dataTransfer.files);
  };

  return (
    <div className={`w-full ${className}`}>
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all duration-200 ${
          isDragging
            ? "border-blue-500 bg-blue-50/50 scale-[0.99]"
            : "border-slate-300 hover:border-blue-400 bg-white hover:bg-slate-50/50"
        } ${isUploading ? "pointer-events-none opacity-60" : ""}`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,application/pdf"
          multiple
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />

        <div className="flex flex-col items-center justify-center gap-3">
          <div className="w-12 h-12 rounded-full bg-blue-50 flex items-center justify-center text-blue-600 shadow-sm border border-blue-100">
            {isUploading ? (
              <Loader2 className="w-6 h-6 animate-spin" />
            ) : (
              <Upload className="w-6 h-6" />
            )}
          </div>

          <div>
            <p className="text-sm font-semibold text-slate-800">
              {isUploading
                ? "Processing and uploading document..."
                : "Click or drag invoice PDFs to upload"}
            </p>
            <p className="text-xs text-slate-500 mt-1">
              Supports text-based digital PDF documents up to 20MB
            </p>
          </div>

          <div className="inline-flex items-center gap-1.5 text-[11px] font-medium text-slate-400 bg-slate-100 px-2.5 py-1 rounded-md">
            <FileText className="w-3.5 h-3.5" />
            <span>PyMuPDF Text Engine • Gemini 2.5 Flash</span>
          </div>
        </div>
      </div>

      {statusMessage && (
        <div
          className={`mt-3 p-3 rounded-lg text-xs flex items-center gap-2 border ${
            statusMessage.type === "success"
              ? "bg-emerald-50 text-emerald-800 border-emerald-200"
              : "bg-rose-50 text-rose-800 border-rose-200"
          }`}
        >
          {statusMessage.type === "success" ? (
            <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0" />
          ) : (
            <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
          )}
          <span>{statusMessage.text}</span>
        </div>
      )}
    </div>
  );
};
