import { Plus, Search } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { PatientForm } from "@/components/patients/PatientForm";
import { Button } from "@/components/ui/Button";
import { Card, ClearanceBadge, DataTable, EmptyState, ErrorNote, InsuranceStateBadge, Modal, PageHeader, Spinner } from "@/components/ui/kit";
import { usePatients } from "@/services/hooks";
import { fmtDate, label } from "@/utils/format";

export function PatientsPage() {
  const [q, setQ] = useState("");
  const [adding, setAdding] = useState(false);
  const navigate = useNavigate();
  const { data, isLoading, error } = usePatients(q.trim() || undefined);

  return (
    <div>
      <PageHeader title="Patients" subtitle="Each patient's insurance policies, claim clearance and eligibility at this hospital."
        actions={<Button onClick={() => setAdding(true)}><Plus size={15} />Register patient</Button>} />
      <div className="mb-4 flex max-w-sm items-center gap-2 rounded-md border border-line bg-surface px-3">
        <Search size={15} className="text-muted" />
        <input aria-label="Search patients" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search name, MRN or phone"
          className="h-9 flex-1 bg-transparent text-sm outline-none" />
      </div>
      <ErrorNote error={error} />
      <Card className="p-0 [&>div]:p-0">
        {isLoading ? <div className="p-6"><Spinner /></div> : !data?.length ? (
          <EmptyState title={q ? "No matching patients" : "No patients yet"} hint={q ? "Try a different name, MRN or phone number." : "Register a patient, then record their insurance policy to track claims and check eligibility."}
            action={!q && <Button onClick={() => setAdding(true)}>Register your first patient</Button>} />
        ) : (
          <DataTable head={["Patient", "Insurance", "Active policies", "Open claims", "Latest claim", "Date of birth"]}>
            {data.map((p) => (
              <tr key={p.id} className="hover:bg-canvas/60">
                <td className="px-3 py-2.5"><Link className="font-medium text-primary hover:underline" to={`/patients/${p.id}`}>{p.full_name}</Link>{p.mrn && <p className="text-xs text-muted">{p.mrn}</p>}</td>
                <td className="px-3 py-2.5"><InsuranceStateBadge state={p.insurance_state} /></td>
                <td className="px-3 py-2.5">{p.active_policies}</td>
                <td className="px-3 py-2.5">{p.open_claims}</td>
                <td className="px-3 py-2.5">{p.latest_clearance ? <span className="flex items-center gap-2"><ClearanceBadge clearance={p.latest_clearance} /><span className="text-xs text-muted">{label(p.latest_claim_status ?? "")}</span></span> : <span className="text-muted">—</span>}</td>
                <td className="px-3 py-2.5 text-muted">{fmtDate(p.date_of_birth)}</td>
              </tr>))}
          </DataTable>)}
      </Card>
      <Modal title="Register patient" open={adding} onClose={() => setAdding(false)} wide>
        <PatientForm onDone={(id) => { setAdding(false); navigate(`/patients/${id}`); }} />
      </Modal>
    </div>
  );
}
