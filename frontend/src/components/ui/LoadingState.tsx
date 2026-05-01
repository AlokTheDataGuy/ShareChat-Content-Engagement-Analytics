export function Spinner() {
  return (
    <div className="flex items-center justify-center py-16">
      <div className="w-8 h-8 border-2 border-bg-border border-t-brand rounded-full animate-spin" />
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="flex items-center justify-center py-16">
      <div className="text-center">
        <div className="text-accent-red text-2xl mb-2">⚠</div>
        <p className="text-text-secondary text-sm">{message}</p>
        <p className="text-text-muted text-xs mt-1">Is the backend running? Run: uvicorn app.main:app --reload</p>
      </div>
    </div>
  );
}

export function PageShell({
  title,
  subtitle,
  description,
  children,
}: {
  title: string;
  subtitle?: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="p-6 space-y-5">
      <div className="border-b border-bg-border pb-4">
        <h1 className="text-[11px] font-bold uppercase tracking-widest text-text-muted">{title}</h1>
        {subtitle && <p className="text-xs text-text-muted mt-0.5">{subtitle}</p>}
        {description && (
          <p className="text-sm text-text-secondary mt-2 max-w-3xl leading-relaxed">{description}</p>
        )}
      </div>
      {children}
    </div>
  );
}

export function Card({ title, children, className = "" }: { title?: string; children: React.ReactNode; className?: string }) {
  return (
    <div className={`bg-bg-surface border border-bg-border overflow-hidden ${className}`}>
      {title && (
        <div className="px-5 py-3 border-b border-bg-border">
          <h3 className="text-[10px] font-bold uppercase tracking-widest text-text-muted">{title}</h3>
        </div>
      )}
      <div className="p-5">{children}</div>
    </div>
  );
}

export function Insight({ children, title = "Key Insight" }: { children: React.ReactNode; title?: string }) {
  return (
    <div className="flex gap-0 border border-bg-border" style={{ borderLeft: "3px solid #FF6B2C" }}>
      <div className="px-4 py-3 bg-orange-50 w-full">
        <div className="text-[10px] font-bold uppercase tracking-widest mb-1" style={{ color: "#FF6B2C" }}>
          {title}
        </div>
        <div className="text-xs text-text-secondary leading-relaxed">{children}</div>
      </div>
    </div>
  );
}

export const TOOLTIP_STYLE = {
  background: "#ffffff",
  border: "1px solid #e5e7eb",
  borderRadius: 4,
  fontSize: 12,
  color: "#111827",
} as const;

export const TICK_STYLE = { fill: "#9CA3AF", fontSize: 11 } as const;

export const SC_COLORS = [
  "#FF6B2C", "#00BCD4", "#10B981", "#8B5CF6",
  "#FFB800", "#EF4444", "#3B82F6", "#EC4899",
] as const;
