import { Check, Paperclip, Pencil, Trash2, X } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ClaimForm } from "@/components/claims/ClaimForm";
import { DocumentTable } from "@/components/documents/DocumentTable";
import { UploadZone } from "@/components/documents/UploadZone";
import { Button } from "@/components/ui/Button";
import { Field, SelectField, TextArea } from "@/components/ui/Field";
import { Card, ClearanceBadge, ConfirmDialog, DefList, EmptyState, ErrorNote, Modal, PageHeader, Spinner, StatusBadge } from "@/components/ui/kit";
import { useToast } from "@/context/ToastContext";
import { del, post, useApi, useClaim, useClaimActivity, useClaimDocs, useDocuments, usePolicy, useRecords } from "@/services/hooks";
import { CLAIM_STATUSES, fmtDate, fmtDateTime, inr, label } from "@/utils/format";

export function ClaimDetailPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const { data: c, isLoading, error } = useClaim(id);
  const policy = usePolicy(c?.policy_id ?? "");
  const activity = useClaimActivity(id);
  const docs = useClaimDocs(id);
  const allDocs = useDocuments();
  const records = useRecords({ claim_id: id });
  const [editing, setEditing] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [status, setStatus] = useState("");
  const [approved, setApproved] = useState("");
  const [statusNote, setStatusNote] = useState("");
  const [reason, setReason] = useState("");
  const [insRef, setInsRef] = useState("");
  const [note, setNote] = useState("");
  const [pick, setPick] = useState("");
  const inv = ["claim", "claims", "claim-activity", "dashboard", "patients"];
  const changeStatus = useApi((b: Record<string, unknown>) => post(`/claims/${id}/status`, b), inv);
  const addNote = useApi((n: string) => post(`/claims/${id}/notes`, { note: n }), inv);
  const attach = useApi((docId: string) => post(`/claims/${id}/documents`, { document_id: docId }), ["claim-docs", "claim-activity"]);
  const detach = useApi((docId: string) => del(`/claims/${id}/documents/${docId}`), ["claim-docs"]);
  const remove = useApi(() => del(`/claims/${id}`), ["claims", "dashboard"]);

  if (isLoading) return <Spinner />;
  if (error || !c) return <ErrorNote error={error ?? new Error("Claim not found")} />;
  const attachedIds = new Set(docs.data?.map((d) => d.id));
  const fail = (e: unknown) => toast(e instanceof Error ? e.message : "Failed", "error");

  return (
    <div>
      <p className="mb-2 text-sm"><Link to={`/patients/${c.patient_id}`} className="text-muted hover:text-ink">← {c.patient_name}</Link><span className="mx-2 text-line">|</span><Link to="/claims" className="text-muted hover:text-ink">All claims</Link></p>
      <PageHeader title={c.claim_ref} subtitle={`${c.patient_name}${c.hospital_name ? ` · ${c.hospital_name}` : ""}`}
        actions={<><ClearanceBadge clearance={c.clearance} /><StatusBadge status={c.status} /><Button variant="outline" size="sm" onClick={() => setEditing(true)}><Pencil size={14} />Edit</Button>
          <Button variant="outline" size="sm" onClick={() => setConfirmDelete(true)}><Trash2 size={14} />Delete</Button></>} />
      <div className="grid gap-4 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          <Card title="Details"><DefList items={[
            ["Patient", <Link className="text-primary hover:underline" to={`/patients/${c.patient_id}`}>{c.patient_name}</Link>],
            ["Insurer", c.insurer ?? "—"], ["Insurer / TPA reference", c.insurer_reference ?? "—"],
            ...(c.rejection_reason ? [["Reason noted for rejection", c.rejection_reason] as [string, string]] : []),
            ["Policy", policy.data ? <Link className="text-primary hover:underline" to={`/policies/${policy.data.id}`}>{policy.data.name}</Link> : "—"],
            ["Claim type", label(c.claim_type)], ["Claim amount", inr(c.claim_amount)], ["Approved amount", c.approved_amount != null ? inr(c.approved_amount) : "—"],
            ["Hospitalization", fmtDate(c.hospitalization_date)], ["Discharge", fmtDate(c.discharge_date)], ["Submission date", fmtDate(c.submission_date)],
            ["Notes", c.notes ?? "—"]]} /></Card>
          <Card title="Update status (manual)">
            <p className="mb-3 text-xs text-muted">Record the outcome you were told by the insurer/TPA. This app does not communicate with insurers or verify status.</p>
            <div className="grid gap-3 sm:grid-cols-3">
              <SelectField label="New status" value={status} onChange={(e) => setStatus(e.target.value)}>
                <option value="">Select…</option>{CLAIM_STATUSES.filter((s) => s !== c.status).map((s) => <option key={s} value={s}>{label(s)}</option>)}</SelectField>
              <Field label="Approved amount (₹)" type="number" min="0" value={approved} onChange={(e) => setApproved(e.target.value)} />
              <Field label="Note (optional)" value={statusNote} onChange={(e) => setStatusNote(e.target.value)} />
              <Field label="Insurer / TPA reference" value={insRef} onChange={(e) => setInsRef(e.target.value)} />
              {status.includes("rejected") && <Field label="Reason for rejection" value={reason} onChange={(e) => setReason(e.target.value)} />}
            </div>
            <div className="mt-3"><Button disabled={!status || changeStatus.isPending} onClick={() => changeStatus.mutate(
              { status, approved_amount: approved ? Number(approved) : null, note: statusNote || null, rejection_reason: reason || null, insurer_reference: insRef || null },
              { onSuccess: () => { toast("Status updated"); setStatus(""); setApproved(""); setStatusNote(""); setReason(""); setInsRef(""); }, onError: fail })}>Update status</Button></div>
          </Card>
          <Card title="Supporting documents" className="[&>div]:p-0">
            <div className="space-y-3 border-b border-line p-4">
              <div className="flex flex-wrap items-end gap-2">
                <div className="min-w-48 flex-1"><SelectField label="Attach an existing document" value={pick} onChange={(e) => setPick(e.target.value)}>
                  <option value="">Select…</option>{allDocs.data?.filter((d) => !attachedIds.has(d.id)).map((d) => <option key={d.id} value={d.id}>{d.original_name}</option>)}</SelectField></div>
                <Button variant="outline" disabled={!pick} onClick={() => attach.mutate(pick, { onSuccess: () => { toast("Document attached"); setPick(""); }, onError: fail })}><Paperclip size={14} />Attach</Button>
              </div>
              <UploadZone defaultCategory="hospital_bill" onUploaded={(docId) => attach.mutate(docId)} />
            </div>
            <DocumentTable docs={docs.data ?? []} extra={(d) => <Button variant="ghost" size="icon" aria-label={`Detach ${d.original_name}`} title="Detach from claim"
              onClick={() => detach.mutate(d.id, { onError: fail })}><X size={15} /></Button>} />
          </Card>
          <Card title="Linked medical records">{!records.data?.length ? <p className="text-sm text-muted">No records linked. Link records from the Medical Records page.</p> :
            <ul className="space-y-1.5 text-sm">{records.data.map((r) => <li key={r.id}>{r.title} <span className="text-muted">· {label(r.category)} · {fmtDate(r.record_date)}</span></li>)}</ul>}</Card>
        </div>
        <div className="space-y-4">
          <Card title="Add note"><TextArea label="Note" value={note} onChange={(e) => setNote(e.target.value)} />
            <Button className="mt-3" size="sm" disabled={!note.trim() || addNote.isPending}
              onClick={() => addNote.mutate(note.trim(), { onSuccess: () => { setNote(""); toast("Note added"); }, onError: fail })}><Check size={14} />Save note</Button></Card>
          <Card title="Status timeline & activity">{!activity.data?.length ? <EmptyState title="No activity yet" /> :
            <ol className="relative space-y-4 border-l border-line pl-4">{activity.data.map((a) => (
              <li key={a.id}><span className="absolute -left-[5px] mt-1.5 h-2.5 w-2.5 rounded-full border-2 border-surface bg-primary" />
                <p className="text-sm">{a.summary}</p>
                {typeof a.meta?.note === "string" && a.meta.note && a.action === "claim.status_changed" && <p className="text-xs text-muted">Note: {a.meta.note}</p>}
                <p className="text-xs text-muted">{fmtDateTime(a.created_at)}</p></li>))}</ol>}</Card>
        </div>
      </div>
      <Modal title="Edit claim" open={editing} onClose={() => setEditing(false)} wide><ClaimForm claim={c} onDone={() => setEditing(false)} /></Modal>
      <ConfirmDialog open={confirmDelete} title="Delete claim?" message={`Claim ${c.claim_ref} will be deleted. Attached documents are kept.`} busy={remove.isPending}
        onClose={() => setConfirmDelete(false)} onConfirm={async () => { await remove.mutateAsync(undefined); toast("Claim deleted"); navigate("/claims"); }} />
    </div>
  );
}
