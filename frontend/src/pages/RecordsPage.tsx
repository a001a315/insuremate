import { zodResolver } from "@hookform/resolvers/zod";
import { Download, Eye, Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link } from "react-router-dom";
import { z } from "zod";
import { Button } from "@/components/ui/Button";
import { Field, SelectField, TextArea } from "@/components/ui/Field";
import { Badge, Card, ConfirmDialog, EmptyState, ErrorNote, Modal, PageHeader, Spinner } from "@/components/ui/kit";
import { useToast } from "@/context/ToastContext";
import { del, openFile, post, uploadDocument, useApi, useClaims, usePatients, usePolicies, useRecords } from "@/services/hooks";
import type { MedicalRecord } from "@/types";
import { RECORD_CATEGORIES, fmtDate, label } from "@/utils/format";

const schema = z.object({
  title: z.string().trim().min(1, "Title is required"), category: z.string(), patient_id: z.string().min(1, "Choose the patient"),
  provider: z.string(), record_date: z.string(), claim_id: z.string(), policy_id: z.string(), notes: z.string(),
});
type V = z.infer<typeof schema>;
const nul = (s: string) => (s === "" ? null : s);

function RecordForm({ onDone }: { onDone: () => void }) {
  const toast = useToast();
  const claims = useClaims();
  const patients = usePatients();
  const policies = usePolicies();
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<unknown>(null);
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<V>({ resolver: zodResolver(schema),
    defaultValues: { title: "", category: "discharge_summary", patient_id: "", provider: "", record_date: "", claim_id: "", policy_id: "", notes: "" } });
  const create = useApi((b: Record<string, unknown>) => post("/records", b), ["records", "dashboard"]);
  const submit = handleSubmit(async (v) => {
    setError(null);
    try {
      let document_id: string | null = null;
      if (file) document_id = (await uploadDocument(file, v.category === "medical_bill" ? "hospital_bill" : v.category === "discharge_summary" ? "discharge_summary" : "medical_report")).id;
      await create.mutateAsync({ title: v.title, category: v.category, patient_id: v.patient_id, provider: nul(v.provider), record_date: nul(v.record_date),
        claim_id: nul(v.claim_id), policy_id: nul(v.policy_id), notes: nul(v.notes), document_id });
      toast("Record added"); onDone();
    } catch (e) { setError(e); }
  });
  return (
    <form onSubmit={submit} className="space-y-4" noValidate>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Document title" error={errors.title?.message} {...register("title")} />
        <SelectField label="Category" {...register("category")}>{RECORD_CATEGORIES.map((c) => <option key={c} value={c}>{label(c)}</option>)}</SelectField>
        <SelectField label="Patient" error={errors.patient_id?.message} {...register("patient_id")}><option value="">Select a patient…</option>{patients.data?.map((p) => <option key={p.id} value={p.id}>{p.full_name}</option>)}</SelectField>
        <Field label="Hospital or doctor" {...register("provider")} />
        <Field label="Record date" type="date" {...register("record_date")} />
        <div />
        <SelectField label="Associated claim" {...register("claim_id")}><option value="">None</option>{claims.data?.map((c) => <option key={c.id} value={c.id}>{c.claim_ref}</option>)}</SelectField>
        <SelectField label="Associated policy" {...register("policy_id")}><option value="">None</option>{policies.data?.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}</SelectField>
      </div>
      <div><label htmlFor="rec-file" className="text-sm font-medium">File attachment</label>
        <input id="rec-file" type="file" accept=".pdf,.docx,.png,.jpg,.jpeg" className="mt-1.5 block text-sm" onChange={(e) => setFile(e.target.files?.[0] ?? null)} /></div>
      <TextArea label="Notes (optional)" {...register("notes")} />
      <ErrorNote error={error} />
      <div className="flex justify-end"><Button type="submit" disabled={isSubmitting}>{isSubmitting ? "Saving…" : "Add record"}</Button></div>
    </form>
  );
}

