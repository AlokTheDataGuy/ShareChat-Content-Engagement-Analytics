import {
  ComposedChart, Area, Line, ReferenceLine,
  BarChart, Bar, Cell, LabelList,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";
import { Spinner, ErrorState, PageShell, Card, Insight, SC_COLORS, TOOLTIP_STYLE, TICK_STYLE } from "../components/ui/LoadingState";
import KPICard from "../components/ui/KPICard";
import { useAPI } from "../hooks/useAPI";
import { api } from "../services/api";

export default function UserAnalytics() {
  const retention = useAPI(api.users.retentionCurve);
  const byHour    = useAPI(api.users.sessionsByHour);
  const tiers     = useAPI(api.users.tierBreakdown);

  if (retention.error) return <ErrorState message={retention.error} />;

  const d0  = retention.data?.[0]?.retained_users ?? 1;
  const d1  = retention.data?.find((r: { day: number }) => r.day === 1)?.retained_users  ?? 0;
  const d7  = retention.data?.find((r: { day: number }) => r.day === 7)?.retained_users  ?? 0;
  const d30 = retention.data?.find((r: { day: number }) => r.day === 30)?.retained_users ?? 0;

  const d1pct  = Math.round(d1  / d0 * 100);
  const d7pct  = Math.round(d7  / d0 * 100);
  const d30pct = Math.round(d30 / d0 * 100);

  // Intensity color for sessions by hour: higher session count = more orange
  const maxSessions = Math.max(...((byHour.data ?? []).map((r: { sessions: number }) => r.sessions)));
  const hourColor = (sessions: number) => {
    const t = sessions / (maxSessions || 1);
    const r = Math.round(255 * (0.6 + 0.4 * t));
    const g = Math.round(107 * (1 - t * 0.6));
    const b = Math.round(44  * (1 - t * 0.7));
    return `rgb(${r},${g},${b})`;
  };

  return (
    <PageShell
      title="User Analytics"
      subtitle="Retention, session behaviour, and segment breakdown"
      description="Understand how users behave after they first open the app. Day-1 retention reflects onboarding quality; Day-7 shows whether the core product hook is working; Day-30 is a proxy for true product-market fit."
    >
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-0 border-l border-t border-bg-border">
        <KPICard label="Day-1 Retention"  value={`${d1pct}%`}  sub="Users returning next day" color="orange" />
        <KPICard label="Day-7 Retention"  value={`${d7pct}%`}  sub="Week-1 returners"         color="teal" />
        <KPICard label="Day-30 Retention" value={`${d30pct}%`} sub="Month-1 returners"        color="green" />
        <KPICard label="Cohort Size"      value={d0.toLocaleString()} sub="Day-0 unique users" color="purple" />
      </div>

      <Insight title="Benchmarks">
        Industry benchmarks: D1 ≥ 35%, D7 ≥ 20%, D30 ≥ 10%.{" "}
        {d1pct >= 35
          ? `Your D1 of ${d1pct}% beats the benchmark — first-session experience is strong.`
          : `D1 of ${d1pct}% is below 35% — run onboarding A/B tests.`}{" "}
        {d7pct >= 20
          ? `D7 of ${d7pct}% confirms the content loop is creating a habit.`
          : `D7 of ${d7pct}% suggests the feed personalisation isn't landing in week one.`}
      </Insight>

      {/* Retention curve — filled area + benchmark reference lines */}
      <Card title="Day-N Retention Curve (30-day window)">
        <p className="text-xs text-text-muted mb-4">
          Orange filled area = actual retention. Dashed lines mark industry benchmarks at D1 (35%) and D7 (20%).
          A curve that stays above both benchmarks and flattens after Day 7 means a strong habit loop has formed.
        </p>
        {retention.loading ? <Spinner /> : (
          <ResponsiveContainer width="100%" height={300}>
            <ComposedChart data={retention.data ?? []} margin={{ top: 8, right: 16, left: 0, bottom: 24 }}>
              <defs>
                <linearGradient id="retGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%"   stopColor="#FF6B2C" stopOpacity={0.3} />
                  <stop offset="100%" stopColor="#FF6B2C" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" vertical={false} />
              <XAxis dataKey="day" tick={TICK_STYLE} tickLine={false}
                label={{ value: "Days after first session", position: "insideBottom", offset: -12, fill: "#9CA3AF", fontSize: 11 }} />
              <YAxis tick={TICK_STYLE} tickLine={false} axisLine={false}
                tickFormatter={(v) => `${v}%`} width={44} domain={[0, 105]} />
              <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v: number) => [`${v}%`, "Retention"]} />
              {/* Benchmark lines */}
              <ReferenceLine x={1}  stroke="#e5e7eb" strokeDasharray="4 3"
                label={{ value: "D1 bench 35%", position: "top", fill: "#9CA3AF", fontSize: 10 }} />
              <ReferenceLine y={35} stroke="#10B981" strokeDasharray="4 3" strokeWidth={1.5}
                label={{ value: "35%", position: "right", fill: "#10B981", fontSize: 10 }} />
              <ReferenceLine y={20} stroke="#00BCD4" strokeDasharray="4 3" strokeWidth={1.5}
                label={{ value: "20%", position: "right", fill: "#00BCD4", fontSize: 10 }} />
              <Area type="monotone" dataKey="retention_rate"
                fill="url(#retGrad)" stroke="#FF6B2C" strokeWidth={2.5} dot={false}
                activeDot={{ r: 5, fill: "#FF6B2C" }} />
            </ComposedChart>
          </ResponsiveContainer>
        )}
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Sessions by hour — intensity-colored bars */}
        <Card title="Sessions by Hour of Day">
          <p className="text-xs text-text-muted mb-4">
            Bar shade = intensity (darker orange = peak traffic). Schedule ad campaigns, push notifications,
            and live content at the darkest hours. Commute (8–9 AM, 6–8 PM) and late evening (9–11 PM)
            are the typical Indian social app peaks.
          </p>
          {byHour.loading ? <Spinner /> : (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={byHour.data ?? []} margin={{ top: 16, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" vertical={false} />
                <XAxis dataKey="hour" tick={TICK_STYLE} tickLine={false} axisLine={false} />
                <YAxis tick={TICK_STYLE} tickLine={false} axisLine={false}
                  tickFormatter={(v) => `${(v / 1000).toFixed(0)}K`} width={40} />
                <Tooltip contentStyle={TOOLTIP_STYLE}
                  formatter={(v: number, name: string) => [
                    name === "sessions" ? v.toLocaleString() : `${v} min`,
                    name === "sessions" ? "Sessions" : "Avg Duration",
                  ]} />
                <Bar dataKey="sessions" radius={[4, 4, 0, 0]} name="sessions">
                  {(byHour.data ?? []).map((row: { sessions: number }, i: number) => (
                    <Cell key={i} fill={hourColor(row.sessions)} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </Card>

        {/* City tier — colored bars with labels */}
        <Card title="Avg Session Duration by City Tier">
          <p className="text-xs text-text-muted mb-4">
            Tier-3/4 users often log longer sessions because ShareChat is a primary entertainment source
            with fewer competing apps. Tier-1 users have more alternatives but higher monetisation value.
          </p>
          {tiers.loading ? <Spinner /> : (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={tiers.data ?? []} margin={{ top: 24, right: 16, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" vertical={false} />
                <XAxis dataKey="city_tier" tick={TICK_STYLE} tickLine={false} axisLine={false} />
                <YAxis tick={TICK_STYLE} tickLine={false} axisLine={false} width={44}
                  tickFormatter={(v) => `${v}m`} />
                <Tooltip contentStyle={TOOLTIP_STYLE}
                  formatter={(v: number) => [`${v} min`, "Avg Duration"]} />
                <Bar dataKey="avg_session_min" radius={[6, 6, 0, 0]} name="Avg Session (min)">
                  {(tiers.data ?? []).map((_: unknown, i: number) => (
                    <Cell key={i} fill={SC_COLORS[i % SC_COLORS.length]} />
                  ))}
                  <LabelList dataKey="avg_session_min" position="top"
                    formatter={(v: number) => `${v}m`}
                    style={{ fontSize: 11, fontWeight: 700, fill: "#374151" }} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </Card>
      </div>
    </PageShell>
  );
}
