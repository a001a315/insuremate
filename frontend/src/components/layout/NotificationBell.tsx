import { Bell } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { post, useNotifications } from "@/services/hooks";
import { fmtDateTime } from "@/utils/format";

export function NotificationBell() {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const qc = useQueryClient();
  const { data } = useNotifications();
  useEffect(() => {
    const h = (e: MouseEvent) => ref.current && !ref.current.contains(e.target as Node) && setOpen(false);
    document.addEventListener("mousedown", h); return () => document.removeEventListener("mousedown", h);
  }, []);
  const refresh = () => qc.invalidateQueries({ queryKey: ["notifications"] });
  return (
    <div className="relative" ref={ref}>
      <button onClick={() => setOpen((o) => !o)} className="relative rounded-md p-2 text-muted hover:bg-canvas" aria-label={`Notifications${data?.unread ? `, ${data.unread} unread` : ""}`} aria-expanded={open}>
        <Bell size={18} />{!!data?.unread && <span className="absolute right-1 top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-danger px-1 text-[10px] font-medium text-white">{data.unread}</span>}
      </button>
      {open && (
        <div className="absolute right-0 z-50 mt-1 w-80 rounded-lg border border-line bg-surface shadow-lg">
          <div className="flex items-center justify-between border-b border-line px-3 py-2"><span className="text-sm font-semibold">Notifications</span>
            {!!data?.unread && <button className="text-xs text-primary hover:underline" onClick={async () => { await post("/notifications/read-all"); refresh(); }}>Mark all read</button>}</div>
          <ul className="max-h-80 overflow-y-auto">
            {!data?.items.length && <li className="px-3 py-6 text-center text-sm text-muted">No notifications</li>}
            {data?.items.map((n) => (
              <li key={n.id}><button className={`block w-full px-3 py-2.5 text-left hover:bg-canvas ${n.is_read ? "" : "bg-primary-soft/50"}`}
                onClick={async () => { if (!n.is_read) { await post(`/notifications/${n.id}/read`); refresh(); } }}>
                <p className="text-sm font-medium">{n.title}</p>{n.body && <p className="text-xs text-muted">{n.body}</p>}
                <p className="mt-0.5 text-[11px] text-muted">{fmtDateTime(n.created_at)}</p></button></li>))}
          </ul>
        </div>)}
    </div>
  );
}
