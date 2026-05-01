import { NavLink } from "react-router-dom";
import {
  LayoutDashboard, Users, FileText, DollarSign,
  RefreshCw, Globe, FlaskConical, Terminal, ChevronRight,
} from "lucide-react";

const NAV = [
  { to: "/",             label: "Overview",         icon: LayoutDashboard },
  { to: "/users",        label: "User Analytics",   icon: Users },
  { to: "/content",      label: "Content",          icon: FileText },
  { to: "/monetisation", label: "Monetisation",     icon: DollarSign },
  { to: "/retention",    label: "Retention",        icon: RefreshCw },
  { to: "/language",     label: "Language Analysis",icon: Globe },
  { to: "/ab-test",      label: "A/B Test",         icon: FlaskConical },
  { to: "/sql",          label: "SQL Workbench",    icon: Terminal },
];

export default function Sidebar() {
  return (
    <aside className="w-60 shrink-0 h-screen sticky top-0 bg-bg-surface border-r border-bg-border flex flex-col">
      {/* Logo */}
      <div className="px-5 py-4 border-b border-bg-border">
        <div className="flex items-center gap-3">
          <img src="/logo.png" alt="ShareChat" className="w-9 h-9 rounded-lg object-contain" />
          <div>
            <p className="text-sm font-bold text-text-primary leading-tight tracking-tight">ShareChat</p>
            <p className="text-[10px] font-semibold uppercase tracking-widest text-text-muted leading-tight">Analytics</p>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
        <p className="text-[10px] font-bold uppercase tracking-widest text-text-muted px-3 mb-3">
          Dashboards
        </p>
        {NAV.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-all group ${
                isActive
                  ? "bg-brand-dim text-brand border-l-2 border-brand pl-[10px]"
                  : "text-text-secondary hover:text-text-primary hover:bg-bg-elevated"
              }`
            }
          >
            {({ isActive }) => (
              <>
                <Icon
                  size={16}
                  className={isActive ? "text-brand" : "text-text-muted group-hover:text-text-secondary"}
                />
                <span className="flex-1">{label}</span>
                {isActive && <ChevronRight size={14} className="text-brand opacity-70" />}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-5 py-4 border-t border-bg-border">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-accent-green animate-pulse" />
          <span className="text-xs text-text-muted">SQLite · 551 MB · 2.97M rows</span>
        </div>
      </div>
    </aside>
  );
}
