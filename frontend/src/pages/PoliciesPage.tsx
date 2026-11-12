import { Plus } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { PolicyForm } from "@/components/policies/PolicyForm";
import { Button } from "@/components/ui/Button";
import { Card, DataTable, EmptyState, ErrorNote, Modal, NetworkBadge, PageHeader, Spinner, StatusBadge } from "@/components/ui/kit";
import { usePolicies } from "@/services/hooks";
import { fmtDate, inr, label } from "@/utils/format";

export function PoliciesPage() {
  const [archived, setArchived] = useState(false);
  const [adding, setAdding] = useState(false);
  const navigate = useNavigate();
  const { data, isLoading, error } = usePolicies(archived);

  return (
    <div>
      <PageHeader title="Policies" subtitle="Every patient policy stored by this hospital, with network status at this hospital."
        actions={<><label className="flex items-center gap-2 text-sm text-muted"><input type="checkbox" checked={archived} onChange={(e) => setArchived(e.target.checked)} />Show archived</label>
          <Button onClick={() => setAdding(true)}><Plus size={15} />Add policy</Button></>} />
      <ErrorNote error={error} />
      <Card className="p-0 [&>div]:p-0">
        {isLoading ? <div className="p-6"><Spinner /></div> : !data?.length ? (
          <EmptyState title="No policies yet" hint="Register a patient first, then add their policy here (or from the patient's page)."
            action={<Button onClick={() => setAdding(true)}>Add a policy</Button>} />
        ) : (
          <DataTable head={["Patient", "Policy", "Insurer / TPA", "Policy no.", "Sum insured", "Expires", "At this hospital", "Status"]}>
            {data.map((p) => (
              <tr key={p.id} className="hover:bg-canvas/60">
                <td className="px-3 py-2.5">{p.patient_id ? <Link className="hover:text-primary" to={`/patients/${p.patient_id}`}>{p.patient_name}</Link> : "—"}</td>
                <td className="px-3 py-2.5"><Link className="font-medium text-primary hover:underline" to={`/policies/${p.id}`}>{p.name}</Link><p className="text-xs text-muted">{label(p.policy_type)}</p></td>
                <td className="px-3 py-2.5">{p.insurer}{p.tpa_name && <p className="text-xs text-muted">TPA: {p.tpa_name}</p>}</td>
                <td className="px-3 py-2.5 font-mono text-xs text-muted">{p.masked_policy_number}</td>
                <td className="px-3 py-2.5">{inr(p.sum_insured)}</td>
                                <td className="px-3 py-2.5">{fmtDate(p.expiry_date)}</td>
                <td className="px-3 py-2.5"><NetworkBadge status={p.network_status} /></td>
                <td className="px-3 py-2.5"><StatusBadge status={p.status} /></td>
              </tr>
            ))}
          </DataTable>
        )}
      </Card>
      <Modal title="Add policy" open={adding} onClose={() => setAdding(false)} wide>
        <PolicyForm onDone={(id) => { setAdding(false); navigate(`/policies/${id}`); }} />
      </Modal>
    </div>
  );
}
