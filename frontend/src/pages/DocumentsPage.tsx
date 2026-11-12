import { useState } from "react";
import { DocumentTable } from "@/components/documents/DocumentTable";
import { UploadZone } from "@/components/documents/UploadZone";
import { Field, SelectField } from "@/components/ui/Field";
import { Card, ErrorNote, PageHeader, Spinner } from "@/components/ui/kit";
import { useDocuments, usePolicies } from "@/services/hooks";
import { DOC_CATEGORIES, label } from "@/utils/format";

export function DocumentsPage() {
  const [q, setQ] = useState("");
  const [category, setCategory] = useState("");
  const [policyId, setPolicyId] = useState("");
  const [uploadPolicy, setUploadPolicy] = useState("");
  const policies = usePolicies(true);
  const { data, isLoading, error } = useDocuments({ q: q || undefined, category: category || undefined, policy_id: policyId || undefined });
  return (
    <div>
      <PageHeader title="Documents" subtitle="Policy documents are indexed so the AI assistant can answer questions about them. Other documents are stored privately." />
      <Card title="Upload" className="mb-4">
        <div className="mb-3 max-w-xs"><SelectField label="Attach to policy (optional)" value={uploadPolicy} onChange={(e) => setUploadPolicy(e.target.value)}>
          <option value="">No policy</option>{policies.data?.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}</SelectField></div>
        <UploadZone key={uploadPolicy} policyId={uploadPolicy || undefined} defaultCategory="policy_document" />
      </Card>
      <ErrorNote error={error} />
      <Card title="All documents" className="[&>div]:p-0">
        <div className="grid gap-3 border-b border-line p-4 sm:grid-cols-3">
          <Field label="Search by name" value={q} onChange={(e) => setQ(e.target.value)} placeholder="e.g. discharge" />
          <SelectField label="Category" value={category} onChange={(e) => setCategory(e.target.value)}><option value="">All categories</option>
            {DOC_CATEGORIES.map((c) => <option key={c} value={c}>{label(c)}</option>)}</SelectField>
          <SelectField label="Policy" value={policyId} onChange={(e) => setPolicyId(e.target.value)}><option value="">All policies</option>
            {policies.data?.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}</SelectField>
        </div>
        {isLoading ? <div className="p-6"><Spinner /></div> : <DocumentTable docs={data ?? []} />}
      </Card>
    </div>
  );
}
