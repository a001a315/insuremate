import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Badge, Card, DefList, ErrorNote, Modal, PageHeader, Spinner } from "@/components/ui/kit";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { post, useAiStatus, useApi } from "@/services/hooks";
import { label } from "@/utils/format";
import { useQueryClient } from "@tanstack/react-query";

export function SettingsPage() {
  const { user, logout } = useAuth();
  const toast = useToast();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const ai = useAiStatus();
  const [deleting, setDeleting] = useState(false);
  const [pw, setPw] = useState("");
  const [err, setErr] = useState<unknown>(null);
  const demo = useApi(() => post<{ status: string; document_index_status?: string; document_index_error?: string }>("/account/demo-data"), []);
  const del = useApi((password: string) => post("/account/delete", { password }), []);
  const s = ai.data;

  return (
    <div className="max-w-3xl">
      <PageHeader title="Settings" />
      <div className="space-y-4">
        <Card title="Account"><DefList items={[["Name", user?.full_name], ["Email", user?.email]]} /></Card>
        <Card title="AI & indexing" action={<Button size="sm" variant="outline" onClick={() => ai.refetch()}>Refresh</Button>}>
          {ai.isLoading ? <Spinner /> : ai.error ? <ErrorNote error={ai.error} /> : s && <>
            <DefList items={[
              ["LLM model", <span className="flex items-center gap-2">{s.llm.model}<Badge tone={s.llm.reachable && s.llm.model_available ? "success" : "danger"}>{s.llm.reachable ? (s.llm.model_available ? "Ready" : "Model not pulled") : "Ollama unreachable"}</Badge></span>],
              ["Embedding model", s.embedding_model],
              ["Vector database", <span className="flex items-center gap-2">ChromaDB · {s.vector_store.vectors} vectors<Badge tone={s.vector_store.ok ? "success" : "danger"}>{s.vector_store.ok ? "OK" : "Error"}</Badge></span>],
              ["Chunking", `${s.chunk_size} characters, ${s.chunk_overlap} overlap`]]} />
            {s.llm.detail !== "ok" && <p className="mt-3 text-sm text-warning">{s.llm.detail}</p>}
            <h3 className="mb-2 mt-5 text-sm font-medium">Document indexing status</h3>
            <div className="flex flex-wrap gap-2">{Object.keys(s.documents_by_status).length ? Object.entries(s.documents_by_status).map(([k, v]) => <Badge key={k}>{label(k)}: {v}</Badge>) : <span className="text-sm text-muted">No documents.</span>}</div>
            <p className="mt-4 text-xs text-muted">Models are set with environment variables (LLM_MODEL, EMBEDDING_MODEL) on the backend.</p></>}
        </Card>
        <Card title="Demo data"><p className="mb-3 text-sm text-muted">Load clearly labelled fictional policies, claims, records and a sample policy document so you can try the app. Nothing here is real.</p>
          <Button variant="outline" disabled={demo.isPending} onClick={() => demo.mutate(undefined, { onSuccess: (r) => { qc.invalidateQueries(); toast(r.status === "already_loaded" ? "Demo data is already loaded" : r.document_index_status === "indexed" ? "Demo data loaded" : `Demo data loaded; document indexing: ${r.document_index_error ?? r.document_index_status}`); }, onError: (e) => toast(e.message, "error") })}>
            {demo.isPending ? "Loading…" : "Load demo data"}</Button></Card>
        <Card title="Danger zone"><p className="mb-3 text-sm text-muted">Permanently delete your account and all policies, claims, records, documents and indexed data. This cannot be undone.</p>
          <Button className="bg-danger hover:bg-danger/90" onClick={() => setDeleting(true)}>Delete my account</Button></Card>
      </div>
      <Modal title="Delete account" open={deleting} onClose={() => setDeleting(false)}>
        <p className="mb-3 text-sm text-muted">Enter your password to permanently delete everything.</p>
        <Field label="Password" type="password" value={pw} onChange={(e) => setPw(e.target.value)} />
        <div className="mt-3"><ErrorNote error={err} /></div>
        <div className="mt-4 flex justify-end gap-2"><Button variant="outline" onClick={() => setDeleting(false)}>Cancel</Button>
          <Button className="bg-danger hover:bg-danger/90" disabled={!pw || del.isPending} onClick={async () => { setErr(null); try { await del.mutateAsync(pw); qc.clear(); logout(); navigate("/login"); } catch (e) { setErr(e); } }}>Delete everything</Button></div>
      </Modal>
    </div>
  );
}
