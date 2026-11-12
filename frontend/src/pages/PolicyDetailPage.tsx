import { Archive, Pencil, Sparkles, Trash2 } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { DocumentTable } from "@/components/documents/DocumentTable";
import { UploadZone } from "@/components/documents/UploadZone";
import { PolicyForm } from "@/components/policies/PolicyForm";
import { Button } from "@/components/ui/Button";
import { Card, ClearanceBadge, ConfirmDialog, DataTable, DefList, EmptyState, ErrorNote, Modal, NetworkBadge, PageHeader, SourceBadge, Spinner, StatusBadge, Tabs } from "@/components/ui/kit";
import { useToast } from "@/context/ToastContext";
import { del, post, useApi, useClaims, useDocuments, usePatient, usePolicy } from "@/services/hooks";
import type { Policy } from "@/types";
import { DETAIL_LABELS, fmtDate, inr, label } from "@/utils/format";

const TABS = [["overview", "Overview"], ["coverage", "Coverage"], ["exclusions", "Exclusions"], ["members", "Insured members"], ["documents", "Documents"], ["claims", "Claims history"], ["summary", "AI summary"]]
  .map(([id, l]) => ({ id, label: l }));

function Detail({ p, keys }: { p: Policy; keys: string[] }) {
  const shown = keys.filter((k) => p.details[k]?.value);
  if (!shown.length) return <EmptyState title="Nothing recorded yet" hint="Edit the policy to add this information, or ask the AI assistant about it once a document is indexed." />;
  return <div className="space-y-4">{shown.map((k) => (
    <div key={k}><div className="mb-1 flex items-center gap-2"><h3 className="text-sm font-medium">{DETAIL_LABELS[k]}</h3><SourceBadge source={p.details[k].source} /></div>
      <p className="whitespace-pre-line text-sm text-muted">{p.details[k].value}</p></div>))}</div>;
}

