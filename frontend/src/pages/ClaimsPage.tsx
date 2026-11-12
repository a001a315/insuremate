import { Plus } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ClaimForm } from "@/components/claims/ClaimForm";
import { Button } from "@/components/ui/Button";
import { Card, ClearanceBadge, DataTable, EmptyState, ErrorNote, Modal, PageHeader, Spinner, StatusBadge } from "@/components/ui/kit";
import { useClaims, usePolicies } from "@/services/hooks";
import { CLAIM_STATUSES, fmtDate, inr, label } from "@/utils/format";

export function ClaimsPage() {
  const [status, setStatus] = useState("");
  const [adding, setAdding] = useState(false);
  const navigate = useNavigate();
  const { data, isLoading, error } = useClaims({ status: status || undefined });
  const all = useClaims();
  const policies = usePolicies(true);
  const pname = (id: string) => policies.data?.find((p) => p.id === id)?.name ?? "—";
  const count = (s: string[]) => all.data?.filter((c) => s.includes(c.clearance)).length ?? 0;

  return (
    <div>
      <PageHeader title="Claims" subtitle="Pre-authorisations and claims for your patients. Statuses are recorded by your team; this app does not contact insurers."
        actions={<Button onClick={() => setAdding(true)}><Plus size={15} />New claim</Button>} />
      <div className="mb-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
        {[["Total claims", all.data?.length ?? 0], ["Pending", count(["pending"])],
          ["Cleared", count(["cleared", "pre_auth_cleared"])], ["Rejected", count(["rejected"])]].map(([l, v]) => (
          <div key={l as string} className="rounded-lg border border-line bg-surface p-4"><p className="text-xs text-muted">{l}</p><p className="mt-1 text-xl font-semibold">{v}</p></div>))}
      </div>
      <ErrorNote error={error} />
      <Card title="All claims" action={<select aria-label="Filter by status" value={status} onChange={(e) => setStatus(e.target.value)}
        className="h-8 rounded-md border border-line bg-surface px-2 text-sm"><option value="">All statuses</option>
        {CLAIM_STATUSES.map((s) => <option key={s} value={s}>{label(s)}</option>)}</select>} className="[&>div]:p-0">
        {isLoading ? <div className="p-6"><Spinner /></div> : !data?.length ? (
          <EmptyState title="No claims found" hint="Create a claim to start tracking it." action={<Button onClick={() => setAdding(true)}>New claim</Button>} />
        ) : (
          <DataTable head={["Claim ID", "Patient", "Policy", "Claimed", "Approved", "Submitted", "Status", "Clearance"]}>
            {data.map((c) => (
              <tr key={c.id} className="hover:bg-canvas/60">
                <td className="px-3 py-2.5"><Link className="font-medium text-primary hover:underline" to={`/claims/${c.id}`}>{c.claim_ref}</Link></td>
                <td className="px-3 py-2.5"><Link className="hover:text-primary" to={`/patients/${c.patient_id}`}>{c.patient_name}</Link></td>
                <td className="px-3 py-2.5 text-muted">{pname(c.policy_id)}</td><td className="px-3 py-2.5">{inr(c.claim_amount)}</td>
                <td className="px-3 py-2.5">{c.approved_amount != null ? inr(c.approved_amount) : "—"}</td>
                <td className="px-3 py-2.5 text-muted">{fmtDate(c.submission_date)}</td><td className="px-3 py-2.5"><StatusBadge status={c.status} /></td>
                <td className="px-3 py-2.5"><ClearanceBadge clearance={c.clearance} /></td>
              </tr>
            ))}
          </DataTable>
        )}
      </Card>
      <Modal title="New claim" open={adding} onClose={() => setAdding(false)} wide>
        <ClaimForm onDone={(id) => { setAdding(false); navigate(`/claims/${id}`); }} />
      </Modal>
    </div>
  );
}
