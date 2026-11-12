import { AlertTriangle, CheckCircle2, CircleHelp, Info, XCircle } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Badge, Card, ErrorNote } from "@/components/ui/kit";
import { post, useApi } from "@/services/hooks";
import type { EligibilityCheck, EligibilityResult } from "@/types";

const ICON: Record<EligibilityCheck["status"], { icon: typeof Info; cls: string; text: string }> = {
  pass: { icon: CheckCircle2, cls: "text-success", text: "Passed" }, fail: { icon: XCircle, cls: "text-danger", text: "Failed" },
  warn: { icon: AlertTriangle, cls: "text-warning", text: "Check" }, info: { icon: Info, cls: "text-primary", text: "Note" },
  unknown: { icon: CircleHelp, cls: "text-muted", text: "Unknown" },
};
const VERDICT_TONE = { eligible_cashless: "success", eligible_reimbursement: "info", needs_review: "warning", not_eligible: "danger" } as const;

export function EligibilityPanel({ patientId, hasPolicies }: { patientId: string; hasPolicies: boolean }) {
  const [admission, setAdmission] = useState(new Date().toISOString().slice(0, 10));
  const [amount, setAmount] = useState("");
  const [treatment, setTreatment] = useState("");
  const [emergency, setEmergency] = useState(false);
  const run = useApi((b: Record<string, unknown>) => post<EligibilityResult[]>(`/patients/${patientId}/eligibility`, b), []);

  return (
    <Card title="Eligibility check at this hospital">
      <p className="mb-3 text-xs text-muted">Compares the recorded policy details and claims with this hospital&apos;s empanelment list. It is an advisory pre-check, not an insurer approval.</p>
      <div className="grid gap-3 sm:grid-cols-4">
        <Field label="Admission date" type="date" value={admission} onChange={(e) => setAdmission(e.target.value)} />
        <Field label="Estimated amount (₹)" type="number" min="0" value={amount} onChange={(e) => setAmount(e.target.value)} />
        <div className="sm:col-span-2"><Field label="Planned treatment (optional)" value={treatment} onChange={(e) => setTreatment(e.target.value)} placeholder="e.g. cataract surgery" /></div>
      </div>
      <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={emergency} onChange={(e) => setEmergency(e.target.checked)} />Emergency / accident admission</label>
        <Button disabled={!hasPolicies || run.isPending}
          onClick={() => run.mutate({ admission_date: admission || null, estimated_amount: amount ? Number(amount) : null, treatment: treatment || null, is_emergency_or_accident: emergency })}>
          {run.isPending ? "Checking…" : "Check eligibility"}</Button>
      </div>
      {!hasPolicies && <p className="mt-2 text-sm text-muted">Add a policy for this patient to run a check.</p>}
      <div className="mt-3"><ErrorNote error={run.error} /></div>
      <div className="mt-4 space-y-4">
        {run.data?.length === 0 && <p className="text-sm text-muted">No policies to check.</p>}
        {run.data?.map((r) => (
          <div key={r.policy_id} className="rounded-lg border border-line" data-testid="eligibility-result">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line bg-canvas px-4 py-3">
              <div><p className="text-sm font-medium">{r.policy_name}</p><p className="text-xs text-muted">{r.insurer}</p></div>
              <Badge tone={VERDICT_TONE[r.verdict]}>{r.verdict_label}</Badge>
            </div>
            <ul className="divide-y divide-line">
              {r.checks.map((c) => { const I = ICON[c.status]; return (
                <li key={c.key} className="flex gap-3 px-4 py-2.5 text-sm">
                  <I.icon size={16} className={`mt-0.5 shrink-0 ${I.cls}`} aria-label={I.text} />
                  <div><p className="font-medium">{c.label}</p><p className="text-muted">{c.detail}</p>
                    <p className="mt-0.5 text-[11px] text-muted">{c.source === "hospital_setup" ? "Source: hospital empanelment setup" : "Source: recorded policy data"}</p></div>
                </li>); })}
            </ul>
            <p className="border-t border-line px-4 py-2 text-xs text-muted">{r.disclaimer}</p>
          </div>))}
      </div>
    </Card>
  );
}
