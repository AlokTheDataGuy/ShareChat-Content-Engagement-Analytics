import {
  ComposedChart, Area, Line,
  BarChart, Bar, Cell, LabelList,
  PieChart, Pie, Label,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from "recharts";
import KPICard from "../components/ui/KPICard";
import { Spinner, ErrorState, PageShell, Card, Insight, SC_COLORS, TOOLTIP_STYLE, TICK_STYLE } from "../components/ui/LoadingState";
import { useAPI } from "../hooks/useAPI";
import { api } from "../services/api";

const fmt = (n: number) =>
  n >= 1_000_000 ? `${(n / 1_000_000).toFixed(1)}M`
  : n >= 1_000   ? `${(n / 1_000).toFixed(1)}K`
  : String(n);

export default function Overview() {
  const kpis         = useAPI(api.overview.kpis);
  const trend        = useAPI(api.overview.dauTrend);
  const engagement   = useAPI(api.overview.engagementBreakdown);
  const contentTypes = useAPI(api.overview.topContentTypes);

  if (kpis.error) return <ErrorState message={kpis.error} />;

  // 7-day rolling average overlay
  const trendWithAvg = (trend.data ?? []).map(
    (d: { date: string; dau: number }, i: number, arr: { dau: number }[]) => {
      const slice = arr.slice(Math.max(0, i - 6), i + 1);
      return { ...d, avg7d: Math.round(slice.reduce((s, r) => s + r.dau, 0) / slice.length) };
    }
  );

  const totalEvents = (engagement.data ?? []).reduce(
    (s: number, r: { count: number }) => s + r.count, 0
  );

  const stickiness = kpis.data?.stickiness ?? 0;

  return (
    <PageShell
      title="Overview"
      subtitle="Platform-wide engagement metrics · last 90 days"
      description="Top-level health of the platform. DAU/MAU stickiness is the single most important metric — it tells you whether users have formed a daily habit. Anything above 20% is healthy for a social app; above 40% is exceptional."
    >
      {/* KPI grid */}
      {kpis.loading ? <Spinner /> : (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-0 border-l border-t border-bg-border">
          <KPICard label="Daily Active Users"   value={fmt(kpis.data?.dau)}             sub="Unique users with ≥1 session today"      color="orange" />
          <KPICard label="Monthly Active Users" value={fmt(kpis.data?.mau)}             sub={`Stickiness ${kpis.data?.stickiness}% DAU/MAU`} color="teal" />
          <KPICard label="Avg Session"          value={`${kpis.data?.avg_session_minutes} min`} sub="Across all device tiers"          color="green" />
          <KPICard label="Engagement Rate"      value={`${kpis.data?.engagement_rate}%`} sub="Likes + shares + comments / views"      color="purple" />
          <KPICard label="Weekly Active Users"  value={fmt(kpis.data?.wau)}             sub="Unique users last 7 days"                color="gold" />
          <KPICard label="ARPU"                 value={`₹${kpis.data?.arpu}`}           sub="Avg revenue per user (ads)"             color="blue" />
          <KPICard label="Total Events"         value={fmt(kpis.data?.total_events)}    sub="Engagement events in warehouse"          color="orange" />
          <KPICard label="DAU / WAU"            value={`${kpis.data?.wau ? Math.round(kpis.data.dau / kpis.data.wau * 100) : 0}%`} sub="Weekly stickiness" color="teal" />
        </div>
      )}

      {!kpis.loading && (
        <Insight title="Stickiness Check">
          {stickiness >= 40
            ? `DAU/MAU of ${stickiness}% is above the 40% benchmark — users have formed a strong daily habit.`
            : `DAU/MAU of ${stickiness}% is below the 40% benchmark. Prioritise D1 onboarding quality and push re-engagement.`}
        </Insight>
      )}

      {/* Hero: DAU trend with 7-day rolling average */}
      <Card title="Daily Active Users — 90-Day Trend">
        <p className="text-xs text-text-muted mb-4">
          Orange area = actual DAU. Teal dashed line = 7-day rolling average (smooths weekend noise).
          A rising average with consistent weekend spikes is the healthiest pattern.
        </p>
        {trend.loading ? <Spinner /> : (
          <ResponsiveContainer width="100%" height={320}>
            <ComposedChart data={trendWithAvg} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="dauGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%"   stopColor="#FF6B2C" stopOpacity={0.35} />
                  <stop offset="100%" stopColor="#FF6B2C" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" vertical={false} />
              <XAxis dataKey="date" tick={TICK_STYLE} tickLine={false} axisLine={false}
                tickFormatter={(v) => v.slice(5)}
                interval={Math.floor((trendWithAvg.length ?? 1) / 8)} />
              <YAxis tick={TICK_STYLE} tickLine={false} axisLine={false} tickFormatter={fmt} width={52} />
              <Tooltip
                contentStyle={TOOLTIP_STYLE}
                formatter={(v: number, name: string) => [fmt(v), name === "dau" ? "DAU" : "7-day avg"]}
                labelFormatter={(l) => `Date: ${l}`}
              />
              <Legend
                iconType="circle" iconSize={8}
                formatter={(v) => (
                  <span style={{ color: "#9CA3AF", fontSize: 12 }}>
                    {v === "dau" ? "Daily Active Users" : "7-Day Rolling Avg"}
                  </span>
                )}
              />
              <Area  type="monotone" dataKey="dau"   fill="url(#dauGrad)" stroke="#FF6B2C" strokeWidth={2} dot={false} activeDot={{ r: 5, fill: "#FF6B2C" }} />
              <Line  type="monotone" dataKey="avg7d" stroke="#00BCD4"     strokeWidth={2}  dot={false}  strokeDasharray="6 3" activeDot={{ r: 4, fill: "#00BCD4" }} />
            </ComposedChart>
          </ResponsiveContainer>
        )}
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Donut with live center stat */}
        <Card title="Engagement Event Breakdown">
          <p className="text-xs text-text-muted mb-4">
            Total events by type. The <strong>share ÷ like ratio</strong> is the virality signal —
            a high share rate means content spreads organically beyond the app.
          </p>
          {engagement.loading ? <Spinner /> : (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={engagement.data ?? []}
                  dataKey="count"
                  nameKey="event_type"
                  cx="50%" cy="50%"
                  innerRadius={80} outerRadius={120}
                  paddingAngle={3}
                  label={({ event_type, percent }) =>
                    `${event_type} ${(percent * 100).toFixed(1)}%`
                  }
                  labelLine={{ stroke: "#e5e7eb", strokeWidth: 1 }}
                >
                  {(engagement.data ?? []).map((_: unknown, i: number) => (
                    <Cell key={i} fill={SC_COLORS[i % SC_COLORS.length]} />
                  ))}
                  <Label
                    content={({ viewBox }) => {
                      const vb = viewBox as { cx: number; cy: number };
                      return (
                        <g>
                          <text x={vb.cx} y={vb.cy - 10} textAnchor="middle"
                            style={{ fontSize: 22, fontWeight: 800, fill: "#111827" }}>
                            {fmt(totalEvents)}
                          </text>
                          <text x={vb.cx} y={vb.cy + 12} textAnchor="middle"
                            style={{ fontSize: 11, fill: "#9CA3AF" }}>
                            total events
                          </text>
                        </g>
                      );
                    }}
                  />
                </Pie>
                <Tooltip contentStyle={TOOLTIP_STYLE}
                  formatter={(v: number) => [v.toLocaleString(), "Events"]} />
              </PieChart>
            </ResponsiveContainer>
          )}
        </Card>

        {/* Multi-color bars with data labels */}
        <Card title="Engagement Rate by Content Type">
          <p className="text-xs text-text-muted mb-4">
            Engagement rate = (likes + shares + comments) ÷ views. Higher-rate formats
            should get more feed weight and more creator incentive budget.
          </p>
          {contentTypes.loading ? <Spinner /> : (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart
                data={contentTypes.data ?? []}
                margin={{ top: 24, right: 16, left: 0, bottom: 32 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" vertical={false} />
                <XAxis
                  dataKey="content_type" tick={{ ...TICK_STYLE, fontSize: 10 }}
                  tickLine={false} axisLine={false}
                  angle={-30} textAnchor="end" interval={0}
                />
                <YAxis tick={TICK_STYLE} tickLine={false} axisLine={false}
                  tickFormatter={(v) => `${v}%`} width={36} />
                <Tooltip contentStyle={TOOLTIP_STYLE}
                  formatter={(v: number) => [`${v}%`, "Eng. Rate"]} />
                <Bar dataKey="eng_rate" radius={[6, 6, 0, 0]} name="Eng. Rate %">
                  {(contentTypes.data ?? []).map((_: unknown, i: number) => (
                    <Cell key={i} fill={SC_COLORS[i % SC_COLORS.length]} />
                  ))}
                  <LabelList
                    dataKey="eng_rate"
                    position="top"
                    formatter={(v: number) => `${v}%`}
                    style={{ fontSize: 11, fontWeight: 700, fill: "#374151" }}
                  />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </Card>
      </div>
    </PageShell>
  );
}
