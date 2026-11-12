import { Bell, Bot, ChevronsLeft, ChevronsRight, FolderOpen, HeartPulse, LayoutDashboard, LogOut, Menu, Settings, ShieldCheck, ClipboardList, Users, Building2 } from "lucide-react";
import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { NotificationBell } from "@/components/layout/NotificationBell";
import { cn } from "@/utils/cn";

const NAV = [
  { to: "/", label: "Overview", icon: LayoutDashboard, end: true },
  { to: "/patients", label: "Patients", icon: Users },
  { to: "/policies", label: "Policies", icon: ShieldCheck },
  { to: "/claims", label: "Claims", icon: ClipboardList },
  { to: "/records", label: "Medical Records", icon: HeartPulse },
  { to: "/documents", label: "Documents", icon: FolderOpen },
  { to: "/assistant", label: "AI Assistant", icon: Bot },
  { to: "/reminders", label: "Reminders", icon: Bell },
  { to: "/hospital", label: "Hospital Setup", icon: Building2 },
  { to: "/settings", label: "Settings", icon: Settings },
];

export function AppLayout() {
  const { user, logout } = useAuth();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const initials = (user?.full_name ?? "?").split(" ").map((p) => p[0]).slice(0, 2).join("").toUpperCase();

  return (
    <div className="flex h-full">
      {mobileOpen && <div className="fixed inset-0 z-30 bg-black/30 lg:hidden" onClick={() => setMobileOpen(false)} />}
      <aside className={cn(
        "fixed inset-y-0 left-0 z-40 flex flex-col border-r border-line bg-surface transition-all lg:static",
        collapsed ? "lg:w-16" : "lg:w-60", "w-60", mobileOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0",
      )}>
        <div className="flex h-14 items-center gap-2.5 border-b border-line px-4">
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-primary text-white"><ShieldCheck size={16} /></span>
          {!collapsed && <div className="min-w-0 leading-tight"><p className="truncate text-sm font-semibold tracking-tight">InsureMate AI</p>
            <p className="truncate text-[11px] text-muted">{user?.hospital_name || "Insurance desk"}</p></div>}
        </div>
        <nav className="flex-1 space-y-0.5 p-2" aria-label="Main">
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink key={to} to={to} end={end} onClick={() => setMobileOpen(false)} title={collapsed ? label : undefined}
              className={({ isActive }) => cn("flex h-9 items-center gap-3 rounded-md px-3 text-sm transition-colors",
                isActive ? "bg-primary-soft font-medium text-primary" : "text-muted hover:bg-canvas hover:text-ink")}>
              <Icon size={17} className="shrink-0" />
              {!collapsed && <span>{label}</span>}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-line p-2">
          <button onClick={() => setCollapsed((c) => !c)} className="mb-1 hidden h-8 w-full items-center gap-3 rounded-md px-3 text-xs text-muted hover:bg-canvas lg:flex" aria-label="Toggle sidebar">
            {collapsed ? <ChevronsRight size={16} /> : <><ChevronsLeft size={16} /><span>Collapse</span></>}
          </button>
          <div className="flex items-center gap-2.5 rounded-md p-2">
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary-soft text-xs font-semibold text-primary">{initials}</span>
            {!collapsed && (
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium">{user?.full_name}</p>
                <p className="truncate text-xs text-muted">{user?.email}</p>
              </div>
            )}
            {!collapsed && <button onClick={logout} aria-label="Sign out" className="text-muted hover:text-ink"><LogOut size={16} /></button>}
          </div>
        </div>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 items-center justify-between border-b border-line bg-surface px-4 lg:justify-end">
          <button className="lg:hidden" onClick={() => setMobileOpen(true)} aria-label="Open navigation"><Menu size={20} /></button>
          <NotificationBell />
        </header>
        <main className="flex-1 overflow-y-auto p-6"><Outlet /></main>
      </div>
    </div>
  );
}
