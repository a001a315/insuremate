import { zodResolver } from "@hookform/resolvers/zod";
import { Pencil, Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Button } from "@/components/ui/Button";
import { Field, TextArea } from "@/components/ui/Field";
import { Badge, Card, ConfirmDialog, DataTable, EmptyState, ErrorNote, Modal, PageHeader, Spinner } from "@/components/ui/kit";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { del, patch, post, useApi, useEmpanelments } from "@/services/hooks";
import type { Empanelment } from "@/types";
import { fmtDate } from "@/utils/format";

const schema = z.object({ insurer: z.string().trim().min(1, "Insurer is required"), tpa_name: z.string(), cashless_enabled: z.boolean(), valid_until: z.string(), notes: z.string() });
type V = z.infer<typeof schema>;
const nul = (s: string) => (s.trim() === "" ? null : s.trim());

function EmpanelmentForm({ item, onDone }: { item?: Empanelment; onDone: () => void }) {
  const toast = useToast();
  const [error, setError] = useState<unknown>(null);
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<V>({ resolver: zodResolver(schema),
    defaultValues: { insurer: item?.insurer ?? "", tpa_name: item?.tpa_name ?? "", cashless_enabled: item?.cashless_enabled ?? true, valid_until: item?.valid_until ?? "", notes: item?.notes ?? "" } });
  const save = useApi((b: Record<string, unknown>) => item ? patch(`/hospital/empanelments/${item.id}`, b) : post("/hospital/empanelments", b), ["empanelments", "policies", "dashboard", "patients"]);
  const submit = handleSubmit(async (v) => {
    setError(null);
    try { await save.mutateAsync({ insurer: v.insurer.trim(), tpa_name: nul(v.tpa_name), cashless_enabled: v.cashless_enabled, valid_until: nul(v.valid_until), notes: nul(v.notes) }); toast("Saved"); onDone(); }
    catch (e) { setError(e); }
  });
  return (
    <form onSubmit={submit} className="space-y-4" noValidate>
      <Field label="Insurance company" error={errors.insurer?.message} {...register("insurer")} />
      <Field label="TPA name (optional)" {...register("tpa_name")} />
      <Field label="Empanelment valid until (optional)" type="date" {...register("valid_until")} />
      <label className="flex items-center gap-2 text-sm"><input type="checkbox" {...register("cashless_enabled")} />Cashless treatment available for this insurer</label>
      <TextArea label="Notes (optional)" {...register("notes")} />
      <ErrorNote error={error} />
      <div className="flex justify-end"><Button type="submit" disabled={isSubmitting}>{isSubmitting ? "Saving…" : "Save"}</Button></div>
    </form>
  );
}

export function HospitalPage() {
  const { user, refreshUser } = useAuth();
  const toast = useToast();
  const { data, isLoading, error } = useEmpanelments();
  const [editing, setEditing] = useState<Empanelment | "new" | null>(null);
  const [toDelete, setToDelete] = useState<Empanelment | null>(null);
  const [name, setName] = useState(user?.hospital_name ?? "");
  const [city, setCity] = useState(user?.hospital_city ?? "");
  const profile = useApi((b: Record<string, unknown>) => patch("/hospital/profile", b), []);
  const remove = useApi((id: string) => del(`/hospital/empanelments/${id}`), ["empanelments", "policies", "dashboard", "patients"]);
  const today = new Date().toISOString().slice(0, 10);

  return (
    <div>
      <PageHeader title="Hospital Setup" subtitle="The insurers and TPAs this hospital works with. Eligibility checks use this list to decide whether cashless treatment is likely."
        actions={<Button onClick={() => setEditing("new")}><Plus size={15} />Add insurer</Button>} />
      <Card title="Hospital profile" className="mb-4">
        <div className="grid items-end gap-3 sm:grid-cols-3">
          <Field label="Hospital name" value={name} onChange={(e) => setName(e.target.value)} />
          <Field label="City" value={city} onChange={(e) => setCity(e.target.value)} />
          <Button variant="outline" disabled={!name.trim() || profile.isPending}
            onClick={() => profile.mutate({ hospital_name: name.trim(), hospital_city: city.trim() || null }, { onSuccess: () => { refreshUser(); toast("Hospital profile saved"); }, onError: (e) => toast(e.message, "error") })}>Save profile</Button>
        </div>
      </Card>
      <ErrorNote error={error} />
      <Card title="Empanelled insurers & TPAs" className="[&>div]:p-0">
        {isLoading ? <div className="p-6"><Spinner /></div> : !data?.length ? (
          <EmptyState title="No insurers added yet" hint="Without this list every policy shows as 'Not empanelled' and eligibility results fall back to the reimbursement route."
            action={<Button onClick={() => setEditing("new")}>Add an insurer</Button>} />
        ) : (
          <DataTable head={["Insurer", "TPA", "Cashless", "Valid until", "Notes", ""]}>
            {data.map((e) => (
              <tr key={e.id}>
                <td className="px-3 py-2.5 font-medium">{e.insurer}</td><td className="px-3 py-2.5 text-muted">{e.tpa_name ?? "—"}</td>
                <td className="px-3 py-2.5"><Badge tone={e.cashless_enabled ? "success" : "neutral"}>{e.cashless_enabled ? "Cashless" : "Reimbursement only"}</Badge></td>
                <td className="px-3 py-2.5">{e.valid_until ? <span className={e.valid_until < today ? "text-danger" : ""}>{fmtDate(e.valid_until)}{e.valid_until < today && " (lapsed)"}</span> : <span className="text-muted">No end date</span>}</td>
                <td className="max-w-56 truncate px-3 py-2.5 text-muted">{e.notes ?? ""}</td>
                <td className="px-3 py-2.5 text-right">
                  <Button variant="ghost" size="icon" aria-label={`Edit ${e.insurer}`} onClick={() => setEditing(e)}><Pencil size={15} /></Button>
                  <Button variant="ghost" size="icon" aria-label={`Remove ${e.insurer}`} onClick={() => setToDelete(e)}><Trash2 size={15} /></Button></td>
              </tr>))}
          </DataTable>)}
      </Card>
      <Modal title={editing === "new" ? "Add insurer" : "Edit insurer"} open={!!editing} onClose={() => setEditing(null)}>
        <EmpanelmentForm key={editing === "new" ? "new" : (editing as Empanelment | null)?.id} item={editing && editing !== "new" ? editing : undefined} onDone={() => setEditing(null)} />
      </Modal>
      <ConfirmDialog open={!!toDelete} title="Remove insurer?" confirmLabel="Remove" busy={remove.isPending}
        message={`${toDelete?.insurer} will no longer count as empanelled. Existing policies are kept.`}
        onClose={() => setToDelete(null)} onConfirm={async () => { await remove.mutateAsync(toDelete!.id); toast("Insurer removed"); setToDelete(null); }} />
    </div>
  );
}
