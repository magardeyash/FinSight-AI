import { apiClient } from "./client";
import {
  Invoice,
  InvoiceListResponse,
  AuditLog,
} from "@/types";

export const invoicesApi = {
  upload: async (file: File): Promise<{ invoice_id: string; job_id: string; status: string; message: string }> => {
    const formData = new FormData();
    formData.append("file", file);
    const res = await apiClient.post("/invoices/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return res.data;
  },

  list: async (params?: {
    page?: number;
    page_size?: number;
    status?: string;
    search?: string;
    date_from?: string;
    date_to?: string;
  }): Promise<InvoiceListResponse> => {
    const res = await apiClient.get<InvoiceListResponse>("/invoices", { params });
    return res.data;
  },

  getById: async (id: string): Promise<Invoice> => {
    const res = await apiClient.get<Invoice>(`/invoices/${id}`);
    return res.data;
  },

  getStatus: async (id: string): Promise<{ id: string; status: string; risk_score: number; error_message?: string }> => {
    const res = await apiClient.get(`/invoices/${id}/status`);
    return res.data;
  },

  getFileBlob: async (id: string): Promise<Blob> => {
    const res = await apiClient.get(`/invoices/${id}/file`, {
      responseType: "blob",
    });
    return res.data;
  },

  update: async (id: string, fields: Record<string, any>): Promise<Invoice> => {
    const res = await apiClient.patch<Invoice>(`/invoices/${id}`, fields);
    return res.data;
  },

  approve: async (id: string, payload?: { corrections?: Record<string, any>; comment?: string }): Promise<Invoice> => {
    const res = await apiClient.post<Invoice>(`/invoices/${id}/approve`, payload || {});
    return res.data;
  },

  reject: async (id: string, payload?: { comment?: string }): Promise<Invoice> => {
    const res = await apiClient.post<Invoice>(`/invoices/${id}/reject`, payload || {});
    return res.data;
  },

  retry: async (id: string): Promise<{ invoice_id: string; job_id: string; status: string }> => {
    const res = await apiClient.post(`/invoices/${id}/retry`);
    return res.data;
  },

  getAuditLogs: async (id: string): Promise<AuditLog[]> => {
    const res = await apiClient.get<AuditLog[]>(`/invoices/${id}/audit`);
    return res.data;
  },
};