export function PolicyDetailPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const [tab, setTab] = useState("overview");
  const [editing, setEditing] = useState(false);
  const [confirm, setConfirm] = useState<"delete" | "archive" | null>(null);
  const { data: p, isLoading, error } = usePolicy(id);
  const patient = usePatient(p?.patient_id ?? "");
  const docs = useDocuments({ policy_id: id });
  const claims = useClaims({ policy_id: id });
  const archive = useApi(() => post(`/policies/${id}/archive`), ["policies", "policy", "dashboard"]);
  const remove = useApi(() => del(`/policies/${id}`), ["policies", "dashboard", "documents", "claims", "patients"]);
  const summarise = useApi(() => post<Policy>(`/policies/${id}/summary`), ["policy"]);

  if (isLoading) return <Spinner />;
  if (error || !p) return <ErrorNote error={error ?? new Error("Policy not found")} />;

  return (
    <div>
      <p className="mb-2 text-sm"><Link to="/policies" className="text-muted hover:text-ink">← Policies</Link></p>
      <PageHeader title={p.name} subtitle={`${p.insurer} · ${p.policy_number}`}
        actions={<><NetworkBadge status={p.network_status} /><StatusBadge status={p.status} />
          <Button variant="outline" size="sm" onClick={() => setEditing(true)}><Pencil size={14} />Edit</Button>
          {p.status !== "archived" && <Button variant="outline" size="sm" onClick={() => setConfirm("archive")}><Archive size={14} />Archive</Button>}
          <Button variant="outline" size="sm" onClick={() => setConfirm("delete")}><Trash2 size={14} />Delete</Button></>} />
      <Tabs tabs={TABS} value={tab} onChange={setTab} />

      {tab === "overview" && <Card><DefList items={[
        ["Patient", patient.data ? <Link className="text-primary hover:underline" to={`/patients/${patient.data.id}`}>{patient.data.full_name}</Link> : "—"],
        ["Policyholder", p.policyholder_name], ["TPA", p.tpa_name ?? "—"], ["Initial waiting period", `${p.initial_waiting_days} days`], ["Policy type", label(p.policy_type)], ["Sum insured", inr(p.sum_insured)],
        ["Premium", `${inr(p.premium_amount)} / ${label(p.premium_frequency).toLowerCase()}`], ["Start date", fmtDate(p.start_date)],
        ["Expiration date", fmtDate(p.expiry_date)], ["Renewal date", fmtDate(p.renewal_date)],
        ["Nominee", p.nominee ? `${p.nominee.name}${p.nominee.relationship ? ` (${p.nominee.relationship})` : ""}` : "—"]]} /></Card>}
      {tab === "coverage" && <Card><Detail p={p} keys={["covered_conditions", "waiting_periods", "room_rent_limit", "copay", "network_hospitals", "restoration_benefit", "no_claim_bonus"]} /></Card>}
      {tab === "exclusions" && <Card><Detail p={p} keys={["exclusions"]} /></Card>}
      {tab === "members" && <Card className="p-0 [&>div]:p-0">{!p.members.length ? <EmptyState title="No insured members recorded" /> :
        <DataTable head={["Name", "Relationship"]}>{p.members.map((m) => <tr key={m.id}><td className="px-3 py-2.5">{m.name}</td><td className="px-3 py-2.5 text-muted">{label(m.relationship_to_holder)}</td></tr>)}</DataTable>}</Card>}
      {tab === "documents" && <div className="space-y-4">
        <Card title="Upload a policy document"><UploadZone policyId={id} defaultCategory="policy_document" /></Card>
        <Card className="p-0 [&>div]:p-0"><DocumentTable docs={docs.data ?? []} /></Card></div>}
      {tab === "claims" && <Card className="p-0 [&>div]:p-0">{!claims.data?.length ? <EmptyState title="No claims for this policy" /> :
        <DataTable head={["Claim", "Patient", "Amount", "Status", "Clearance"]}>{claims.data.map((c) => (
          <tr key={c.id}><td className="px-3 py-2.5"><Link className="font-medium text-primary hover:underline" to={`/claims/${c.id}`}>{c.claim_ref}</Link></td>
            <td className="px-3 py-2.5">{c.patient_name}</td><td className="px-3 py-2.5">{inr(c.claim_amount)}</td><td className="px-3 py-2.5"><StatusBadge status={c.status} /></td><td className="px-3 py-2.5"><ClearanceBadge clearance={c.clearance} /></td></tr>))}</DataTable>}</Card>}
      {tab === "summary" && <Card title="AI-generated summary" action={<Button size="sm" variant="outline" disabled={summarise.isPending}
        onClick={() => summarise.mutate(undefined, { onError: (e) => toast(e instanceof Error ? e.message : "Failed", "error"), onSuccess: () => toast("Summary generated") })}>
        <Sparkles size={14} />{summarise.isPending ? "Generating…" : p.ai_summary ? "Regenerate" : "Generate"}</Button>}>
        {p.ai_summary ? <><div className="mb-3"><SourceBadge source="ai_summary" /></div>
          <div className="prose-sm text-sm leading-relaxed [&_li]:ml-5 [&_li]:list-disc [&_p]:mb-2"><ReactMarkdown remarkPlugins={[remarkGfm]}>{p.ai_summary}</ReactMarkdown></div></> :
          <EmptyState title="No summary yet" hint="Generated from this policy's indexed documents by your local model. Upload and index a document first." />}</Card>}

      <Modal title="Edit policy" open={editing} onClose={() => setEditing(false)} wide><PolicyForm policy={p} onDone={() => setEditing(false)} /></Modal>
      <ConfirmDialog open={confirm === "delete"} title="Delete policy?" busy={remove.isPending}
        message="This permanently deletes the policy, its claims, and its uploaded documents (including their indexed text)."
        onClose={() => setConfirm(null)} onConfirm={async () => { await remove.mutateAsync(undefined); toast("Policy deleted"); navigate("/policies"); }} />
      <ConfirmDialog open={confirm === "archive"} title="Archive policy?" confirmLabel="Archive" busy={archive.isPending}
        message="Archived policies are hidden from the dashboard and the assistant's default scope. You can still view them under Policies."
        onClose={() => setConfirm(null)} onConfirm={async () => { await archive.mutateAsync(undefined); toast("Policy archived"); setConfirm(null); }} />
    </div>
  );
}
