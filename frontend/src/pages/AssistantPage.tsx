import { useQueryClient } from "@tanstack/react-query";
import { Eraser, Plus, SendHorizontal, Trash2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Citations } from "@/components/chat/Citations";
import { Markdown } from "@/components/chat/Markdown";
import { Button } from "@/components/ui/Button";
import { ErrorNote, PageHeader, Spinner } from "@/components/ui/kit";
import { tokenStore } from "@/services/api";
import { del, post, useConversations, useMessages, usePatients, usePolicies } from "@/services/hooks";
import type { ChatMessage, Conversation } from "@/types";
import { cn } from "@/utils/cn";

const SUGGESTIONS = ["Is this patient eligible for cashless treatment here?", "What is the status of our pending claims?", "Which claims were rejected?", "Which policies expire soon?",
  "What is the waiting period for pre-existing diseases?", "Is room rent capped?", "What exclusions does the policy list?", "Which documents are needed for a reimbursement claim?"];

/** Minimal SSE reader for POST streams (EventSource only supports GET). */
async function streamAnswer(convId: string, question: string, policyId: string | null, patientId: string | null, onToken: (t: string) => void, signal: AbortSignal) {
  const res = await fetch(`/api/chat/conversations/${convId}/messages/stream`, {
    method: "POST", signal, headers: { "Content-Type": "application/json", Authorization: `Bearer ${tokenStore.get()}` },
    body: JSON.stringify({ question, policy_id: policyId, patient_id: patientId }),
  });
  if (!res.ok || !res.body) throw new Error(res.status === 401 ? "Session expired. Please sign in again." : "The assistant request failed.");
  const reader = res.body.getReader(); const dec = new TextDecoder(); let buf = "";
  for (;;) {
    const { value, done } = await reader.read(); if (done) break;
    buf += dec.decode(value, { stream: true });
    let i: number;
    while ((i = buf.indexOf("\n\n")) >= 0) {
      const block = buf.slice(0, i); buf = buf.slice(i + 2);
      const event = /^event: (.*)$/m.exec(block)?.[1]; const data = /^data: (.*)$/m.exec(block)?.[1];
      if (!event || data === undefined) continue;
      const parsed = JSON.parse(data);
      if (event === "token") onToken(parsed as string);
      else if (event === "error") throw new Error(parsed.detail);
    }
  }
}

