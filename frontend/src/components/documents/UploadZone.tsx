import { UploadCloud } from "lucide-react";
import { useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { SelectField } from "@/components/ui/Field";
import { uploadDocument } from "@/services/hooks";
import { DOC_CATEGORIES, label } from "@/utils/format";
import { cn } from "@/utils/cn";

const ALLOWED = [".pdf", ".docx", ".png", ".jpg", ".jpeg"];
const MAX_MB = 25;

interface Props { policyId?: string; patientId?: string; defaultCategory?: string; fixedCategory?: boolean; onUploaded?: (id: string) => void }
interface Item { name: string; pct: number; error?: string; done?: boolean }

export function UploadZone({ policyId, patientId, defaultCategory = "other", fixedCategory, onUploaded }: Props) {
  const [category, setCategory] = useState(defaultCategory);
  const [items, setItems] = useState<Record<string, Item>>({});
  const [drag, setDrag] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const qc = useQueryClient();

  const patch = (k: string, v: Partial<Item>) => setItems((s) => ({ ...s, [k]: { ...s[k], ...v } }));

  async function handle(files: FileList | File[]) {
    for (const f of Array.from(files)) {
      const key = `${f.name}-${f.size}-${Math.random()}`;
      const ext = "." + (f.name.split(".").pop() ?? "").toLowerCase();
      setItems((s) => ({ ...s, [key]: { name: f.name, pct: 0 } }));
      if (!ALLOWED.includes(ext)) { patch(key, { error: `Unsupported type. Allowed: ${ALLOWED.join(", ")}` }); continue; }
      if (f.size > MAX_MB * 1024 * 1024) { patch(key, { error: `Larger than ${MAX_MB} MB` }); continue; }
      try {
        const doc = await uploadDocument(f, category, policyId, (pct) => patch(key, { pct }), patientId);
        patch(key, { pct: 100, done: true });
        onUploaded?.(doc.id);
        qc.invalidateQueries({ queryKey: ["documents"] });
        qc.invalidateQueries({ queryKey: ["dashboard"] });
        qc.invalidateQueries({ queryKey: ["patient-docs"] });
      } catch (e) {
        patch(key, { error: e instanceof Error ? e.message : "Upload failed" });
      }
    }
  }

  return (
    <div className="space-y-3">
      {!fixedCategory && (
        <div className="max-w-xs">
          <SelectField label="Document category" value={category} onChange={(e) => setCategory(e.target.value)}>
            {DOC_CATEGORIES.map((c) => <option key={c} value={c}>{label(c)}</option>)}
          </SelectField>
        </div>
      )}
      <div
        onDragOver={(e) => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)}
        onDrop={(e) => { e.preventDefault(); setDrag(false); handle(e.dataTransfer.files); }}
        onClick={() => input.current?.click()} role="button" tabIndex={0} aria-label="Upload files"
        onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && input.current?.click()}
        className={cn("flex cursor-pointer flex-col items-center gap-1.5 rounded-lg border border-dashed px-6 py-8 text-center transition-colors",
          drag ? "border-primary bg-primary-soft" : "border-line bg-canvas hover:border-primary/50")}>
        <UploadCloud size={20} className="text-muted" />
        <p className="text-sm"><span className="font-medium text-primary">Choose files</span> or drag them here</p>
        <p className="text-xs text-muted">PDF, DOCX, PNG, JPG · up to {MAX_MB} MB</p>
        <input ref={input} type="file" multiple hidden accept={ALLOWED.join(",")} data-testid="file-input"
          onChange={(e) => { if (e.target.files) handle(e.target.files); e.target.value = ""; }} />
      </div>
      {Object.entries(items).map(([k, it]) => (
        <div key={k} className="text-sm">
          <div className="flex justify-between"><span className="truncate">{it.name}</span>
            <span className={it.error ? "text-danger" : "text-muted"}>{it.error ?? (it.done ? "Uploaded" : `${it.pct}%`)}</span></div>
          {!it.error && <div className="mt-1 h-1 rounded bg-line"><div className="h-1 rounded bg-primary transition-all" style={{ width: `${it.pct}%` }} /></div>}
        </div>
      ))}
    </div>
  );
}
