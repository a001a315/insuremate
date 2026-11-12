import { Loader2, X } from "lucide-react";
import { useEffect, type ReactNode } from "react";
import { cn } from "@/utils/cn";
import { Button } from "./Button";
import { CLEARANCE_LABEL, INSURANCE_STATE_LABEL, NETWORK_LABEL, label } from "@/utils/format";

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
        {subtitle && <p className="mt-0.5 text-sm text-muted">{subtitle}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}

export function Card({ title, action, children, className }: { title?: string; action?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={cn("rounded-lg border border-line bg-surface", className)}>
      {title && (
        <header className="flex items-center justify-between border-b border-line px-4 py-3">
          <h2 className="text-sm font-semibold">{title}</h2>{action}
        </header>
      )}
      <div className="p-4">{children}</div>
    </section>
  );
}

const TONES: Record<string, string> = {
  neutral: "bg-canvas text-muted border-line", info: "bg-primary-soft text-primary border-transparent",
  success: "bg-success/10 text-success border-transparent", warning: "bg-warning/10 text-warning border-transparent",
  danger: "bg-danger/10 text-danger border-transparent",
};
export function Badge({ tone = "neutral", children }: { tone?: keyof typeof TONES; children: ReactNode }) {
  return <span className={cn("inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium whitespace-nowrap", TONES[tone])}>{children}</span>;
}

const STATUS_TONE: Record<string, keyof typeof TONES> = {
  draft: "neutral", pre_auth_requested: "info", pre_auth_approved: "success", pre_auth_rejected: "danger", submitted: "info", under_review: "info", additional_documents_required: "warning",
  approved: "success", partially_approved: "success", rejected: "danger", settled: "success",
  active: "success", expired: "danger", archived: "neutral",
  uploaded: "neutral", extracting_text: "info", processing: "info", generating_embeddings: "info", indexed: "success", failed: "danger",
};
export const StatusBadge = ({ status }: { status: string }) => <Badge tone={STATUS_TONE[status] ?? "neutral"}>{label(status)}</Badge>;

export const SourceBadge = ({ source }: { source: string }) => (
  <Badge tone={source === "manual" ? "neutral" : source === "extracted" ? "info" : "warning"}>
    {source === "manual" ? "Entered by staff" : source === "extracted" ? "Extracted" : "AI-generated"}
  </Badge>
);

export function Spinner({ className }: { className?: string }) {
  return <Loader2 className={cn("animate-spin text-muted", className)} size={16} aria-label="Loading" />;
}

export function EmptyState({ title, hint, action }: { title: string; hint?: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-1 px-6 py-10 text-center">
      <p className="text-sm font-medium">{title}</p>
      {hint && <p className="max-w-sm text-sm text-muted">{hint}</p>}
      {action && <div className="mt-3">{action}</div>}
    </div>
  );
}

export function ErrorNote({ error }: { error: unknown }) {
  if (!error) return null;
  return <p role="alert" className="rounded-md bg-danger/10 px-3 py-2 text-sm text-danger">{error instanceof Error ? error.message : String(error)}</p>;
}

export function Modal({ title, open, onClose, children, wide }: { title: string; open: boolean; onClose: () => void; children: ReactNode; wide?: boolean }) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/30 p-4 pt-[8vh]" onMouseDown={onClose}>
      <div role="dialog" aria-modal="true" aria-label={title} onMouseDown={(e) => e.stopPropagation()}
        className={cn("w-full rounded-lg border border-line bg-surface shadow-lg", wide ? "max-w-2xl" : "max-w-md")}>
        <header className="flex items-center justify-between border-b border-line px-4 py-3">
          <h2 className="text-sm font-semibold">{title}</h2>
          <button onClick={onClose} aria-label="Close" className="text-muted hover:text-ink"><X size={16} /></button>
        </header>
        <div className="p-4">{children}</div>
      </div>
    </div>
  );
}

export function ConfirmDialog({ open, title, message, confirmLabel = "Delete", onConfirm, onClose, busy }:
  { open: boolean; title: string; message: string; confirmLabel?: string; onConfirm: () => void; onClose: () => void; busy?: boolean }) {
  return (
    <Modal title={title} open={open} onClose={onClose}>
      <p className="text-sm text-muted">{message}</p>
      <div className="mt-5 flex justify-end gap-2">
        <Button variant="outline" onClick={onClose}>Cancel</Button>
        <Button className="bg-danger hover:bg-danger/90" onClick={onConfirm} disabled={busy}>{busy ? "Working…" : confirmLabel}</Button>
      </div>
    </Modal>
  );
}

export function Tabs({ tabs, value, onChange }: { tabs: { id: string; label: string }[]; value: string; onChange: (id: string) => void }) {
  return (
    <div role="tablist" className="mb-4 flex gap-1 overflow-x-auto border-b border-line">
      {tabs.map((t) => (
        <button key={t.id} role="tab" aria-selected={value === t.id} onClick={() => onChange(t.id)}
          className={cn("-mb-px whitespace-nowrap border-b-2 px-3 py-2 text-sm transition-colors",
            value === t.id ? "border-primary font-medium text-primary" : "border-transparent text-muted hover:text-ink")}>{t.label}</button>
      ))}
    </div>
  );
}

export function DataTable({ head, children }: { head: string[]; children: ReactNode }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead><tr className="border-b border-line text-left text-xs uppercase tracking-wide text-muted">
          {head.map((h) => <th key={h} className="px-3 py-2 font-medium">{h}</th>)}
        </tr></thead>
        <tbody className="divide-y divide-line">{children}</tbody>
      </table>
    </div>
  );
}

export function DefList({ items }: { items: [string, ReactNode][] }) {
  return (
    <dl className="grid grid-cols-1 gap-x-8 gap-y-3 sm:grid-cols-2">
      {items.map(([k, v]) => (
        <div key={k}><dt className="text-xs text-muted">{k}</dt><dd className="mt-0.5 text-sm">{v ?? "—"}</dd></div>
      ))}
    </dl>
  );
}

const CLEAR_TONE: Record<string, keyof typeof TONES> = { cleared: "success", pre_auth_cleared: "success", pending: "warning", rejected: "danger", draft: "neutral" };
export const ClearanceBadge = ({ clearance }: { clearance: string }) => <Badge tone={CLEAR_TONE[clearance] ?? "neutral"}>{CLEARANCE_LABEL[clearance] ?? label(clearance)}</Badge>;

const NET_TONE: Record<string, keyof typeof TONES> = { empanelled_cashless: "success", empanelled_no_cashless: "info", not_empanelled: "danger", expired: "warning", unknown: "neutral" };
export const NetworkBadge = ({ status }: { status: string }) => <Badge tone={NET_TONE[status] ?? "neutral"}>{NETWORK_LABEL[status] ?? label(status)}</Badge>;

const INS_TONE: Record<string, keyof typeof TONES> = { active: "success", expiring_soon: "warning", expired: "danger", no_policy: "neutral" };
export const InsuranceStateBadge = ({ state }: { state: string }) => <Badge tone={INS_TONE[state] ?? "neutral"}>{INSURANCE_STATE_LABEL[state] ?? label(state)}</Badge>;
