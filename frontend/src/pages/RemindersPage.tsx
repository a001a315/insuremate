import { zodResolver } from "@hookform/resolvers/zod";
import { Check, Plus, RefreshCw, Trash2 } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Button } from "@/components/ui/Button";
import { Field, SelectField, TextArea } from "@/components/ui/Field";
import { Badge, Card, EmptyState, ErrorNote, Modal, PageHeader, Spinner } from "@/components/ui/kit";
import { useToast } from "@/context/ToastContext";
import { del, patch, post, useApi, useReminders } from "@/services/hooks";
import type { Reminder } from "@/types";
import { fmtDate, label } from "@/utils/format";

const schema = z.object({ title: z.string().trim().min(1, "Title is required"), kind: z.string(), due_date: z.string().min(1, "Choose a due date"), description: z.string() });
type V = z.infer<typeof schema>;

function ReminderForm({ reminder, onDone }: { reminder?: Reminder; onDone: () => void }) {
  const [error, setError] = useState<unknown>(null);
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<V>({ resolver: zodResolver(schema),
    defaultValues: { title: reminder?.title ?? "", kind: reminder?.kind ?? "custom", due_date: reminder?.due_date ?? "", description: reminder?.description ?? "" } });
  const save = useApi((b: Record<string, unknown>) => reminder ? patch(`/reminders/${reminder.id}`, b) : post("/reminders", b), ["reminders", "notifications"]);
  return (
    <form className="space-y-4" noValidate onSubmit={handleSubmit(async (v) => {
      setError(null);
      try { await save.mutateAsync(reminder ? { title: v.title, due_date: v.due_date, description: v.description || null } : { ...v, description: v.description || null }); onDone(); } catch (e) { setError(e); }
    })}>
      <Field label="Title" error={errors.title?.message} {...register("title")} />
      <div className="grid gap-4 sm:grid-cols-2">
        {!reminder && <SelectField label="Type" {...register("kind")}><option value="custom">Custom</option><option value="premium">Premium payment</option>
          <option value="renewal">Policy renewal</option><option value="claim_documents">Missing claim documents</option><option value="claim_followup">Claim follow-up</option></SelectField>}
        <Field label="Due date" type="date" error={errors.due_date?.message} {...register("due_date")} />
      </div>
      <TextArea label="Description (optional)" {...register("description")} />
      <ErrorNote error={error} />
      <div className="flex justify-end"><Button type="submit" disabled={isSubmitting}>{reminder ? "Save changes" : "Create reminder"}</Button></div>
    </form>
  );
}

export function RemindersPage() {
  const toast = useToast();
  const { data, isLoading, error } = useReminders();
  const [editing, setEditing] = useState<Reminder | "new" | null>(null);
  const toggle = useApi((r: Reminder) => patch(`/reminders/${r.id}`, { is_completed: !r.is_completed }), ["reminders"]);
  const remove = useApi((id: string) => del(`/reminders/${id}`), ["reminders"]);
  const check = useApi(() => post<{ reminders_created: number; notifications_created: number }>("/reminders/run-checks"), ["reminders", "notifications"]);
  const today = new Date().toISOString().slice(0, 10);
  const open = data?.filter((r) => !r.is_completed) ?? []; const done = data?.filter((r) => r.is_completed) ?? [];

  const row = (r: Reminder) => (
    <li key={r.id} className="flex items-center gap-3 py-2.5">
      <button aria-label={r.is_completed ? `Mark ${r.title} as not completed` : `Mark ${r.title} as completed`} onClick={() => toggle.mutate(r)}
        className={`flex h-5 w-5 shrink-0 items-center justify-center rounded border ${r.is_completed ? "border-success bg-success text-white" : "border-line hover:border-primary"}`}>{r.is_completed && <Check size={13} />}</button>
      <button className="min-w-0 flex-1 text-left" onClick={() => setEditing(r)}>
        <p className={`truncate text-sm ${r.is_completed ? "text-muted line-through" : "font-medium"}`}>{r.title}</p>
        {r.description && <p className="truncate text-xs text-muted">{r.description}</p>}</button>
      <Badge>{label(r.kind)}</Badge>{r.is_auto && <Badge tone="info">Auto</Badge>}
      <span className={`w-24 text-right text-xs ${!r.is_completed && r.due_date < today ? "font-medium text-danger" : "text-muted"}`}>{fmtDate(r.due_date)}</span>
      <Button variant="ghost" size="icon" aria-label={`Delete ${r.title}`} onClick={() => remove.mutate(r.id, { onSuccess: () => toast("Reminder deleted") })}><Trash2 size={15} /></Button>
    </li>);

  return (
    <div>
      <PageHeader title="Reminders" subtitle="In-app only. This app does not send emails or SMS."
        actions={<><Button variant="outline" size="sm" disabled={check.isPending} onClick={() => check.mutate(undefined, { onSuccess: (r) => toast(`Checked: ${r.reminders_created} new reminder(s), ${r.notifications_created} notification(s)`) })}><RefreshCw size={14} />Check now</Button>
          <Button onClick={() => setEditing("new")}><Plus size={15} />New reminder</Button></>} />
      <p className="mb-4 text-xs text-muted">Renewal, missing-document and follow-up reminders are created automatically from the dates and statuses you have recorded.</p>
      <ErrorNote error={error} />
      {isLoading ? <Spinner /> : !data?.length ? <Card><EmptyState title="No reminders" hint="Create one, or add policies and claims to get automatic reminders." /></Card> : <>
        <Card title={`Upcoming (${open.length})`}>{open.length ? <ul className="divide-y divide-line">{open.map(row)}</ul> : <p className="text-sm text-muted">Nothing pending.</p>}</Card>
        {done.length > 0 && <Card title={`Completed (${done.length})`} className="mt-4"><ul className="divide-y divide-line">{done.map(row)}</ul></Card>}</>}
      <Modal title={editing === "new" ? "New reminder" : "Edit reminder"} open={!!editing} onClose={() => setEditing(null)}>
        {editing && <ReminderForm key={editing === "new" ? "new" : editing.id} reminder={editing === "new" ? undefined : editing} onDone={() => { setEditing(null); toast("Saved"); }} />}</Modal>
    </div>
  );
}
