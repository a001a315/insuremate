export function inr(n: number | string | null | undefined): string {
  return "₹" + new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 }).format(Number(n ?? 0));
}
export function fmtDate(d: string | null | undefined): string {
  if (!d) return "—";
  const dt = new Date(d.length === 10 ? d + "T00:00:00" : d);
  return dt.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}
export function fmtDateTime(d: string): string {
  return new Date(d).toLocaleString("en-IN", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}
export const label = (s: string) => s.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());
export function fmtSize(b: number): string {
  return b > 1048576 ? (b / 1048576).toFixed(1) + " MB" : Math.max(1, Math.round(b / 1024)) + " KB";
}
export const CLAIM_STATUSES = ["draft", "pre_auth_requested", "pre_auth_approved", "pre_auth_rejected", "submitted", "under_review", "additional_documents_required", "approved", "partially_approved", "rejected", "settled"] as const;
export const RECORD_CATEGORIES = ["discharge_summary", "prescription", "diagnostic_report", "lab_report", "medical_bill", "consultation", "surgery", "other"] as const;
export const DOC_CATEGORIES = ["policy_document", "policy_schedule", "premium_receipt", "claim_form", "hospital_bill", "discharge_summary", "medical_report", "other"] as const;
export const POLICY_TYPES = ["individual", "family_floater", "senior_citizen", "critical_illness", "top_up", "group"] as const;
export const DETAIL_LABELS: Record<string, string> = {
  covered_conditions: "Covered conditions", exclusions: "Exclusions", waiting_periods: "Waiting periods", room_rent_limit: "Room rent limit",
  copay: "Co-payment", network_hospitals: "Network hospitals", restoration_benefit: "Restoration benefit", no_claim_bonus: "No-claim bonus",
};
export const CLEARANCE_LABEL: Record<string, string> = { cleared: "Cleared", pre_auth_cleared: "Pre-auth cleared", pending: "Pending", rejected: "Rejected", draft: "Draft" };
export const NETWORK_LABEL: Record<string, string> = {
  empanelled_cashless: "Cashless at this hospital", empanelled_no_cashless: "Empanelled, no cashless", not_empanelled: "Not empanelled", expired: "Empanelment lapsed", unknown: "Unknown",
};
export const INSURANCE_STATE_LABEL: Record<string, string> = { active: "Insured", expiring_soon: "Expiring soon", expired: "Expired", no_policy: "No policy" };
