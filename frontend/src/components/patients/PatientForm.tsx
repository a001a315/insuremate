import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Button } from "@/components/ui/Button";
import { Field, SelectField, TextArea } from "@/components/ui/Field";
import { ErrorNote } from "@/components/ui/kit";
import { useToast } from "@/context/ToastContext";
import { patch, post, useApi } from "@/services/hooks";
import type { Patient } from "@/types";

export const patientSchema = z.object({
  full_name: z.string().trim().min(1, "Patient name is required"),
  mrn: z.string(), date_of_birth: z.string(), gender: z.string(), phone: z.string(), notes: z.string(),
});
type Values = z.infer<typeof patientSchema>;
const nul = (s: string) => (s.trim() === "" ? null : s.trim());

export function PatientForm({ patient, onDone }: { patient?: Patient; onDone: (id: string) => void }) {
  const toast = useToast();
  const [error, setError] = useState<unknown>(null);
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<Values>({
    resolver: zodResolver(patientSchema),
    defaultValues: { full_name: patient?.full_name ?? "", mrn: patient?.mrn ?? "", date_of_birth: patient?.date_of_birth ?? "",
      gender: patient?.gender ?? "", phone: patient?.phone ?? "", notes: patient?.notes ?? "" },
  });
  const save = useApi((b: Record<string, unknown>) => patient ? patch<Patient>(`/patients/${patient.id}`, b) : post<Patient>("/patients", b),
    ["patients", "patient", "dashboard"]);
  const onSubmit = handleSubmit(async (v) => {
    setError(null);
    try {
      const p = await save.mutateAsync({ full_name: v.full_name.trim(), mrn: nul(v.mrn), date_of_birth: nul(v.date_of_birth), gender: nul(v.gender), phone: nul(v.phone), notes: nul(v.notes) });
      toast(patient ? "Patient updated" : "Patient registered");
      onDone(p.id);
    } catch (e) { setError(e); }
  });
  return (
    <form onSubmit={onSubmit} className="space-y-4" noValidate>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Patient name" error={errors.full_name?.message} {...register("full_name")} />
        <Field label="MRN / patient ID (optional)" {...register("mrn")} />
        <Field label="Date of birth" type="date" {...register("date_of_birth")} />
        <SelectField label="Gender" {...register("gender")}><option value="">Not recorded</option><option value="female">Female</option><option value="male">Male</option><option value="other">Other</option></SelectField>
        <Field label="Phone" {...register("phone")} />
      </div>
      <TextArea label="Notes" {...register("notes")} />
      <ErrorNote error={error} />
      <div className="flex justify-end"><Button type="submit" disabled={isSubmitting}>{isSubmitting ? "Saving…" : patient ? "Save changes" : "Register patient"}</Button></div>
    </form>
  );
}
