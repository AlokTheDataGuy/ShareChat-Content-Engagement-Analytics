import {
  ComposedChart, Area, Bar, Cell, LabelList,
  BarChart, AreaChart,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from "recharts";
import { Spinner, ErrorState, PageShell, Card, Insight, SC_COLORS, TOOLTIP_STYLE, TICK_STYLE } from "../components/ui/LoadingState";
import KPICard from "../components/ui/KPICard";
import { useAPI } from "../hooks/useAPI";
import { api } from "../services/api";

export default function Monetisation() {
  const kpis      = useAPI(api.monetisation.kpis);
  const arpuTiers = useAPI(api.monetisation.arpuByTier);
  const trend     = useAPI(api.monetisation.revenueTrend);
  const devices   = useAPI(api.monetisation.deviceMonetisation);

  if (kpis.error) return <ErrorState message={kpis.error} />;

  // Add 7-day rolling avg for revenue trend
  const trendWithAvg = (trend.data ?? []).map(
    (d: { date: string; daily_revenue: number }, i: number, arr: { daily_revenue: number }[]) => {
      const slice = arr.slice(Math.max(0, i - 6), i + 1);
      return { ...d, avg7d: parseFloat((slice.reduce((s, r) => s + r.daily_revenue, 0) / slice.length).toFixed(2)) };
    }
  );

  return (
    <PageShell
      title="Monetisation"
      subtitle="Ad revenue, ARPU by segment, and conversion funnel"
      description="ShareChat monetises primarily through in-feed ads. ARPU and CTR are the two levers — ARPU improves with better ad relevance and inventory quality; CTR improves with targeting and creative."
    >
      {kpis.loading ? <Spinner /> : (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-0 border-l border-t border-bg-border">
          <KPICard label="Total Revenue"    value={`₹${(kpis.data?.total_revenue / 1000).toFixed(1)}K`} sub="Ad revenue across all impressions" color="orange" />
          <KPICard label="ARPU"             value={`₹${kpis.data?.arpu}`}   sub="Avg revenue per user"        color="gold" />
          <KPICard label="Ad CTR"           value={`${kpis.data?.ctr}%`}    sub="Click-through rate"           color="teal" />
          <KPICard label="CVR (post-click)" value={`${kpis.data?.cvr}%`}    sub="Click-to-conversion rate"    color="green" />
        </div>
      )}

      {/* Revenue trend — area + rolling avg line */}
      <Card title="Daily Ad Revenue Trend">
        <p className="text-xs text-text-muted mb-4">
          Green area = daily revenue. Teal dashed = 7-day rolling average. Weekend spikes (Sat/Sun) of
          15–25% are normal. A sudden flat line usually means an ad fill rate issue — not organic traffic change.
        </p>
        {trend.loading ? <Spinner /> : (
          <ResponsiveContainer width="100%" height={320}>
            <ComposedChart data={trendWithAvg} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="revGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%"   stopColor="#10B981" stopOpacity={0.35} />
                  <stop offset="100%" stopColor="#10B981" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" vertical={false} />
              <XAxis dataKey="date" tick={TICK_STYLE} tickLine={false} axisLine={false}
                tickFormatter={(v) => v.slice(5)} interval={Math.floor((trendWithAvg.length ?? 1) / 8)} />
              <YAxis tick={TICK_STYLE} tickLine={false} axisLine={false}
                tickFormatter={(v) => `₹${v}`} width={52} />
              <Tooltip contentStyle={TOOLTIP_STYLE}
                formatter={(v: number, name: string) => [
                  `₹${v.toFixed(2)}`,
                  name === "daily_revenue" ? "Revenue" : "7-day avg",
                ]} />
              <Legend iconType="circle" iconSize={8}
                formatter={(v) => (
                  <span style={{ color: "#9CA3AF", fontSize: 12 }}>
                    {v === "daily_revenue" ? "Daily Revenue" : "7-Day Rolling Avg"}
                  </span>
                )} />
              <Area type="monotone" dataKey="daily_revenue"
                fill="url(#revGrad)" stroke="#10B981" strokeWidth={2} dot={false}
                activeDot={{ r: 4, fill: "#10B981" }} />
              <Area type="monotone" dataKey="avg7d"
                fill="none" stroke="#00BCD4" strokeWidth={2} dot={false}
                strokeDasharray="6 3" activeDot={{ r: 4, fill: "#00BCD4" }} />
            </ComposedChart>
          </ResponsiveContainer>
        )}
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* ARPU by tier — multi-color with labels */}
        <Card title="ARPU by City Tier">
          <p className="text-xs text-text-muted mb-4">
            Tier-1 users command 3–4× higher ARPU because advertisers bid more for metro audiences.
            The gap closes by improving ad relevance for Tier-3/4, not just adding more impressions.
          </p>
          {arpuTiers.loading ? <Spinner /> : (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={arpuTiers.data ?? []} margin={{ top: 24, right: 16, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" vertical={false} />
                <XAxis dataKey="city_tier" tick={TICK_STYLE} tickLine={false} axisLine={false} />
                <YAxis tick={TICK_STYLE} tickLine={false} axisLine={false}
                  tickFormatter={(v) => `₹${v}`} width={44} />
                <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v: number) => [`₹${v}`, "ARPU"]} />
                <Bar dataKey="arpu" radius={[6, 6, 0, 0]} name="ARPU (₹)">
                  {(arpuTiers.data ?? []).map((_: unknown, i: number) => (
                    <Cell key={i} fill={SC_COLORS[i % SC_COLORS.length]} />
                  ))}
                  <LabelList dataKey="arpu" position="top"
                    formatter={(v: number) => `₹${v}`}
                    style={{ fontSize: 11, fontWeight: 700, fill: "#374151" }} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </Card>

        {/* Device monetisation — inline bars */}
        <Card title="ARPU & CTR by Device Type">
          <p className="text-xs text-text-muted mb-4">
            iOS and premium Android see higher-bid ads. Low-end Android CTR below 1% is a signal
            to test lighter ad formats (native cards) to reduce load-related drop-off.
          </p>
          {devices.loading ? <Spinner /> : (
            <div className="space-y-5 pt-2">
              {(devices.data ?? []).map((row: { device_type: string; arpu: number; ctr: number }, i: number) => (
                <div key={row.device_type}>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-sm font-semibold text-text-primary">{row.device_type}</span>
                    <div className="flex gap-4 text-xs">
                      <span className="font-bold" style={{ color: SC_COLORS[i % SC_COLORS.length] }}>₹{row.arpu} ARPU</span>
                      <span className="font-bold" style={{ color: "#10B981" }}>{row.ctr}% CTR</span>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <div className="flex-1 bg-bg-elevated h-2 rounded-full overflow-hidden">
                      <div className="h-2 rounded-full transition-all"
                        style={{
                          width: `${Math.min(100, (row.arpu / ((devices.data?.[0]?.arpu ?? 1))) * 100)}%`,
                          background: SC_COLORS[i % SC_COLORS.length],
                        }} />
                    </div>
                    <div className="flex-1 bg-bg-elevated h-2 rounded-full overflow-hidden">
                      <div className="h-2 rounded-full transition-all"
                        style={{
                          width: `${Math.min(100, (row.ctr / ((devices.data?.[0]?.ctr ?? 1))) * 100)}%`,
                          background: "#10B981",
                        }} />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      <Insight title="Monetisation Lever">
        The highest-ROI action is improving ad relevance for Tier-2/3 users — largest segment by volume
        but lowest ARPU. A 10% CTR lift in Tier-3 adds more total revenue than a 10% ARPU lift in Tier-1
        because of the volume difference.
      </Insight>
    </PageShell>
  );
}
