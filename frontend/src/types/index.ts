export interface User { id: string; email: string; full_name: string; is_demo: boolean; hospital_name: string; hospital_city: string | null }
export interface TokenResponse { access_token: string; token_type: string; user: User }

export type DetailSource = "manual" | "extracted" | "ai_summary";
export interface DetailField { value: string; source: DetailSource }
export interface Member { id?: string; name: string; relationship_to_holder: string; date_of_birth?: string | null }

export type NetworkStatus = "empanelled_cashless" | "empanelled_no_cashless" | "not_empanelled" | "expired" | "unknown";
export type Clearance = "cleared" | "pre_auth_cleared" | "pending" | "rejected" | "draft";

export interface Patient {
  id: string; full_name: string; mrn: string | null; date_of_birth: string | null; gender: string | null; phone: string | null; notes: string | null; created_at: string;
}
export interface PatientListItem extends Patient {
  active_policies: number; open_claims: number; latest_claim_status: string | null; latest_clearance: Clearance | null;
  insurance_state: "active" | "expiring_soon" | "expired" | "no_policy";
}
export interface Empanelment { id: string; insurer: string; tpa_name: string | null; cashless_enabled: boolean; valid_until: string | null; notes: string | null }
export interface EligibilityCheck { key: string; label: string; status: "pass" | "fail" | "warn" | "info" | "unknown"; detail: string; source: "recorded_data" | "hospital_setup" }
export interface EligibilityResult {
  policy_id: string; policy_name: string; insurer: string; verdict: "eligible_cashless" | "eligible_reimbursement" | "needs_review" | "not_eligible";
  verdict_label: string; checks: EligibilityCheck[]; disclaimer: string;
}

export interface PolicyListItem {
  patient_id: string | null; patient_name: string | null; tpa_name: string | null; network_status: NetworkStatus;
  id: string; name: string; insurer: string; masked_policy_number: string; policy_type: string; sum_insured: number;
  premium_amount: number; premium_frequency: string; expiry_date: string | null; renewal_date: string | null; status: string;
}
export interface Policy {
  patient_id: string; tpa_name: string | null; initial_waiting_days: number; network_status: NetworkStatus;
  id: string; name: string; insurer: string; policy_number: string; policy_type: string; policyholder_name: string;
  sum_insured: number; premium_amount: number; premium_frequency: string; start_date: string | null; expiry_date: string | null;
  renewal_date: string | null; status: string; nominee: Record<string, string> | null; details: Record<string, DetailField>;
  ai_summary: string | null; members: Member[];
}

export type ClaimStatus = "draft" | "pre_auth_requested" | "pre_auth_approved" | "pre_auth_rejected" | "submitted" | "under_review" | "additional_documents_required" | "approved" | "partially_approved" | "rejected" | "settled";
export interface Claim {
  id: string; claim_ref: string; policy_id: string; patient_id: string; patient_name: string; clearance: Clearance; insurer: string | null;
  insurer_reference: string | null; rejection_reason: string | null; hospital_name: string | null;
  hospitalization_date: string | null; discharge_date: string | null; claim_amount: number; approved_amount: number | null;
  claim_type: "cashless" | "reimbursement"; submission_date: string | null; status: ClaimStatus; notes: string | null;
}
export interface ActivityItem { id: string; action: string; summary: string; created_at: string; meta?: Record<string, unknown> | null }

export interface MedicalRecord {
  id: string; title: string; category: string; patient_id: string; patient_name: string; provider: string | null; record_date: string | null;
  claim_id: string | null; policy_id: string | null; document_id: string | null; notes: string | null;
}
export interface DocumentItem {
  id: string; policy_id: string | null; patient_id: string | null; original_name: string; mime_type: string; size_bytes: number; category: string;
  index_status: string; index_error: string | null; page_count: number | null; created_at: string; indexed_at: string | null;
}
export interface Reminder {
  id: string; title: string; description: string | null; kind: string; due_date: string; policy_id: string | null;
  claim_id: string | null; is_completed: boolean; is_auto: boolean;
}
export interface NotificationItem { id: string; title: string; body: string | null; is_read: boolean; created_at: string }

export interface Citation {
  type: "document" | "recorded_data"; label?: string; document_id?: string; document_name?: string;
  page_number?: number | null; excerpt?: string; score?: number;
}
export interface ChatMessage { id: string; role: "user" | "assistant"; content: string; citations: Citation[]; created_at: string }
export interface Conversation { id: string; title: string; policy_id: string | null; updated_at: string }

export interface Dashboard {
  summary: { patients: number; active_policies: number; expiring_policies: number; pending_claims: number; rejected_claims: number; cleared_claims: number;
    amount_pending: number; amount_approved: number; amount_pending_display: string; amount_approved_display: string; empanelled_insurers: number };
  claims_by_status: { status: string; count: number }[];
  expiring: { id: string; name: string; insurer: string; patient_id: string | null; patient_name: string | null; expiry_date: string | null; days_left: number | null; network_status: NetworkStatus }[];
  recent_claims: { id: string; claim_ref: string; patient_id: string | null; patient_name: string; insurer: string | null; claim_amount: number; status: ClaimStatus; clearance: Clearance }[];
  recent_documents: { id: string; name: string; category: string; index_status: string; created_at: string }[];
  activity: ActivityItem[];
  insights: { kind: string; text: string; patient_id?: string | null }[];
}
export interface AiStatus {
  llm: { reachable: boolean; model: string; model_available: boolean; detail: string };
  embedding_model: string; vector_store: { ok: boolean; vectors: number }; chunk_size: number; chunk_overlap: number;
  documents_by_status: Record<string, number>;
}