export function AssistantPage() {
  const qc = useQueryClient();
  const patients = usePatients();
  const [patientId, setPatientId] = useState<string>("");
  const policies = usePolicies(false, patientId || undefined);
  const convs = useConversations();
  const [convId, setConvId] = useState<string | null>(null);
  const [policyId, setPolicyId] = useState<string>("");
  const [input, setInput] = useState("");
  const [pending, setPending] = useState<{ q: string; a: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [failedQ, setFailedQ] = useState<string | null>(null);
  const msgs = useMessages(convId);
  const bottom = useRef<HTMLDivElement>(null);
  const abort = useRef<AbortController | null>(null);
  useEffect(() => { bottom.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs.data, pending]);
  useEffect(() => () => abort.current?.abort(), []);

  const busy = pending !== null;
  async function send(q: string) {
    q = q.trim(); if (!q || busy) return;
    setError(null); setFailedQ(null); setInput("");
    let id = convId;
    try {
      if (!id) {
        const c = await post<Conversation>("/chat/conversations", { policy_id: policyId || null, patient_id: patientId || null });
        id = c.id; setConvId(id);
      }
      setPending({ q, a: "" });
      abort.current = new AbortController();
      await streamAnswer(id, q, policyId || null, patientId || null, (t) => setPending((p) => p && { ...p, a: p.a + t }), abort.current.signal);
      await qc.invalidateQueries({ queryKey: ["messages", id] });
      qc.invalidateQueries({ queryKey: ["conversations"] });
    } catch (e) {
      if ((e as Error).name !== "AbortError") { setError(e instanceof Error ? e.message : "Something went wrong"); setFailedQ(q); }
      if (id) qc.invalidateQueries({ queryKey: ["messages", id] });
    } finally { setPending(null); }
  }

  const list: ChatMessage[] = msgs.data ?? [];
  const noPolicies = policies.data && policies.data.length === 0;

  return (
    <div className="flex h-[calc(100vh-7.5rem)] flex-col">
      <PageHeader title="AI Assistant" subtitle="Answers come from the policies, claims and documents stored by this hospital, using a model running locally via Ollama."
        actions={<><Button variant="outline" size="sm" onClick={() => { setConvId(null); setError(null); }}><Plus size={14} />New conversation</Button>
          {convId && <Button variant="outline" size="sm" onClick={async () => { await post(`/chat/conversations/${convId}/clear`); qc.invalidateQueries({ queryKey: ["messages", convId] }); }}><Eraser size={14} />Clear</Button>}</>} />
      <div className="flex min-h-0 flex-1 gap-4">
        <aside className="hidden w-56 shrink-0 flex-col overflow-y-auto rounded-lg border border-line bg-surface p-2 md:flex" aria-label="Conversation history">
          <p className="px-2 py-1 text-xs font-medium text-muted">History</p>
          {!convs.data?.length && <p className="px-2 py-2 text-xs text-muted">No conversations yet.</p>}
          {convs.data?.map((c) => (
            <div key={c.id} className={cn("group flex items-center rounded-md", convId === c.id ? "bg-primary-soft" : "hover:bg-canvas")}>
              <button className="min-w-0 flex-1 truncate px-2 py-1.5 text-left text-sm" onClick={() => { setConvId(c.id); setError(null); }}>{c.title}</button>
              <button aria-label={`Delete conversation ${c.title}`} className="hidden px-1.5 text-muted hover:text-danger group-hover:block"
                onClick={async () => { await del(`/chat/conversations/${c.id}`); if (convId === c.id) setConvId(null); qc.invalidateQueries({ queryKey: ["conversations"] }); }}><Trash2 size={13} /></button>
            </div>))}
        </aside>
        <section className="flex min-w-0 flex-1 flex-col rounded-lg border border-line bg-surface">
          <div className="flex items-center gap-2 border-b border-line px-4 py-2.5">
            <label htmlFor="patient-scope" className="text-xs text-muted">Patient</label>
            <select id="patient-scope" value={patientId} onChange={(e) => { setPatientId(e.target.value); setPolicyId(""); }} className="h-8 max-w-44 rounded-md border border-line bg-surface px-2 text-sm">
              <option value="">All patients</option>{patients.data?.map((p) => <option key={p.id} value={p.id}>{p.full_name}</option>)}</select>
            <label htmlFor="scope" className="ml-2 text-xs text-muted">Policy</label>
            <select id="scope" value={policyId} onChange={(e) => setPolicyId(e.target.value)} className="h-8 max-w-52 rounded-md border border-line bg-surface px-2 text-sm">
              <option value="">{patientId ? "All of this patient's policies" : "All policies"}</option>{policies.data?.map((p) => <option key={p.id} value={p.id}>{p.name}{!patientId && p.patient_name ? ` · ${p.patient_name}` : ""}</option>)}</select>
          </div>
          <div className="flex-1 space-y-4 overflow-y-auto p-4" aria-live="polite">
            {msgs.isLoading && convId && <Spinner />}
            {!list.length && !pending && (
              <div className="mx-auto max-w-xl py-6 text-center">
                <p className="text-sm font-medium">{noPolicies ? "Add a patient policy first" : "Ask about patients' policies"}</p>
                <p className="mt-1 text-sm text-muted">{noPolicies ? "The assistant needs at least one patient policy, ideally with an uploaded policy document." : "Try one of these:"}</p>
                {!noPolicies && <div className="mt-4 flex flex-wrap justify-center gap-2">{SUGGESTIONS.map((s) => (
                  <button key={s} onClick={() => send(s)} className="rounded-full border border-line px-3 py-1.5 text-xs text-muted transition-colors hover:border-primary hover:text-primary">{s}</button>))}</div>}
              </div>)}
            {list.map((m) => <Bubble key={m.id} role={m.role} text={m.content} citations={m.citations} />)}
            {pending && <><Bubble role="user" text={pending.q} />{pending.a ? <Bubble role="assistant" text={pending.a} /> :
              <div className="flex items-center gap-2 text-sm text-muted"><Spinner />Checking the records…</div>}</>}
            {error && failedQ && <Bubble role="user" text={failedQ} />}
            <ErrorNote error={error} />
            {error && failedQ && <div><Button variant="outline" size="sm" onClick={() => send(failedQ)}>Try again</Button></div>}
            <div ref={bottom} />
          </div>
          <form className="flex gap-2 border-t border-line p-3" onSubmit={(e) => { e.preventDefault(); send(input); }}>
            <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask about eligibility, coverage, waiting periods, claim status…" aria-label="Message" maxLength={2000}
              className="h-10 flex-1 rounded-md border border-line bg-surface px-3 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary" />
            <Button type="submit" disabled={busy || !input.trim()} aria-label="Send"><SendHorizontal size={16} /></Button>
          </form>
          <p className="px-4 pb-2 text-[11px] text-muted">Informational only. Not an insurer decision; confirm coverage and eligibility with the patient's insurer/TPA.</p>
        </section>
      </div>
    </div>
  );
}

function Bubble({ role, text, citations }: { role: "user" | "assistant"; text: string; citations?: ChatMessage["citations"] }) {
  const user = role === "user";
  return (
    <div className={cn("flex", user && "justify-end")}>
      <div className={cn("max-w-[85%] rounded-lg px-3.5 py-2.5", user ? "bg-primary text-white" : "border border-line bg-canvas")}>
        {user ? <p className="whitespace-pre-wrap text-sm">{text}</p> : <Markdown>{text}</Markdown>}
        {!user && citations && <Citations items={citations} />}
      </div>
    </div>
  );
}
