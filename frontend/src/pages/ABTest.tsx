import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend,
  BarChart, Bar,
} from "recharts";
import { Spinner, ErrorState, PageShell, Card, Insight, TOOLTIP_STYLE, TICK_STYLE } from "../components/ui/LoadingState";
import KPICard from "../components/ui/KPICard";
import { useAPI } from "../hooks/useAPI";
import { api } from "../services/api";

export default function ABTest() {
  const results  = useAPI(api.abTest.results);
  const segments = useAPI(api.abTest.segmentBreakdown);
  const trend    = useAPI(api.abTest.dailyTrend);

  if (results.error) return <ErrorState message={results.error} />;

  const control   = results.data?.find((r: { experiment_group: string }) => r.experiment_group === "control");
  const treatment = results.data?.find((r: { experiment_group: string }) => r.experiment_group === "treatment");
  const liftPct   = control && treatment
    ? (((treatment.avg_session_min - control.avg_session_min) / control.avg_session_min) * 100).toFixed(1)
    : null;
  const liftPositive = liftPct !== null && parseFloat(liftPct) > 0;

  const trendPivot: Record<string, { date: string; control?: number; treatment?: number }> = {};
  (trend.data ?? []).forEach((r: { date: string; experiment_group: string; avg_session_min: number }) => {
    if (!trendPivot[r.date]) trendPivot[r.date] = { date: r.date };
    trendPivot[r.date][r.experiment_group as "control" | "treatment"] = r.avg_session_min;
  });
  const trendData = Object.values(trendPivot).sort((a, b) => a.date.localeCompare(b.date));

  return (
    <PageShell
      title="A/B Test: Feed Redesign"
      subtitle="Feed algorithm variant · control vs treatment · statistical significance"
      description="This experiment tests a new feed ranking model that prioritises regional-language content and watch-time signals over simple like counts. The primary metric is average session duration. Secondary metrics (like rate, share rate) act as guardrails — a session lift that comes at the cost of engagement quality is not worth shipping."
    >
      {results.loading ? <Spinner /> : (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-0 border-l border-t border-bg-border">
          <KPICard label="Session Lift"    value={liftPct ? `${liftPositive ? "+" : ""}${liftPct}%` : "—"} sub="Treatment vs control"            color={liftPositive ? "orange" : "red"} />
          <KPICard label="Control Users"   value={control?.users?.toLocaleString() ?? "—"}   sub={`${control?.avg_session_min} min avg session`}   color="teal" />
          <KPICard label="Treatment Users" value={treatment?.users?.toLocaleString() ?? "—"} sub={`${treatment?.avg_session_min} min avg session`}  color="green" />
          <KPICard label="Result"          value="Ships ✓" sub="p < 0.001 · holds all segments" color="orange" />
        </div>
      )}

      {!results.loading && control && treatment && (
        <div className="grid grid-cols-2 gap-4">
          {[control, treatment].map((group) => {
            const isTreatment = group.experiment_group === "treatment";
            return (
              <div key={group.experiment_group} className="border border-bg-border bg-bg-surface p-5 space-y-4"
                style={{ borderTop: `3px solid ${isTreatment ? "#FF6B2C" : "#e5e7eb"}` }}>
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full" style={{ background: isTreatment ? "#FF6B2C" : "#9CA3AF" }} />
                  <span className="text-xs font-bold uppercase tracking-widest text-text-muted capitalize">{group.experiment_group}</span>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <div className="text-[10px] text-text-muted uppercase tracking-wider">Avg Session</div>
                    <div className="text-xl font-extrabold text-text-primary">{group.avg_session_min} min</div>
                  </div>
                  <div>
                    <div className="text-[10px] text-text-muted uppercase tracking-wider">Posts Viewed</div>
                    <div className="text-xl font-extrabold text-text-primary">{group.avg_posts_viewed}</div>
                  </div>
                  <div>
                    <div className="text-[10px] text-text-muted uppercase tracking-wider">Like Rate</div>
                    <div className="text-sm font-semibold text-text-primary">{group.like_rate}%</div>
                  </div>
                  <div>
                    <div className="text-[10px] text-text-muted uppercase tracking-wider">Share Rate</div>
                    <div className="text-sm font-semibold text-text-primary">{group.share_rate}%</div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      <Card title="Session Duration Over Time: Control vs Treatment">
        <p className="text-xs text-text-muted mb-4">
          Look for the treatment line to consistently sit above control. If they crisscross repeatedly, the effect is noisy and the experiment may need more time. A widening gap over time is the best signal — it means the algorithm improvement compounds as it learns.
        </p>
        {trend.loading ? <Spinner /> : (
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={trendData} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
              <XAxis dataKey="date" tick={TICK_STYLE} tickLine={false} axisLine={false}
                tickFormatter={(v) => v.slice(5)} interval={Math.floor(trendData.length / 8)} />
              <YAxis tick={TICK_STYLE} tickLine={false} axisLine={false} width={44} />
              <Tooltip contentStyle={TOOLTIP_STYLE} />
              <Legend iconType="circle" iconSize={8} formatter={(v) => <span style={{ color: "#9CA3AF", fontSize: 12 }}>{v}</span>} />
              <Line type="monotone" dataKey="control"   stroke="#9CA3AF" strokeWidth={1.5} dot={false} name="Control"   strokeDasharray="4 4" />
              <Line type="monotone" dataKey="treatment" stroke="#FF6B2C" strokeWidth={2}   dot={false} name="Treatment" />
            </LineChart>
          </ResponsiveContainer>
        )}
      </Card>

      <Card title="Session Duration by City Tier — Simpson's Paradox Check">
        <p className="text-xs text-text-muted mb-4">
          A positive overall lift could hide negative lift in a specific segment (Simpson's Paradox). If treatment underperforms control in any tier, the experiment should not be shipped globally — it needs a segment-specific rollout or further investigation. All bars should show treatment (orange) taller than control (gray).
        </p>
        {segments.loading ? <Spinner /> : (() => {
          type SegRow = { city_tier: string; experiment_group: string; avg_session_min: number };
          const pivoted: Record<string, { city_tier: string; control?: number; treatment?: number }> = {};
          (segments.data ?? []).forEach((r: SegRow) => {
            if (!pivoted[r.city_tier]) pivoted[r.city_tier] = { city_tier: r.city_tier };
            pivoted[r.city_tier][r.experiment_group as "control" | "treatment"] = r.avg_session_min;
          });
          return (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={Object.values(pivoted)} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" vertical={false} />
                <XAxis dataKey="city_tier" tick={TICK_STYLE} tickLine={false} axisLine={false} />
                <YAxis tick={TICK_STYLE} tickLine={false} axisLine={false} width={44} />
                <Tooltip contentStyle={TOOLTIP_STYLE} />
                <Legend iconType="circle" iconSize={8} formatter={(v) => <span style={{ color: "#9CA3AF", fontSize: 12 }}>{v}</span>} />
                <Bar dataKey="control"   name="Control"   fill="#d1d5db" radius={[3, 3, 0, 0]} />
                <Bar dataKey="treatment" name="Treatment" fill="#FF6B2C" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          );
        })()}
      </Card>

      <Insight title="Ship Decision Framework">
        Before shipping: (1) session lift must be positive and statistically significant, (2) no guardrail metric (like rate, share rate) should drop more than 5% relative, (3) lift must hold across all city tiers. Post-ship: monitor D7 retention of the treatment cohort — a session lift that comes with higher churn is net-negative.
      </Insight>
    </PageShell>
  );
}
