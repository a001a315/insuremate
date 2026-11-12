import { createContext, useCallback, useContext, useState, type ReactNode } from "react";
import { cn } from "@/utils/cn";

interface Toast { id: number; text: string; tone: "ok" | "error" }
const Ctx = createContext<(text: string, tone?: Toast["tone"]) => void>(() => {});

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<Toast[]>([]);
  const push = useCallback((text: string, tone: Toast["tone"] = "ok") => {
    const id = Date.now() + Math.random();
    setItems((s) => [...s, { id, text, tone }]);
    setTimeout(() => setItems((s) => s.filter((t) => t.id !== id)), 4000);
  }, []);
  return (
    <Ctx.Provider value={push}>
      {children}
      <div className="fixed bottom-4 right-4 z-[60] space-y-2" role="status" aria-live="polite">
        {items.map((t) => (
          <div key={t.id} className={cn("rounded-md border bg-surface px-4 py-2.5 text-sm shadow-md", t.tone === "error" ? "border-danger/40 text-danger" : "border-line")}>{t.text}</div>
        ))}
      </div>
    </Ctx.Provider>
  );
}
export const useToast = () => useContext(Ctx);
