import { Pencil, Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ClaimForm } from "@/components/claims/ClaimForm";
import { DocumentTable } from "@/components/documents/DocumentTable";
import { UploadZone } from "@/components/documents/UploadZone";
import { EligibilityPanel } from "@/components/patients/EligibilityPanel";
import { PatientForm } from "@/components/patients/PatientForm";
import { PolicyForm } from "@/components/policies/PolicyForm";
import { Button } from "@/components/ui/Button";
import { Card, ClearanceBadge, ConfirmDialog, DataTable, DefList, EmptyState, ErrorNote, InsuranceStateBadge, Modal, NetworkBadge, PageHeader, Spinner, StatusBadge, Tabs } from "@/components/ui/kit";
import { useToast } from "@/context/ToastContext";
import { del, useApi, useClaims, useDocuments, usePatient, usePatients, usePolicies, useRecords } from "@/services/hooks";
import { fmtDate, inr, label } from "@/utils/format";

const TABS = [["insurance", "Insurance & eligibility"], ["claims", "Claims"], ["documents", "Documents"], ["records", "Medical records"], ["details", "Details"]].map(([id, l]) => ({ id, label: l }));

export function PatientDetailPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const [tab, setTab] = useState("insurance");
  const [modal, setModal] = useState<"edit" | "policy" | "claim" | "delete" | null>(null);
  const { data: p, isLoading, error } = usePatient(id);
  const summary = usePatients().data?.find((x) => x.id === id);
  const policies = usePolicies(false, id);
  const claims = useClaims({ patient_id: id });
  const docs = useDocuments({ patient_id: id });
  const records = useRecords({ patient_id: id });
  const remove = useApi(() => del(`/patients/${id}`), ["patients", "policies", "claims", "documents", "records", "dashboard"]);

  if (isLoading) return <Spinner />;
  if (error || !p) return <ErrorNote error={error ?? new Error("Patient not found")} />;
  const pol = policies.data ?? [];

  return (
    <div>
      <p className="mb-2 text-sm"><Link to="/patients" className="text-muted hover:text-ink">← Patients</Link></p>
      <PageHeader title={p.full_name} subtitle={[p.mrn, p.gender && label(p.gender), p.date_of_birth && `Born ${fmtDate(p.date_of_birth)}`].filter(Boolean).join(" · ") || "Patient"}
        actions={<>{summary && <InsuranceStateBadge state={summary.insurance_state} />}
          <Button variant="outline" size="sm" onClick={() => setModal("edit")}><Pencil size={14} />Edit</Button>
          <Button variant="outline" size="sm" onClick={() => setModal("delete")}><Trash2 size={14} />Delete</Button></>} />
      <Tabs tabs={TABS} value={tab} onChange={setTab} />

      {tab === "insurance" && <div className="space-y-4">
        <Card title="Insurance policies" action={<Button size="sm" variant="outline" onClick={() => setModal("policy")}><Plus size={14} />Add policy</Button>} className="[&>div]:p-0">
          {!pol.length ? <EmptyState title="No policy recorded" hint="Add this patient's insurance policy to track claims and check eligibility." action={<Button onClick={() => setModal("policy")}>Add policy</Button>} /> :
            <DataTable head={["Policy", "Insurer / TPA", "Sum insured", "Valid until", "At this hospital", "Status"]}>
              {pol.map((x) => (
                <tr key={x.id}>
                  <td className="px-3 py-2.5"><Link className="font-medium text-primary hover:underline" to={`/policies/${x.id}`}>{x.name}</Link><p className="font-mono text-xs text-muted">{x.masked_policy_number}</p></td>
                  <td className="px-3 py-2.5">{x.insurer}{x.tpa_name && <p className="text-xs text-muted">TPA: {x.tpa_name}</p>}</td>
                  <td className="px-3 py-2.5">{inr(x.sum_insured)}</td><td className="px-3 py-2.5">{fmtDate(x.expiry_date)}</td>
                  <td className="px-3 py-2.5"><NetworkBadge status={x.network_status} /></td><td className="px-3 py-2.5"><StatusBadge status={x.status} /></td>
                </tr>))}
            </DataTable>}
        </Card>
        <EligibilityPanel patientId={id} hasPolicies={pol.length > 0} />
      </div>}

      {tab === "claims" && <Card title="Claims & pre-authorisations" action={<Button size="sm" variant="outline" disabled={!pol.length} onClick={() => setModal("claim")}><Plus size={14} />New claim</Button>} className="[&>div]:p-0">
        {!claims.data?.length ? <EmptyState title="No claims for this patient" hint={pol.length ? undefined : "Add a policy first."} /> :
          <DataTable head={["Claim", "Insurer", "Claimed", "Approved", "Status", "Clearance"]}>
            {claims.data.map((c) => (
              <tr key={c.id}>
                <td className="px-3 py-2.5"><Link className="font-medium text-primary hover:underline" to={`/claims/${c.id}`}>{c.claim_ref}</Link>
                  {c.rejection_reason && <p className="max-w-64 truncate text-xs text-danger" title={c.rejection_reason}>{c.rejection_reason}</p>}</td>
                <td className="px-3 py-2.5 text-muted">{c.insurer ?? "—"}</td><td className="px-3 py-2.5">{inr(c.claim_amount)}</td>
                <td className="px-3 py-2.5">{c.approved_amount != null ? inr(c.approved_amount) : "—"}</td>
                <td className="px-3 py-2.5"><StatusBadge status={c.status} /></td><td className="px-3 py-2.5"><ClearanceBadge clearance={c.clearance} /></td>
              </tr>))}
          </DataTable>}</Card>}

      {tab === "documents" && <div className="space-y-4">
        <Card title="Upload a document"><UploadZone patientId={id} defaultCategory="policy_document" /></Card>
        <Card className="p-0 [&>div]:p-0"><DocumentTable docs={docs.data ?? []} /></Card></div>}

      {tab === "records" && <Card className="p-0 [&>div]:p-0">{!records.data?.length ? <EmptyState title="No medical records" hint="Add records from the Medical Records page." /> :
        <DataTable head={["Date", "Title", "Category", "Provider"]}>{records.data.map((r) => (
          <tr key={r.id}><td className="px-3 py-2.5 text-muted">{fmtDate(r.record_date)}</td><td className="px-3 py-2.5">{r.title}</td>
            <td className="px-3 py-2.5">{label(r.category)}</td><td className="px-3 py-2.5 text-muted">{r.provider ?? "—"}</td></tr>))}</DataTable>}</Card>}

      {tab === "details" && <Card><DefList items={[["MRN", p.mrn], ["Gender", p.gender ? label(p.gender) : null], ["Date of birth", fmtDate(p.date_of_birth)], ["Phone", p.phone], ["Notes", p.notes]]} /></Card>}

      <Modal title="Edit patient" open={modal === "edit"} onClose={() => setModal(null)} wide><PatientForm patient={p} onDone={() => setModal(null)} /></Modal>
      <Modal title="Add policy" open={modal === "policy"} onClose={() => setModal(null)} wide><PolicyForm patientId={id} onDone={() => setModal(null)} /></Modal>
      <Modal title="New claim" open={modal === "claim"} onClose={() => setModal(null)} wide><ClaimForm defaultPatientId={id} onDone={(cid) => { setModal(null); navigate(`/claims/${cid}`); }} /></Modal>
      <ConfirmDialog open={modal === "delete"} title="Delete patient?" busy={remove.isPending}
        message="This permanently deletes the patient together with their policies, claims and uploaded documents (including indexed text)."
        onClose={() => setModal(null)} onConfirm={async () => { await remove.mutateAsync(undefined); toast("Patient deleted"); navigate("/patients"); }} />
    </div>
  );
}
