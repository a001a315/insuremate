import { FileText, Database } from "lucide-react";
import { useState } from "react";
import type { Citation } from "@/types";

export function Citations({ items }: { items: Citation[] }) {
  const [open, setOpen] = useState<number | null>(null);
  if (!items.length) return null;
  return (
    <div className="mt-3 border-t border-line pt-2">
      <p className="mb-1.5 text-xs font-medium text-muted">Sources</p>
      <ul className="space-y-1">
        {items.map((c, i) => (
          <li key={i} className="text-xs">
            {c.type === "document" ? (
              <button className="flex w-full items-start gap-1.5 text-left text-muted hover:text-ink" onClick={() => setOpen(open === i ? null : i)} aria-expanded={open === i}>
                <FileText size={13} className="mt-0.5 shrink-0" />
                <span><span className="font-medium text-ink">{c.document_name}</span>{c.page_number ? `, page ${c.page_number}` : ""}</span>
              </button>
            ) : (
              <span className="flex items-start gap-1.5 text-muted"><Database size={13} className="mt-0.5 shrink-0" />{c.label}</span>
            )}
            {open === i && c.excerpt && <blockquote className="ml-5 mt-1 border-l-2 border-line pl-2 text-muted">{c.excerpt}…</blockquote>}
          </li>
        ))}
      </ul>
    </div>
  );
}
