import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, tokenStore } from "@/services/api";
import type { ActivityItem, AiStatus, Claim, Empanelment, Patient, PatientListItem, Conversation, ChatMessage, Dashboard, DocumentItem, MedicalRecord, NotificationItem, Policy, PolicyListItem, Reminder } from "@/types";

const qs = (p: Record<string, string | undefined>) => {
  const s = new URLSearchParams(Object.entries(p).filter(([, v]) => v) as [string, string][]).toString();
  return s ? `?${s}` : "";
};
const json = (body: unknown) => JSON.stringify(body);

export const usePolicies = (includeArchived = false, patientId?: string) => useQuery({ queryKey: ["policies", includeArchived, patientId ?? ""], queryFn: () => api<PolicyListItem[]>(`/policies${qs({ include_archived: includeArchived ? "true" : undefined, patient_id: patientId })}`) });
export const usePatients = (q?: string) => useQuery({ queryKey: ["patients", q ?? ""], queryFn: () => api<PatientListItem[]>(`/patients${qs({ q })}`) });
export const usePatient = (id: string) => useQuery({ queryKey: ["patient", id], enabled: !!id, queryFn: () => api<Patient>(`/patients/${id}`) });
export const useEmpanelments = () => useQuery({ queryKey: ["empanelments"], queryFn: () => api<Empanelment[]>("/hospital/empanelments") });
export const usePolicy = (id: string) => useQuery({ queryKey: ["policy", id], enabled: !!id, queryFn: () => api<Policy>(`/policies/${id}`) });
export const useClaims = (f: { status?: string; policy_id?: string; patient_id?: string } = {}) => useQuery({ queryKey: ["claims", f], queryFn: () => api<Claim[]>(`/claims${qs(f)}`) });
export const useClaim = (id: string) => useQuery({ queryKey: ["claim", id], queryFn: () => api<Claim>(`/claims/${id}`) });
export const useClaimActivity = (id: string) => useQuery({ queryKey: ["claim-activity", id], queryFn: () => api<ActivityItem[]>(`/claims/${id}/activity`) });
export const useClaimDocs = (id: string) => useQuery({ queryKey: ["claim-docs", id], queryFn: () => api<DocumentItem[]>(`/claims/${id}/documents`) });
export const useRecords = (f: Record<string, string | undefined>) => useQuery({ queryKey: ["records", f], queryFn: () => api<MedicalRecord[]>(`/records${qs(f)}`) });
export const useReminders = () => useQuery({ queryKey: ["reminders"], queryFn: () => api<Reminder[]>("/reminders") });
export const useDashboard = () => useQuery({ queryKey: ["dashboard"], queryFn: () => api<Dashboard>("/dashboard") });
export const useAiStatus = () => useQuery({ queryKey: ["ai-status"], queryFn: () => api<AiStatus>("/ai/status") });
export const useNotifications = () => useQuery({ queryKey: ["notifications"], refetchInterval: 60000, queryFn: () => api<{ unread: number; items: NotificationItem[] }>("/notifications") });
export const useConversations = () => useQuery({ queryKey: ["conversations"], queryFn: () => api<Conversation[]>("/chat/conversations") });
export const useMessages = (id: string | null) => useQuery({ queryKey: ["messages", id], enabled: !!id, queryFn: () => api<ChatMessage[]>(`/chat/conversations/${id}/messages`) });

/** Documents poll while any are still being processed so status changes appear without a refresh. */
export const useDocuments = (f: Record<string, string | undefined> = {}) => useQuery({
  queryKey: ["documents", f], queryFn: () => api<DocumentItem[]>(`/documents${qs(f)}`),
  refetchInterval: (q) => (q.state.data?.some((d) => !["indexed", "failed", "uploaded"].includes(d.index_status)) ? 1500 : false),
});

/** Run a mutation, then invalidate the given query-key prefixes. */
export function useApi<TIn, TOut = unknown>(fn: (v: TIn) => Promise<TOut>, invalidate: string[] = []) {
  const qc = useQueryClient();
  return useMutation({ mutationFn: fn, onSuccess: () => { invalidate.forEach((k) => qc.invalidateQueries({ queryKey: [k] })); } });
}

export const post = <T>(path: string, body?: unknown) => api<T>(path, { method: "POST", body: body === undefined ? undefined : json(body) });
export const patch = <T>(path: string, body: unknown) => api<T>(path, { method: "PATCH", body: json(body) });
export const del = (path: string) => api<void>(path, { method: "DELETE" });

export function uploadDocument(file: File, category: string, policyId?: string, onProgress?: (pct: number) => void, patientId?: string): Promise<DocumentItem> {
  return new Promise((resolve, reject) => {
    const form = new FormData();
    form.append("file", file); form.append("category", category);
    if (policyId) form.append("policy_id", policyId);
    if (patientId) form.append("patient_id", patientId);
    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/documents");
    xhr.setRequestHeader("Authorization", `Bearer ${tokenStore.get()}`);
    xhr.upload.onprogress = (e) => e.lengthComputable && onProgress?.(Math.round((e.loaded / e.total) * 100));
    xhr.onload = () => {
      let body: { detail?: unknown } = {};
      try { body = JSON.parse(xhr.responseText); } catch { /* ignore */ }
      if (xhr.status >= 200 && xhr.status < 300) resolve(body as unknown as DocumentItem);
      else reject(new Error(typeof body.detail === "string" ? body.detail : "Upload failed"));
    };
    xhr.onerror = () => reject(new Error("Cannot reach the server. Is the backend running?"));
    xhr.send(form);
  });
}

/** Authenticated file fetch (files are private, so plain links without a token would fail). */
export async function fetchFileBlob(id: string, mode: "download" | "preview"): Promise<Blob> {
  const res = await fetch(`/api/documents/${id}/${mode}`, { headers: { Authorization: `Bearer ${tokenStore.get()}` } });
  if (!res.ok) throw new Error("Could not load the file");
  return res.blob();
}
export async function openFile(id: string, name: string, mode: "download" | "preview") {
  const blob = await fetchFileBlob(id, mode);
  const url = URL.createObjectURL(blob);
  if (mode === "preview") window.open(url, "_blank", "noopener");
  else { const a = document.createElement("a"); a.href = url; a.download = name; a.click(); }
  setTimeout(() => URL.revokeObjectURL(url), 60000);
}
