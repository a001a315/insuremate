import { Download, Eye, RefreshCw, Trash2 } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog, DataTable, EmptyState, StatusBadge } from "@/components/ui/kit";
import { useToast } from "@/context/ToastContext";
import { del, openFile, post, useApi } from "@/services/hooks";
import type { DocumentItem } from "@/types";
import { fmtDate, fmtSize, label } from "@/utils/format";

export function DocumentTable({ docs, extra }: { docs: DocumentItem[]; extra?: (d: DocumentItem) => React.ReactNode }) {
  const toast = useToast();
  const [toDelete, setToDelete] = useState<DocumentItem | null>(null);
  const remove = useApi((id: string) => del(`/documents/${id}`), ["documents", "claim-docs", "dashboard", "policies"]);
  const reindex = useApi((id: string) => post(`/documents/${id}/reindex`), ["documents"]);

  if (!docs.length) return <EmptyState title="No documents yet" hint="Uploaded documents will appear here." />;
  const act = async (fn: () => Promise<unknown>) => { try { await fn(); } catch (e) { toast(e instanceof Error ? e.message : "Failed", "error"); } };

  return (
    <>
      <DataTable head={["Name", "Category", "Status", "Size", "Uploaded", ""]}>
        {docs.map((d) => (
          <tr key={d.id} className="hover:bg-canvas/60">
            <td className="max-w-[16rem] px-3 py-2.5"><p className="truncate font-medium">{d.original_name}</p>
              {d.index_error && <p className="mt-0.5 text-xs text-danger">{d.index_error}</p>}</td>
            <td className="px-3 py-2.5 text-muted">{label(d.category)}</td>
            <td className="px-3 py-2.5"><StatusBadge status={d.index_status} /></td>
            <td className="px-3 py-2.5 text-muted">{fmtSize(d.size_bytes)}</td>
            <td className="px-3 py-2.5 text-muted">{fmtDate(d.created_at)}</td>
            <td className="px-3 py-2.5"><div className="flex justify-end gap-0.5">
              {extra?.(d)}
              <Button variant="ghost" size="icon" aria-label={`Preview ${d.original_name}`} onClick={() => act(() => openFile(d.id, d.original_name, "preview"))}><Eye size={15} /></Button>
              <Button variant="ghost" size="icon" aria-label={`Download ${d.original_name}`} onClick={() => act(() => openFile(d.id, d.original_name, "download"))}><Download size={15} /></Button>
              {["policy_document", "policy_schedule"].includes(d.category) &&
                <Button variant="ghost" size="icon" aria-label={`Re-index ${d.original_name}`} title="Re-index" onClick={() => act(() => reindex.mutateAsync(d.id))}><RefreshCw size={15} /></Button>}
              <Button variant="ghost" size="icon" aria-label={`Delete ${d.original_name}`} onClick={() => setToDelete(d)}><Trash2 size={15} /></Button>
            </div></td>
          </tr>
        ))}
      </DataTable>
      <ConfirmDialog open={!!toDelete} title="Delete document?" busy={remove.isPending}
        message={`"${toDelete?.original_name}" will be permanently deleted, including its indexed text used by the AI assistant.`}
        onClose={() => setToDelete(null)}
        onConfirm={() => toDelete && act(async () => { await remove.mutateAsync(toDelete.id); toast("Document deleted"); setToDelete(null); })} />
    </>
  );
}
