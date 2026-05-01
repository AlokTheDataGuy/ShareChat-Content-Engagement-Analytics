interface KPICardProps {
  label: string;
  value: string | number;
  sub?: string;
  trend?: number;
  icon?: React.ReactNode; // accepted, not rendered — keeps Streamlit clean look
  color?: string;
}

const accentMap: Record<string, string> = {
  orange: "#FF6B2C",
  teal:   "#00BCD4",
  green:  "#10B981",
  purple: "#8B5CF6",
  gold:   "#FFB800",
  blue:   "#3B82F6",
  amber:  "#FFB800",
  cyan:   "#00BCD4",
  red:    "#EF4444",
};

export default function KPICard({ label, value, sub, trend, color = "orange" }: KPICardProps) {
  const accent = accentMap[color] ?? "#FF6B2C";
  return (
    <div
      className="bg-bg-surface border-r border-b border-bg-border p-5 flex flex-col justify-between min-h-[110px]"
      style={{ borderTop: `3px solid ${accent}` }}
    >
      <div>
        <div className="text-[10px] font-bold uppercase tracking-widest text-text-muted mb-2">
          {label}
        </div>
        <div className="text-[26px] font-extrabold text-text-primary leading-none">
          {value ?? "—"}
        </div>
      </div>
      <div className="mt-3 flex items-center gap-2">
        {trend !== undefined && (
          <span className="text-xs font-semibold" style={{ color: trend >= 0 ? "#10B981" : "#EF4444" }}>
            {trend >= 0 ? "↑" : "↓"} {Math.abs(trend)}%
          </span>
        )}
        {sub && <p className="text-[11px] text-text-muted">{sub}</p>}
      </div>
    </div>
  );
}
