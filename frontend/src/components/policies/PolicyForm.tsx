import { zodResolver } from "@hookform/resolvers/zod";
import { Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { useFieldArray, useForm } from "react-hook-form";
import { z } from "zod";
import { Button } from "@/components/ui/Button";
import { Field, SelectField, TextArea } from "@/components/ui/Field";
import { ErrorNote } from "@/components/ui/kit";
import { useToast } from "@/context/ToastContext";
import { patch, post, uploadDocument, useApi, usePatients } from "@/services/hooks";
import type { Policy } from "@/types";
import { DETAIL_LABELS, POLICY_TYPES, label } from "@/utils/format";

export const policySchema = z.object({
  patient_id: z.string().min(1, "Choose the patient"),
  tpa_name: z.string(),
  initial_waiting_days: z.string().refine((v) => v === "" || (Number(v) >= 0 && Number.isInteger(Number(v))), "Enter whole days"),
  name: z.string().trim().min(1, "Policy name is required"),
  insurer: z.string().trim().min(1, "Insurance company is required"),
  policy_number: z.string().trim().min(1, "Policy number is required"),
  policy_type: z.string(),
  policyholder_name: z.string().trim().min(1, "Policyholder name is required"),
  sum_insured: z.string().refine((v) => v !== "" && Number(v) >= 0, "Enter a valid amount"),
  premium_amount: z.string().refine((v) => v === "" || Number(v) >= 0, "Enter a valid amount"),
  premium_frequency: z.string(),
  start_date: z.string(), expiry_date: z.string(), renewal_date: z.string(),
  nominee_name: z.string(), nominee_relationship: z.string(),
  details: z.record(z.string(), z.string()),
  members: z.array(z.object({ name: z.string().trim().min(1, "Name required"), relationship_to_holder: z.string() })),
}).refine((v) => !v.start_date || !v.expiry_date || v.expiry_date >= v.start_date, { path: ["expiry_date"], message: "Expiry must be after the start date" });
export type PolicyFormValues = z.infer<typeof policySchema>;

const nullIfEmpty = (s: string) => (s === "" ? null : s);

export function PolicyForm({ policy, patientId, onDone }: { policy?: Policy; patientId?: string; onDone: (id: string) => void }) {
  const toast = useToast();
  const patients = usePatients();
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<unknown>(null);
  const { register, control, handleSubmit, formState: { errors, isSubmitting } } = useForm<PolicyFormValues>({
    resolver: zodResolver(policySchema),
    defaultValues: {
      patient_id: policy?.patient_id ?? patientId ?? "", tpa_name: policy?.tpa_name ?? "",
      initial_waiting_days: policy ? String(policy.initial_waiting_days) : "30",
      name: policy?.name ?? "", insurer: policy?.insurer ?? "", policy_number: policy?.policy_number ?? "",
      policy_type: policy?.policy_type ?? "individual", policyholder_name: policy?.policyholder_name ?? "",
      sum_insured: policy ? String(policy.sum_insured) : "", premium_amount: policy ? String(policy.premium_amount) : "",
      premium_frequency: policy?.premium_frequency ?? "annual", start_date: policy?.start_date ?? "",
      expiry_date: policy?.expiry_date ?? "", renewal_date: policy?.renewal_date ?? "",
      nominee_name: policy?.nominee?.name ?? "", nominee_relationship: policy?.nominee?.relationship ?? "",
      details: Object.fromEntries(Object.keys(DETAIL_LABELS).map((k) => [k, policy?.details[k]?.value ?? ""])),
      members: policy?.members.map((m) => ({ name: m.name, relationship_to_holder: m.relationship_to_holder })) ?? [{ name: "", relationship_to_holder: "self" }],
    },
  });
  const { fields, append, remove } = useFieldArray({ control, name: "members" });
  const save = useApi(async (p: { id?: string; body: Record<string, unknown> }) =>
    p.id ? patch<Policy>(`/policies/${p.id}`, p.body) : post<Policy>("/policies", p.body), ["policies", "policy", "dashboard", "patients"]);

  const onSubmit = handleSubmit(async (v) => {
    setError(null);
    // Only fields the user actually changed are marked as manual, so extracted values keep their source.
    const details: Record<string, { value: string; source: "manual" }> = {};
    for (const [k, val] of Object.entries(v.details)) if (val.trim() && val !== (policy?.details[k]?.value ?? "")) details[k] = { value: val.trim(), source: "manual" };
    const body = {
      patient_id: v.patient_id, tpa_name: nullIfEmpty(v.tpa_name.trim()), initial_waiting_days: Number(v.initial_waiting_days || 30),
      name: v.name, insurer: v.insurer, policy_number: v.policy_number, policy_type: v.policy_type, policyholder_name: v.policyholder_name,
      sum_insured: Number(v.sum_insured), premium_amount: Number(v.premium_amount || 0), premium_frequency: v.premium_frequency,
      start_date: nullIfEmpty(v.start_date), expiry_date: nullIfEmpty(v.expiry_date), renewal_date: nullIfEmpty(v.renewal_date),
      nominee: v.nominee_name ? { name: v.nominee_name, relationship: v.nominee_relationship } : null,
      details, members: v.members,
    };
    try {
      const saved = await save.mutateAsync({ id: policy?.id, body });
      if (file) {
        try { await uploadDocument(file, "policy_document", saved.id); }
        catch (e) { toast(`Policy saved, but the document upload failed: ${e instanceof Error ? e.message : ""}`, "error"); }
      }
      toast(policy ? "Policy updated" : "Policy added");
      onDone(saved.id);
    } catch (e) { setError(e); }
  });

  return (
    <form onSubmit={onSubmit} className="space-y-5" noValidate>
      <div className="grid gap-4 sm:grid-cols-2">
        <SelectField label="Patient" error={errors.patient_id?.message} {...register("patient_id")}>
          <option value="">Select a patient…</option>{patients.data?.map((p) => <option key={p.id} value={p.id}>{p.full_name}{p.mrn ? ` (${p.mrn})` : ""}</option>)}</SelectField>
        <Field label="TPA name (optional)" {...register("tpa_name")} />
        <Field label="Policy name" error={errors.name?.message} {...register("name")} />
        <Field label="Insurance company" error={errors.insurer?.message} {...register("insurer")} />
        <Field label="Policy number" error={errors.policy_number?.message} {...register("policy_number")} />
        <SelectField label="Policy type" {...register("policy_type")}>{POLICY_TYPES.map((t) => <option key={t} value={t}>{label(t)}</option>)}</SelectField>
        <Field label="Policyholder name" error={errors.policyholder_name?.message} {...register("policyholder_name")} />
        <Field label="Sum insured (₹)" type="number" min="0" error={errors.sum_insured?.message} {...register("sum_insured")} />
        <Field label="Premium amount (₹)" type="number" min="0" error={errors.premium_amount?.message} {...register("premium_amount")} />
        <SelectField label="Premium frequency" {...register("premium_frequency")}>
          {["monthly", "quarterly", "half_yearly", "annual"].map((t) => <option key={t} value={t}>{label(t)}</option>)}</SelectField>
        <Field label="Start date" type="date" {...register("start_date")} />
        <Field label="Expiration date" type="date" error={errors.expiry_date?.message} {...register("expiry_date")} />
        <Field label="Renewal date" type="date" {...register("renewal_date")} />
        <Field label="Initial waiting period (days)" type="number" min="0" error={errors.initial_waiting_days?.message} {...register("initial_waiting_days")} />
        <Field label="Nominee name" {...register("nominee_name")} />
        <Field label="Nominee relationship" {...register("nominee_relationship")} />
      </div>
      <fieldset>
        <legend className="mb-2 text-sm font-semibold">Insured members</legend>
        <div className="space-y-2">
          {fields.map((f, i) => (
            <div key={f.id} className="flex items-end gap-2">
              <div className="flex-1"><Field label={i === 0 ? "Name" : "Name "} error={errors.members?.[i]?.name?.message} {...register(`members.${i}.name`)} /></div>
              <div className="w-36"><Field label="Relationship" {...register(`members.${i}.relationship_to_holder`)} /></div>
              <Button type="button" variant="ghost" size="icon" aria-label="Remove member" onClick={() => remove(i)}><Trash2 size={15} /></Button>
            </div>
          ))}
          <Button type="button" variant="outline" size="sm" onClick={() => append({ name: "", relationship_to_holder: "" })}><Plus size={14} />Add member</Button>
        </div>
      </fieldset>
      <fieldset>
        <legend className="mb-1 text-sm font-semibold">Policy conditions <span className="font-normal text-muted">(optional, as read from the policy)</span></legend>
        <div className="grid gap-4 sm:grid-cols-2">
          {Object.entries(DETAIL_LABELS).map(([k, l]) => <TextArea key={k} label={l} rows={2} {...register(`details.${k}`)} />)}
        </div>
      </fieldset>
      <div>
        <label className="text-sm font-medium" htmlFor="policy-file">Policy document <span className="font-normal text-muted">(optional — indexed for the AI assistant)</span></label>
        <input id="policy-file" type="file" accept=".pdf,.docx,.png,.jpg,.jpeg" className="mt-1.5 block text-sm" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
      </div>
      <ErrorNote error={error} />
      <div className="flex justify-end"><Button type="submit" disabled={isSubmitting}>{isSubmitting ? "Saving…" : policy ? "Save changes" : "Add policy"}</Button></div>
    </form>
  );
}
