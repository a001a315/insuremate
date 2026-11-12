import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Button } from "@/components/ui/Button";
import { Field, SelectField, TextArea } from "@/components/ui/Field";
import { ErrorNote } from "@/components/ui/kit";
import { useToast } from "@/context/ToastContext";
import { patch, post, useApi, usePatients, usePolicies } from "@/services/hooks";
import type { Claim } from "@/types";
import { CLAIM_STATUSES, label } from "@/utils/format";

export const claimSchema = z.object({
  policy_id: z.string().min(1, "Choose a policy"),
  patient_id: z.string().min(1, "Choose the patient"),
  insurer_reference: z.string(),
  hospital_name: z.string(), hospitalization_date: z.string(), discharge_date: z.string(),
  claim_amount: z.string().refine((v) => v === "" || Number(v) >= 0, "Enter a valid amount"),
  claim_type: z.string(), status: z.string(), submission_date: z.string(), notes: z.string(),
}).refine((v) => !v.hospitalization_date || !v.discharge_date || v.discharge_date >= v.hospitalization_date,
  { path: ["discharge_date"], message: "Discharge date cannot be before hospitalization date" });
type Values = z.infer<typeof claimSchema>;
const nul = (s: string) => (s === "" ? null : s);

export function ClaimForm({ claim, defaultPolicyId, defaultPatientId, onDone }: { claim?: Claim; defaultPolicyId?: string; defaultPatientId?: string; onDone: (id: string) => void }) {
  const toast = useToast();
  const patients = usePatients();
  const [error, setError] = useState<unknown>(null);
  const { register, handleSubmit, watch, formState: { errors, isSubmitting } } = useForm<Values>({
    resolver: zodResolver(claimSchema),
    defaultValues: { policy_id: claim?.policy_id ?? defaultPolicyId ?? "", patient_id: claim?.patient_id ?? defaultPatientId ?? "", insurer_reference: claim?.insurer_reference ?? "", hospital_name: claim?.hospital_name ?? "",
      hospitalization_date: claim?.hospitalization_date ?? "", discharge_date: claim?.discharge_date ?? "", claim_amount: claim ? String(claim.claim_amount) : "",
      claim_type: claim?.claim_type ?? "reimbursement", status: claim?.status ?? "draft", submission_date: claim?.submission_date ?? "", notes: claim?.notes ?? "" },
  });
  const patientId = watch("patient_id");
  const policies = usePolicies(false, patientId || undefined);
  const save = useApi((b: Record<string, unknown>) => claim ? patch<Claim>(`/claims/${claim.id}`, b) : post<Claim>("/claims", b),
    ["claims", "claim", "claim-activity", "dashboard", "patients"]);

  const onSubmit = handleSubmit(async (v) => {
    setError(null);
    const common = { insurer_reference: nul(v.insurer_reference), hospital_name: nul(v.hospital_name), hospitalization_date: nul(v.hospitalization_date),
      discharge_date: nul(v.discharge_date), claim_amount: Number(v.claim_amount || 0), claim_type: v.claim_type,
      submission_date: nul(v.submission_date), notes: nul(v.notes) };
    try {
      const c = await save.mutateAsync(claim ? common : { ...common, policy_id: v.policy_id, patient_id: v.patient_id, status: v.status });
      toast(claim ? "Claim updated" : "Claim created");
      onDone(c.id);
    } catch (e) { setError(e); }
  });

  return (
    <form onSubmit={onSubmit} className="space-y-4" noValidate>
      <div className="grid gap-4 sm:grid-cols-2">
        <SelectField label="Patient" disabled={!!claim} error={errors.patient_id?.message} {...register("patient_id")}>
          <option value="">Select a patient…</option>{patients.data?.map((p) => <option key={p.id} value={p.id}>{p.full_name}{p.mrn ? ` (${p.mrn})` : ""}</option>)}</SelectField>
        <SelectField label="Policy" disabled={!!claim || !patientId} error={errors.policy_id?.message} {...register("policy_id")}>
          <option value="">{patientId ? "Select the patient's policy…" : "Choose a patient first"}</option>{policies.data?.map((p) => <option key={p.id} value={p.id}>{p.name} · {p.insurer}</option>)}</SelectField>
        <Field label="Insurer / TPA reference (optional)" {...register("insurer_reference")} />
        <Field label="Hospital name" {...register("hospital_name")} />
        <SelectField label="Claim type" {...register("claim_type")}><option value="reimbursement">Reimbursement</option><option value="cashless">Cashless</option></SelectField>
        <Field label="Hospitalization date" type="date" {...register("hospitalization_date")} />
        <Field label="Discharge date" type="date" error={errors.discharge_date?.message} {...register("discharge_date")} />
        <Field label="Claim amount (₹)" type="number" min="0" error={errors.claim_amount?.message} {...register("claim_amount")} />
        <Field label="Submission date" type="date" {...register("submission_date")} />
        {!claim && <SelectField label="Status" {...register("status")}>{CLAIM_STATUSES.map((s) => <option key={s} value={s}>{label(s)}</option>)}</SelectField>}
      </div>
      <TextArea label="Notes" {...register("notes")} />
      <ErrorNote error={error} />
      <div className="flex justify-end"><Button type="submit" disabled={isSubmitting}>{isSubmitting ? "Saving…" : claim ? "Save changes" : "Create claim"}</Button></div>
    </form>
  );
}
