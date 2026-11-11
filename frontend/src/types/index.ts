export type InvoiceStatus =
  | "UPLOADED"
  | "QUEUED"
  | "PROCESSING"
  | "APPROVING"
  | "APPROVED"
  | "REVIEW_REQUIRED"
  | "FAILED"
  | "REJECTED";

export interface LineItem {
  description: string;
  quantity?: number | null;
  unit_price?: number | null;
  tax_rate?: number | null;
  amount?: number | null;
  confidence?: number | null;
}

export interface InvoiceData {
  invoice_number?: string | null;
  vendor_name?: string | null;
  vendor_gstin?: string | null;
  buyer_name?: string | null;
  buyer_gstin?: string | null;
  invoice_date?: string | null;
  due_date?: string | null;
  currency?: string | null;
  subtotal?: number | null;
  cgst?: number | null;
  sgst?: number | null;
  igst?: number | null;
  total_tax?: number | null;
  grand_total?: number | null;
  payment_terms?: string | null;
  line_items?: LineItem[];
  field_confidence?: Record<string, number>;
}

export interface Invoice {
  id: string;
  user_id: string;
  original_filename: string;
  file_size_bytes: number;
  status: InvoiceStatus;
  extracted: InvoiceData;
  risk_score: number;
  risk_flags: string[];
  validation_errors: string[];
  is_duplicate: boolean;
  duplicate_reason?: string | null;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
  completed_at?: string | null;
}

export interface PaginationMeta {
  page: number;
  page_size: number;
  total_count: number;
  total_pages: number;
}

export interface InvoiceListResponse {
  items: Invoice[];
  pagination: PaginationMeta;
}

export interface User {
  id: string;
  email: string;
  full_name?: string | null;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface StatusDistribution {
  name: string;
  value: number;
  color: string;
}

export interface DashboardStats {
  total_invoices: number;
  approved_invoices: number;
  pending_reviews: number;
  failed_jobs: number;
  processing_invoices: number;
  total_approved_value: number;
  status_distribution: StatusDistribution[];
}

export interface RecentActivity {
  id: string;
  invoice_id: string;
  action: string;
  detail: string;
  created_at: string;
}

export interface AuditLog {
  id: string;
  invoice_id: string;
  user_id: string;
  action: string;
  detail: string;
  metadata?: Record<string, any>;
  created_at: string;
}
