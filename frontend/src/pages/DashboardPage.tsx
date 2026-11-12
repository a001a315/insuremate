import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Link } from "react-router-dom";
import { Card, ClearanceBadge, EmptyState, ErrorNote, NetworkBadge, PageHeader, Spinner } from "@/components/ui/kit";
import { useAuth } from "@/context/AuthContext";
import { useDashboard } from "@/services/hooks";
import { fmtDate, fmtDateTime, inr, label } from "@/utils/format";

export function DashboardPage() {
  const { user } = useAuth();
  const { data: d, isLoading, error } = useDashboard();
  if (isLoading) return <Spinner />;
  if (error || !d) return <ErrorNote error={error} />;
  const s = d.summary;
  const chart = d.claims_by_status.map((c) => ({ name: label(c.status), value: c.count }));
  const tiles: [string, string | number, string?][] = [
    ["Patients", s.patients], ["Active policies", s.active_policies], ["Expiring in 30 days", s.expiring_policies],
    ["Pending claims", s.pending_claims, `${s.amount_pending_display} claimed`], ["Cleared claims", s.cleared_claims, `${s.amount_approved_display} approved`], ["Rejected claims", s.rejected_claims],
  ];

  return (
    <div>
      <PageHeader title="Insurance desk overview" subtitle={`${user?.hospital_name || "Your hospital"}: patient policies, claim clearance and network status, from the information recorded by your team.`} />
      <div className="mb-5 grid grid-cols-2 gap-3 lg:grid-cols-6">
        {tiles.map(([l, v, sub]) => (
          <div key={l} className="rounded-lg border border-line bg-surface p-4"><p className="text-xs text-muted">{l}</p><p className="mt-1 text-2xl font-semibold tracking-tight">{v}</p>{sub && <p className="mt-0.5 text-xs text-muted">{sub}</p>}</div>))}
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          <Card title="Claims by status">{!chart.length ? <EmptyState title="No claims recorded yet" hint="Register a patient and add their policy and claims." action={<Link className="text-sm font-medium text-primary hover:underline" to="/patients">Go to Patients</Link>} /> :
            <div className="h-44" aria-label="Claims by status"><ResponsiveContainer width="100%" height="100%"><BarChart data={chart} margin={{ left: 0, right: 8 }}>
              <XAxis dataKey="name" tick={{ fontSize: 11, fill: "#667085" }} axisLine={false} tickLine={false} interval={0} />
              <YAxis hide allowDecimals={false} /><Tooltip cursor={{ fill: "#f4f1ea" }} />
              <Bar dataKey="value" name="Claims" fill="#1b3558" radius={[3, 3, 0, 0]} maxBarSize={48} /></BarChart></ResponsiveContainer></div>}</Card>
          <Card title="Policies expiring in the next 30 days">{!d.expiring.length ? <p className="text-sm text-muted">No active policy expires in the next 30 days.</p> :
            <ul className="divide-y divide-line text-sm">{d.expiring.map((p) => (
              <li key={p.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
                <span>{p.patient_id ? <Link className="font-medium hover:text-primary" to={`/patients/${p.patient_id}`}>{p.patient_name}</Link> : "—"}
                  <Link className="ml-2 text-muted hover:text-primary" to={`/policies/${p.id}`}>{p.name} · {p.insurer}</Link></span>
                <span className="flex items-center gap-2"><NetworkBadge status={p.network_status} /><span className="font-medium text-warning">{fmtDate(p.expiry_date)} · {p.days_left}d</span></span></li>))}</ul>}</Card>
          <Card title="Recent claims" action={<Link to="/claims" className="text-xs text-primary hover:underline">View all</Link>}>
            {!d.recent_claims.length ? <p className="text-sm text-muted">No claims recorded yet.</p> :
              <ul className="divide-y divide-line text-sm">{d.recent_claims.map((c) => (
                <li key={c.id} className="flex items-center justify-between gap-3 py-2"><Link className="font-medium text-primary hover:underline" to={`/claims/${c.id}`}>{c.claim_ref}</Link>
                  <span className="flex-1 truncate text-muted">{c.patient_name}{c.insurer ? ` · ${c.insurer}` : ""}</span><span>{inr(c.claim_amount)}</span><ClearanceBadge clearance={c.clearance} /></li>))}</ul>}</Card>
        </div>
        <div className="space-y-4">
          <Card title="Needs attention"><p className="mb-3 text-xs text-muted">Derived only from recorded data.</p>
            {!d.insights.length ? <p className="text-sm text-muted">Nothing needs attention right now.</p> :
              <ul className="space-y-2.5 text-sm">{d.insights.map((i, n) => <li key={n} className="border-l-2 border-primary/40 pl-3">{i.patient_id ? <Link className="hover:text-primary" to={`/patients/${i.patient_id}`}>{i.text}</Link> : i.text}</li>)}</ul>}</Card>
          <Card title="Recent activity">{!d.activity.length ? <p className="text-sm text-muted">Activity will appear as you add patients, policies and claims.</p> :
            <ol className="relative space-y-3 border-l border-line pl-4">{d.activity.slice(0, 8).map((a) => (
              <li key={a.id}><span className="absolute -left-[5px] mt-1.5 h-2.5 w-2.5 rounded-full border-2 border-surface bg-muted" /><p className="text-sm">{a.summary}</p>
                <p className="text-xs text-muted">{fmtDateTime(a.created_at)}</p></li>))}</ol>}</Card>
          <Card title="Recent documents" action={<Link to="/documents" className="text-xs text-primary hover:underline">View all</Link>}>
            {!d.recent_documents.length ? <p className="text-sm text-muted">No documents uploaded.</p> :
              <ul className="space-y-2 text-sm">{d.recent_documents.map((x) => (
                <li key={x.id} className="flex items-center justify-between gap-2"><span className="truncate">{x.name}</span><span className="shrink-0 text-xs text-muted">{label(x.index_status)}</span></li>))}</ul>}</Card>
        </div>
      </div>
    </div>
  );
}