export function RecordsPage() {
  const toast = useToast();
  const [q, setQ] = useState(""); const [category, setCategory] = useState(""); const [from, setFrom] = useState(""); const [to, setTo] = useState("");
  const [adding, setAdding] = useState(false);
  const [toDelete, setToDelete] = useState<MedicalRecord | null>(null);
  const { data, isLoading, error } = useRecords({ q: q || undefined, category: category || undefined, date_from: from || undefined, date_to: to || undefined });
  const claims = useClaims();
  const remove = useApi((id: string) => del(`/records/${id}`), ["records"]);
  const claimRef = (id: string | null) => claims.data?.find((c) => c.id === id);
  const years = [...new Set((data ?? []).map((r) => (r.record_date ?? "Undated").slice(0, 4)))];

  return (
    <div>
      <PageHeader title="Medical Records" subtitle="Patient records stored by this hospital, newest first."
        actions={<Button onClick={() => setAdding(true)}><Plus size={15} />Add record</Button>} />
      <Card className="mb-4"><div className="grid gap-3 sm:grid-cols-4">
        <Field label="Search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Title, patient, doctor…" />
        <SelectField label="Category" value={category} onChange={(e) => setCategory(e.target.value)}><option value="">All</option>{RECORD_CATEGORIES.map((c) => <option key={c} value={c}>{label(c)}</option>)}</SelectField>
        <Field label="From" type="date" value={from} onChange={(e) => setFrom(e.target.value)} />
        <Field label="To" type="date" value={to} onChange={(e) => setTo(e.target.value)} />
      </div></Card>
      <ErrorNote error={error} />
      {isLoading ? <Spinner /> : !data?.length ? <Card><EmptyState title="No records found" hint="Add discharge summaries, prescriptions, reports and bills to build the patient history." action={<Button onClick={() => setAdding(true)}>Add record</Button>} /></Card> :
        years.map((y) => (
          <div key={y} className="mb-5"><h2 className="mb-2 text-sm font-semibold text-muted">{y}</h2>
            <div className="space-y-2">{data.filter((r) => (r.record_date ?? "Undated").slice(0, 4) === y).map((r) => {
              const cl = claimRef(r.claim_id);
              return (
                <div key={r.id} className="flex flex-wrap items-center gap-3 rounded-lg border border-line bg-surface px-4 py-3">
                  <div className="w-24 shrink-0 text-xs text-muted">{fmtDate(r.record_date)}</div>
                  <div className="min-w-0 flex-1"><p className="truncate text-sm font-medium">{r.title}</p>
                    <p className="truncate text-xs text-muted">{r.patient_name}{r.provider ? ` · ${r.provider}` : ""}</p></div>
                  <Badge>{label(r.category)}</Badge>
                  {cl && <Link to={`/claims/${cl.id}`}><Badge tone="info">{cl.claim_ref}</Badge></Link>}
                  <div className="flex">
                    {r.document_id && <><Button variant="ghost" size="icon" aria-label={`Preview ${r.title}`} onClick={() => openFile(r.document_id!, r.title, "preview").catch((e) => toast(e.message, "error"))}><Eye size={15} /></Button>
                      <Button variant="ghost" size="icon" aria-label={`Download ${r.title}`} onClick={() => openFile(r.document_id!, r.title, "download").catch((e) => toast(e.message, "error"))}><Download size={15} /></Button></>}
                    <Button variant="ghost" size="icon" aria-label={`Delete ${r.title}`} onClick={() => setToDelete(r)}><Trash2 size={15} /></Button></div>
                </div>);
            })}</div></div>))}
      <Modal title="Add medical record" open={adding} onClose={() => setAdding(false)} wide><RecordForm onDone={() => setAdding(false)} /></Modal>
      <ConfirmDialog open={!!toDelete} title="Delete record?" message={`"${toDelete?.title}" will be removed. Its attached file stays in Documents.`} busy={remove.isPending}
        onClose={() => setToDelete(null)} onConfirm={async () => { await remove.mutateAsync(toDelete!.id); toast("Record deleted"); setToDelete(null); }} />
    </div>
  );
}
